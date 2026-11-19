from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from ..types.dag_types import DagGraph, DagNode, NodeStatus, NodeMetadata
from ..registry.unified_tool_registry import (
    UnifiedToolRegistry,
    ExecutionMode,
)
from ..registry.mcp_bridge import BridgeResult
from .cache_manager import CacheManager, CacheConfig, CacheBackendType, CacheMetadata
from .scheduler import Scheduler

logger = logging.getLogger("oea.orchestrator")


@dataclass
class OrchestratorConfig:
    use_mock_bridge: bool = True
    bridge_url: str = "http://localhost:3000/api/oea-bridge"
    max_parallel: int = 8
    cache_backend: str = "local"
    cache_root: str = "/tmp/oea_cache"
    enable_cache: bool = True


class SpaceOrchestrator:
    """
    空间编排器核心

    职责:
    1. DAG 构建与执行
    2. 工具匹配与调度
    3. 中间结果缓存
    4. 进度跟踪
    """

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()

        self.tool_registry = UnifiedToolRegistry({
            "bridge_url": self.config.bridge_url,
            "use_mock_bridge": self.config.use_mock_bridge,
        })

        cache_config = CacheConfig(
            backend_type=CacheBackendType(self.config.cache_backend),
            local_root=self.config.cache_root,
        )
        self.cache_manager = CacheManager(cache_config)

        self.scheduler = Scheduler(max_parallel=self.config.max_parallel)

    async def initialize(self) -> None:
        await self.tool_registry.initialize()
        logger.info("SpaceOrchestrator initialized")

    async def build_dag(
        self,
        task_description: str,
        steps: list[dict],
        workspace_id: str = "default",
    ) -> DagGraph:
        graph_id = f"dag_{uuid.uuid4().hex[:8]}"
        dag = DagGraph(graph_id=graph_id)

        for i, step in enumerate(steps):
            node_id = f"node_{i:03d}"

            tool_name = step.get("tool", step.get("tool_name", ""))
            execution_mode = step.get("execution_mode", "mcp")

            node = DagNode(
                node_id=node_id,
                name=step.get("name", f"步骤 {i+1}"),
                description=step.get("description", tool_name),
                tool_name=tool_name,
                tool_id=step.get("tool_id"),
                execution_mode=execution_mode,
                tool_args=step.get("args", {}),
                dependencies=step.get("dependencies", []),
                metadata=NodeMetadata(
                    estimated_duration_seconds=step.get("estimated_duration", 60),
                    estimated_gpu_memory_gb=step.get("gpu_memory", 0),
                ),
            )

            dag.add_node(node)

        for node in dag.nodes.values():
            for dep_id in node.dependencies:
                if dep_id in dag.nodes:
                    dag.add_edge(dep_id, node.node_id)

        return dag

    async def execute_dag(
        self,
        dag: DagGraph,
        workspace_id: str = "default",
        on_progress: Optional[callable] = None,
    ) -> DagGraph:
        async def execute_node(node: DagNode):
            mode = ExecutionMode(node.execution_mode)

            args = node.tool_args or {}

            if mode == ExecutionMode.SANDBOX:
                if "code" not in args:
                    return {"success": False, "error": "No code provided for sandbox"}
            else:
                tool_id = node.tool_id or node.tool_name
                if not tool_id:
                    return {"success": False, "error": "No tool specified"}

                cached = await self._check_cache(node, tool_id)
                if cached:
                    logger.info(f"Cache hit for node {node.node_id}")
                    return cached

            result: BridgeResult = await self.tool_registry.execute_tool(
                tool_id=node.tool_id or node.tool_name,
                args=args,
                mode=mode,
                workspace_id=workspace_id,
            )

            if result.success:
                await self._save_to_cache(node, result)

            return result

        def on_node_update(node: DagNode):
            if on_progress:
                on_progress({
                    "node_id": node.node_id,
                    "status": node.status.value,
                    "progress": node.progress,
                    "error": node.error,
                })

        return await self.scheduler.execute(dag, execute_node, on_node_update)

    async def orchestrate(
        self,
        task_description: str,
        steps: list[dict],
        workspace_id: str = "default",
        on_progress: Optional[callable] = None,
    ) -> dict:
        logger.info(f"Orchestrating task: {task_description}")

        await self.initialize()

        dag = await self.build_dag(task_description, steps, workspace_id)

        executed_dag = await self.execute_dag(dag, workspace_id, on_progress)

        return {
            "success": True,
            "graph_id": executed_dag.graph_id,
            "nodes": [n.to_dict() for n in executed_dag.nodes.values()],
            "duration_ms": sum(
                n.duration_ms for n in executed_dag.nodes.values()
                if n.duration_ms
            ),
            "succeeded_count": sum(
                1 for n in executed_dag.nodes.values()
                if n.status == NodeStatus.SUCCEEDED
            ),
            "failed_count": sum(
                1 for n in executed_dag.nodes.values()
                if n.status == NodeStatus.FAILED
            ),
        }

    async def _check_cache(
        self,
        node: DagNode,
        tool_id: str,
    ) -> Optional[dict]:
        if not self.config.enable_cache:
            return None

        cache_key = self.cache_manager.get_cache_key(
            source_file=str(node.tool_args.get("input_path", "")),
            operation=tool_id,
            params=node.tool_args,
        )

        local_path = self.cache_manager.get_task_cache_path("default", cache_key)

        if await self.cache_manager.check_cache(cache_key, local_path):
            return {
                "success": True,
                "from_cache": True,
                "cache_key": cache_key,
                "output_files": [local_path],
            }

        return None

    async def _save_to_cache(self, node: DagNode, result: BridgeResult) -> None:
        if not self.config.enable_cache:
            return

        cache_key = self.cache_manager.get_cache_key(
            source_file=str(node.tool_args.get("input_path", "")),
            operation=node.tool_id or node.tool_name or "unknown",
            params=node.tool_args,
        )

        output_files = []
        if isinstance(result.result, dict):
            output_files = result.result.get("output_files", [])

        if output_files and os.path.exists(output_files[0]):
            metadata = CacheMetadata(
                cache_key=cache_key,
                source_file=str(node.tool_args.get("input_path", "")),
                operation=node.tool_id or node.tool_name or "unknown",
                params=node.tool_args,
                file_size=os.path.getsize(output_files[0]),
            )
            await self.cache_manager.save_to_cache(output_files[0], cache_key, metadata)

    async def close(self) -> None:
        await self.tool_registry.close()

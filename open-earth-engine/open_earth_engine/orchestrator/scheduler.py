from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..types.dag_types import DagGraph, DagNode, NodeStatus
from .parallel_optimizer import ParallelOptimizer, ResourceMonitor

logger = logging.getLogger("oea.scheduler")


class Scheduler:
    """DAG 调度器 - 资源感知版"""

    def __init__(self, max_parallel: int = 8, config: dict = None):
        self.max_parallel = max_parallel
        self.config = config or {}
        self._semaphore: Optional[asyncio.Semaphore] = None

        self.optimizer = ParallelOptimizer(self.config)
        self.resource_monitor = ResourceMonitor()

    async def execute(
        self,
        graph: DagGraph,
        node_executor: Callable[[DagNode], Any],
        on_node_update: Optional[Callable[[DagNode], None]] = None,
    ) -> DagGraph:
        logger.info(f"Executing DAG: {graph.graph_id}")

        graph = self.optimizer.optimize(graph)

        self._semaphore = asyncio.Semaphore(self.max_parallel)

        resource_snapshot = await self.resource_monitor.get_snapshot()
        logger.info(
            f"Resource snapshot: "
            f"GPU={resource_snapshot.gpu_available}/{resource_snapshot.gpu_total}, "
            f"Mem={resource_snapshot.memory_available_gb:.1f}GB, "
            f"CPU={resource_snapshot.cpu_available}/{resource_snapshot.cpu_total}"
        )

        while True:
            ready_nodes = graph.get_ready_nodes()

            if not ready_nodes:
                running = [
                    n for n in graph.nodes.values()
                    if n.status == NodeStatus.RUNNING
                ]
                if not running:
                    break
                await asyncio.sleep(0.1)
                continue

            tasks = []
            groups = self._group_ready_nodes(ready_nodes)

            for group_id, group_nodes in groups.items():
                if group_id != "independent":
                    group_parallelism = await self._calculate_group_parallelism(
                        group_nodes, resource_snapshot
                    )
                    group_semaphore = asyncio.Semaphore(group_parallelism)

                    for node in group_nodes:
                        node.status = NodeStatus.READY
                        if on_node_update:
                            on_node_update(node)

                        task = self._execute_with_group_semaphore(
                            node, graph, group_semaphore, node_executor, on_node_update
                        )
                        tasks.append(task)
                else:
                    for node in group_nodes:
                        node.status = NodeStatus.READY
                        if on_node_update:
                            on_node_update(node)

                        task = self._execute_node(
                            node, graph, node_executor, on_node_update
                        )
                        tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                resource_snapshot = await self.resource_monitor.get_snapshot()

        return graph

    def _group_ready_nodes(
        self,
        nodes: list[DagNode],
    ) -> dict[str, list[DagNode]]:
        groups: dict[str, list[DagNode]] = {"independent": []}

        for node in nodes:
            pg = getattr(node.metadata, "parallel_group", None)
            if pg:
                if pg not in groups:
                    groups[pg] = []
                groups[pg].append(node)
            else:
                groups["independent"].append(node)

        return groups

    async def _calculate_group_parallelism(
        self,
        group_nodes: list[DagNode],
        resource_snapshot,
    ) -> int:
        from .parallel_optimizer import ParallelGroup, ParallelGroupType

        group = ParallelGroup(
            group_id="temp",
            group_type=ParallelGroupType.MULTI_SCENE,
            nodes=group_nodes,
        )

        return self.optimizer.estimate_parallel_degree(group, resource_snapshot)

    async def _execute_with_group_semaphore(
        self,
        node: DagNode,
        graph: DagGraph,
        group_semaphore: asyncio.Semaphore,
        node_executor: Callable[[DagNode], Any],
        on_node_update: Optional[Callable[[DagNode], None]],
    ):
        async with group_semaphore:
            async with self._semaphore:
                node.status = NodeStatus.RUNNING
                node.started_at = time.time()
                if on_node_update:
                    on_node_update(node)

                try:
                    result = await node_executor(node)
                    node.result = result
                    node.status = NodeStatus.SUCCEEDED
                    logger.info(f"Node succeeded: {node.node_id}")
                except Exception as e:
                    logger.error(f"Node failed: {node.node_id}, error={e}")

                    if node.retries < node.max_retries:
                        node.retries += 1
                        node.status = NodeStatus.RETRYING
                        node.error = str(e)
                        if on_node_update:
                            on_node_update(node)
                        await asyncio.sleep(1.0 * node.retries)
                        return await self._execute_with_group_semaphore(
                            node, graph, group_semaphore, node_executor, on_node_update
                        )

                    node.status = NodeStatus.FAILED
                    node.error = str(e)
                finally:
                    node.completed_at = time.time()
                    if node.started_at and node.completed_at:
                        node.duration_ms = (node.completed_at - node.started_at) * 1000
                    if on_node_update:
                        on_node_update(node)

    async def _execute_node(
        self,
        node: DagNode,
        graph: DagGraph,
        executor: Callable[[DagNode], Any],
        on_node_update: Optional[Callable[[DagNode], None]],
    ) -> None:
        async with self._semaphore:
            node.status = NodeStatus.RUNNING
            node.started_at = time.time()
            if on_node_update:
                on_node_update(node)

            try:
                result = await executor(node)
                node.result = result
                node.status = NodeStatus.SUCCEEDED
            except Exception as e:
                logger.error(f"Node execution failed: {node.node_id}, error={e}")

                if node.retries < node.max_retries:
                    node.retries += 1
                    node.status = NodeStatus.RETRYING
                    node.error = str(e)
                    if on_node_update:
                        on_node_update(node)
                    await asyncio.sleep(1.0 * node.retries)
                    await self._execute_node(node, graph, executor, on_node_update)
                    return

                node.status = NodeStatus.FAILED
                node.error = str(e)
            finally:
                node.completed_at = time.time()
                if node.started_at and node.completed_at:
                    node.duration_ms = (node.completed_at - node.started_at) * 1000
                if on_node_update:
                    on_node_update(node)

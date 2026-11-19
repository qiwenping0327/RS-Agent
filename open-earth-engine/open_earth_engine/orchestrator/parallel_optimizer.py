from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ..types.dag_types import DagGraph, DagNode

logger = logging.getLogger("oea.parallel")


class ParallelGroupType(str, Enum):
    MULTI_SCENE = "multi_scene"
    MULTI_INDEX = "multi_index"
    INDEPENDENT_GIS = "independent_gis"
    BAND_PARALLEL = "band_parallel"


@dataclass
class ParallelGroup:
    group_id: str
    group_type: ParallelGroupType
    nodes: list[DagNode]
    parallel_priority: int = 1

    @property
    def size(self) -> int:
        return len(self.nodes)


@dataclass
class ResourceSnapshot:
    gpu_total: int = 0
    gpu_available: int = 0
    gpu_memory_total_gb: float = 0.0
    gpu_memory_available_gb: float = 0.0
    cpu_total: int = 0
    cpu_available: int = 0
    memory_total_gb: float = 0.0
    memory_available_gb: float = 0.0


class ParallelOptimizer:
    """DAG 并行优化器"""

    OPERATION_RESOURCE_COST = {
        "download": {"gpu": 0, "memory_gb": 1.0, "cpu": 2},
        "preprocess": {"gpu": 0, "memory_gb": 2.0, "cpu": 4},
        "ndvi": {"gpu": 0, "memory_gb": 1.5, "cpu": 2},
        "ndwi": {"gpu": 0, "memory_gb": 1.5, "cpu": 2},
        "classification": {"gpu": 1, "memory_gb": 4.0, "cpu": 4},
        "segmentation": {"gpu": 1, "memory_gb": 6.0, "cpu": 4},
        "change_detection": {"gpu": 1, "memory_gb": 3.0, "cpu": 4},
        "zonal_stats": {"gpu": 0, "memory_gb": 0.5, "cpu": 2},
        "default": {"gpu": 0, "memory_gb": 1.0, "cpu": 2},
    }

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.max_parallel = self.config.get("max_parallel", 8)
        self.min_parallel_size = self.config.get("min_parallel_size", 2)

    def optimize(self, dag: DagGraph) -> DagGraph:
        logger.info("Optimizing DAG for parallel execution")

        groups = self._detect_parallel_groups(dag)

        for group in groups:
            for node in group.nodes:
                node.metadata.parallelizable = True
                node.metadata.parallel_group = group.group_id
                node.metadata.parallel_type = group.group_type.value

        logger.info(
            f"Detected {len(groups)} parallel groups, "
            f"total {sum(g.size for g in groups)} nodes"
        )

        return dag

    def _detect_parallel_groups(self, dag: DagGraph) -> list[ParallelGroup]:
        groups: list[ParallelGroup] = []
        layers = self._topological_layers(dag)

        for layer_idx, layer_nodes in enumerate(layers):
            scene_groups = self._detect_multi_scene(layer_nodes)
            groups.extend(scene_groups)

            index_groups = self._detect_multi_index(layer_nodes)
            groups.extend(index_groups)

            gis_groups = self._detect_independent_gis(layer_nodes, dag)
            groups.extend(gis_groups)

        groups = [g for g in groups if g.size >= self.min_parallel_size]
        groups.sort(key=lambda g: g.parallel_priority, reverse=True)

        return groups

    def _topological_layers(self, dag: DagGraph) -> list[list[DagNode]]:
        layers: list[list[DagNode]] = []
        visited: set[str] = set()
        in_degree = {nid: len(node.dependencies) for nid, node in dag.nodes.items()}

        while len(visited) < len(dag.nodes):
            current_layer = [
                dag.nodes[nid]
                for nid, deg in in_degree.items()
                if deg == 0 and nid not in visited
            ]

            if not current_layer:
                break

            layers.append(current_layer)

            for node in current_layer:
                visited.add(node.node_id)
                if node.node_id in dag.adjacency:
                    for successor in dag.adjacency[node.node_id]:
                        if successor in in_degree:
                            in_degree[successor] -= 1

        return layers

    def _detect_multi_scene(self, nodes: list[DagNode]) -> list[ParallelGroup]:
        by_operation: dict[str, list[DagNode]] = defaultdict(list)

        for node in nodes:
            op = self._get_operation_type(node)
            by_operation[op].append(node)

        groups = []
        for op, op_nodes in by_operation.items():
            if len(op_nodes) >= self.min_parallel_size:
                input_paths = set()
                for node in op_nodes:
                    input_path = self._get_input_path(node)
                    if input_path:
                        input_paths.add(input_path)

                if len(input_paths) >= self.min_parallel_size:
                    groups.append(ParallelGroup(
                        group_id=f"scene_{op}_{len(groups)}",
                        group_type=ParallelGroupType.MULTI_SCENE,
                        nodes=op_nodes,
                        parallel_priority=3,
                    ))

        return groups

    def _detect_multi_index(self, nodes: list[DagNode]) -> list[ParallelGroup]:
        by_input: dict[str, list[DagNode]] = defaultdict(list)
        index_keywords = ["ndvi", "ndwi", "evi", "savi", "ndbi", "mndwi", "nbr", "fvc"]

        for node in nodes:
            if self._is_index_calculation(node, index_keywords):
                input_path = self._get_input_path(node)
                if input_path:
                    by_input[input_path].append(node)

        groups = []
        for input_path, index_nodes in by_input.items():
            if len(index_nodes) >= self.min_parallel_size:
                groups.append(ParallelGroup(
                    group_id=f"index_{len(groups)}",
                    group_type=ParallelGroupType.MULTI_INDEX,
                    nodes=index_nodes,
                    parallel_priority=2,
                ))

        return groups

    def _detect_independent_gis(
        self,
        nodes: list[DagNode],
        dag: DagGraph,
    ) -> list[ParallelGroup]:
        gis_keywords = [
            "buffer", "clip", "intersect", "union", "difference",
            "zonal", "zonal_stats", "rasterize", "polygonize",
        ]

        gis_nodes = [
            n for n in nodes
            if self._matches_keywords(n, gis_keywords)
        ]

        if len(gis_nodes) < self.min_parallel_size:
            return []

        independent = []
        for i, node in enumerate(gis_nodes):
            has_dependency = False
            for j, other in enumerate(gis_nodes):
                if i == j:
                    continue
                if other.node_id in node.dependencies:
                    has_dependency = True
                    break
                if node.node_id in other.dependencies:
                    has_dependency = True
                    break

            if not has_dependency:
                independent.append(node)

        if len(independent) >= self.min_parallel_size:
            return [ParallelGroup(
                group_id=f"gis_{len(independent)}",
                group_type=ParallelGroupType.INDEPENDENT_GIS,
                nodes=independent,
                parallel_priority=1,
            )]

        return []

    def _get_operation_type(self, node: DagNode) -> str:
        if node.tool_name:
            for op in ["download", "preprocess", "analyze", "visualize", "ndvi", "ndwi"]:
                if op in node.tool_name.lower():
                    return op

        desc = (node.description or "").lower()
        for op in ["download", "preprocess", "analyze", "classify", "detect"]:
            if op in desc:
                return op

        return "unknown"

    def _get_input_path(self, node: DagNode) -> Optional[str]:
        if node.tool_args:
            for key in ["input_path", "input", "src", "source", "input_nir_path", "input_red_path"]:
                if key in node.tool_args:
                    return str(node.tool_args[key])
        return None

    def _is_index_calculation(self, node: DagNode, keywords: list[str]) -> bool:
        text = f"{node.tool_name or ''} {node.description or ''}".lower()
        return any(kw in text for kw in keywords)

    def _matches_keywords(self, node: DagNode, keywords: list[str]) -> bool:
        text = f"{node.tool_name or ''} {node.description or ''}".lower()
        return any(kw in text for kw in keywords)

    def estimate_parallel_degree(
        self,
        group: ParallelGroup,
        resource_snapshot: ResourceSnapshot,
    ) -> int:
        if group.size == 0:
            return 1

        total_gpu = 0
        total_memory = 0.0
        total_cpu = 0

        for node in group.nodes:
            op = self._get_operation_type(node)
            cost = self.OPERATION_RESOURCE_COST.get(
                op, self.OPERATION_RESOURCE_COST["default"]
            )
            total_gpu += cost["gpu"]
            total_memory += cost["memory_gb"]
            total_cpu += cost["cpu"]

        avg_gpu = total_gpu / len(group.nodes) if group.nodes else 0
        avg_memory = total_memory / len(group.nodes) if group.nodes else 1.0
        avg_cpu = total_cpu / len(group.nodes) if group.nodes else 1

        max_by_gpu = (
            resource_snapshot.gpu_available // max(int(avg_gpu), 1)
            if avg_gpu > 0
            else len(group.nodes)
        )
        max_by_memory = int(resource_snapshot.memory_available_gb / max(avg_memory, 0.5))
        max_by_cpu = int(resource_snapshot.cpu_available / max(int(avg_cpu), 1))

        parallel_degree = min(
            max_by_gpu,
            max_by_memory,
            max_by_cpu,
            self.max_parallel,
            group.size,
        )

        parallel_degree = max(parallel_degree, 1)

        logger.info(
            f"Group {group.group_id}: {group.size} nodes, "
            f"suggested parallelism={parallel_degree}"
        )

        return parallel_degree


class ResourceMonitor:
    """资源监控器"""

    async def get_snapshot(self) -> ResourceSnapshot:
        snapshot = ResourceSnapshot()

        try:
            import os
            cpu_count = os.cpu_count() or 4
            snapshot.cpu_total = cpu_count
            snapshot.cpu_available = max(1, int(cpu_count * 0.8))
        except Exception:
            snapshot.cpu_total = 4
            snapshot.cpu_available = 3

        try:
            import psutil
            mem = psutil.virtual_memory()
            snapshot.memory_total_gb = mem.total / (1024 ** 3)
            snapshot.memory_available_gb = mem.available / (1024 ** 3)
        except Exception:
            snapshot.memory_total_gb = 16.0
            snapshot.memory_available_gb = 8.0

        try:
            import torch
            if torch.cuda.is_available():
                snapshot.gpu_total = torch.cuda.device_count()
                snapshot.gpu_available = max(1, snapshot.gpu_total)
                if snapshot.gpu_total > 0:
                    props = torch.cuda.get_device_properties(0)
                    snapshot.gpu_memory_total_gb = props.total_memory / (1024 ** 3)
                    snapshot.gpu_memory_available_gb = snapshot.gpu_memory_total_gb * 0.7
        except Exception:
            pass

        return snapshot

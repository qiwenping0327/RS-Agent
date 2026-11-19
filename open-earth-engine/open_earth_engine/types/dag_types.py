from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class NodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class NodeMetadata:
    estimated_duration_seconds: Optional[int] = None
    estimated_gpu_memory_gb: Optional[float] = None
    estimated_cpu_cores: Optional[int] = None
    output_size_mb: Optional[float] = None
    parallelizable: bool = False
    parallel_group: Optional[str] = None
    parallel_type: Optional[str] = None


@dataclass
class DagNode:
    node_id: str
    name: str
    description: str = ""
    tool_name: Optional[str] = None
    tool_id: Optional[str] = None
    execution_mode: str = "mcp"
    tool_args: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: Optional[float] = None
    progress: Optional[float] = None
    output_files: list[str] = field(default_factory=list)
    metadata: NodeMetadata = field(default_factory=NodeMetadata)

    @property
    def parallelizable(self) -> bool:
        return self.metadata.parallelizable

    @parallelizable.setter
    def parallelizable(self, value: bool) -> None:
        self.metadata.parallelizable = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.name,
            "description": self.description,
            "toolName": self.tool_name,
            "toolId": self.tool_id,
            "executionMode": self.execution_mode,
            "status": self.status.value,
            "progress": self.progress,
            "error": self.error,
            "outputFiles": self.output_files,
            "parallelizable": self.metadata.parallelizable,
            "parallelGroup": self.metadata.parallel_group,
            "parallelType": self.metadata.parallel_type,
        }


@dataclass
class DagEdge:
    source: str
    target: str
    status: str = "inactive"
    animated: bool = False


@dataclass
class DagGraph:
    graph_id: str
    nodes: dict[str, DagNode] = field(default_factory=dict)
    edges: list[DagEdge] = field(default_factory=list)
    adjacency: dict[str, list[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def add_node(self, node: DagNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str) -> None:
        self.edges.append(DagEdge(source=source_id, target=target_id))
        if source_id not in self.adjacency:
            self.adjacency[source_id] = []
        self.adjacency[source_id].append(target_id)

    def get_ready_nodes(self) -> list[DagNode]:
        ready = []
        for node in self.nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            all_deps_satisfied = True
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if dep_node is None:
                    continue
                if dep_node.status != NodeStatus.SUCCEEDED:
                    all_deps_satisfied = False
                    break
            if all_deps_satisfied:
                ready.append(node)
        return ready

    def mark_edge_active(self, source_id: str, target_id: str) -> None:
        for edge in self.edges:
            if edge.source == source_id and edge.target == target_id:
                edge.status = "active"
                edge.animated = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.graph_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [
                {"source": e.source, "target": e.target, "animated": e.animated}
                for e in self.edges
            ],
        }

    def topological_order(self) -> list[DagNode]:
        visited: set[str] = set()
        order: list[DagNode] = []

        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            node = self.nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    visit(dep_id)
                order.append(node)

        for node_id in self.nodes:
            visit(node_id)

        return order

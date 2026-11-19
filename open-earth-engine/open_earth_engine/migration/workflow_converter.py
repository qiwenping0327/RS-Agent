from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("oea.migration")


@dataclass
class LegacyRsAgentTask:
    task_id: str
    description: str
    steps: list[dict] = field(default_factory=list)


@dataclass
class ConvertedDag:
    task_id: str
    dag_id: str
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class WorkflowConverter:
    """工作流转换器 - rs-agent 链式任务 → DAG"""

    TOOL_MAPPING = {
        "rs_download": "rs-agent.rs_download",
        "rs_preprocess": "rs-agent.rs_preprocess",
        "rs_analyze": "rs-agent.rs_analyze",
        "rs_visualize": "rs-agent.rs_visualize",
        "rs_report": "rs-agent.rs_report",
        "rs_sar_analysis": "rs-agent.rs_sar_analysis",
        "rs_model_inference": "rs-agent.rs_model_inference",
        "calculate_ndvi": "rs-index.ndvi_calc",
        "calculate_ndwi": "rs-index.ndwi_calc",
        "calculate_evi": "rs-index.evi_calc",
    }

    def convert_rs_agent_task(
        self,
        legacy_task: LegacyRsAgentTask,
    ) -> ConvertedDag:
        logger.info(f"Converting legacy task: {legacy_task.task_id}")

        nodes: list[dict] = []
        edges: list[dict] = []
        var_to_node: dict[str, str] = {}

        for i, step in enumerate(legacy_task.steps):
            node_id = f"step_{i:03d}"
            tool_name = step.get("tool", "")
            mapped_tool = self.TOOL_MAPPING.get(tool_name, tool_name)

            node = {
                "id": node_id,
                "name": f"步骤 {i+1}: {step.get('tool', 'unknown')}",
                "description": step.get("description", ""),
                "tool_id": mapped_tool,
                "tool_name": tool_name,
                "execution_mode": "mcp",
                "tool_args": step.get("args", {}),
                "dependencies": [],
                "output_var": step.get("output_var"),
                "parallelizable": False,
            }

            nodes.append(node)

            if step.get("output_var"):
                var_to_node[step["output_var"]] = node_id

        for i, node in enumerate(nodes):
            node_id = node["id"]
            args = node.get("tool_args", {})

            dependencies = self._extract_dependencies(args, var_to_node)

            if not dependencies and i > 0:
                dependencies.append(nodes[i - 1]["id"])

            dependencies = list(set(dependencies))
            node["dependencies"] = dependencies

            for dep_id in dependencies:
                if dep_id != node_id:
                    edges.append({
                        "source": dep_id,
                        "target": node_id,
                    })

        nodes = self._detect_parallel_opportunities(nodes, edges)

        metadata = {
            "converted_from": "rs_agent_chain",
            "original_step_count": len(legacy_task.steps),
            "parallel_groups_detected": sum(
                1 for n in nodes if n.get("parallelizable")
            ),
        }

        return ConvertedDag(
            task_id=legacy_task.task_id,
            dag_id=f"dag_{legacy_task.task_id}",
            nodes=nodes,
            edges=edges,
            metadata=metadata,
        )

    def _extract_dependencies(
        self,
        args: dict[str, Any],
        var_to_node: dict[str, str],
    ) -> list[str]:
        dependencies = []

        def check_value(value: Any):
            if isinstance(value, str):
                if value in var_to_node:
                    dependencies.append(var_to_node[value])
                template_vars = re.findall(r'\{\{(\w+)\}\}', value)
                for var in template_vars:
                    if var in var_to_node:
                        dependencies.append(var_to_node[var])
            elif isinstance(value, dict):
                for v in value.values():
                    check_value(v)
            elif isinstance(value, list):
                for v in value:
                    check_value(v)

        for v in args.values():
            check_value(v)

        return dependencies

    def _detect_parallel_opportunities(
        self,
        nodes: list[dict],
        edges: list[dict],
    ) -> list[dict]:
        in_degree = defaultdict(int)
        for edge in edges:
            in_degree[edge["target"]] += 1

        layer_nodes = [n for n in nodes if in_degree.get(n["id"], 0) == 0]

        if len(layer_nodes) >= 2:
            tools = set(n.get("tool_id", "").split(".")[-1] for n in layer_nodes)
            if len(tools) == 1:
                group_id = f"auto_parallel_{len(layer_nodes)}"
                for node in layer_nodes:
                    node["parallelizable"] = True
                    node["parallel_group"] = group_id
                    node["parallel_type"] = "multi_scene"

        return nodes

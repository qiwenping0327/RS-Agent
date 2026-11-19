from __future__ import annotations

import asyncio
import os
import sys

from .orchestrator import SpaceOrchestrator, OrchestratorConfig
from .registry import UnifiedToolRegistry, McpBridgeClient
from .types import DagGraph, DagNode, NodeStatus

__all__ = [
    "SpaceOrchestrator",
    "OrchestratorConfig",
    "UnifiedToolRegistry",
    "McpBridgeClient",
    "DagGraph",
    "DagNode",
    "NodeStatus",
    "run_simple_task",
]


async def run_simple_task(
    task_description: str,
    steps: list[dict],
    workspace_id: str = "default",
) -> dict:
    orchestrator = SpaceOrchestrator(OrchestratorConfig(
        use_mock_bridge=True,
        max_parallel=4,
    ))

    try:
        result = await orchestrator.orchestrate(
            task_description=task_description,
            steps=steps,
            workspace_id=workspace_id,
        )
        return result
    finally:
        await orchestrator.close()


def run_cli():
    import argparse

    parser = argparse.ArgumentParser(description="OpenEarthAgent CLI")
    parser.add_argument("--task", type=str, help="Task description")
    parser.add_argument("--steps", type=str, help="JSON steps file path")

    args = parser.parse_args()

    if args.steps and os.path.exists(args.steps):
        import json
        with open(args.steps, "r") as f:
            steps = json.load(f)

        result = asyncio.run(run_simple_task(
            task_description=args.task or "OpenEarthAgent Task",
            steps=steps,
        ))

        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python -m open_earth_engine --steps steps.json")


if __name__ == "__main__":
    run_cli()

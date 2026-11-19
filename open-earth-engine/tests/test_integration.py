import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_earth_engine.orchestrator import (
    SpaceOrchestrator,
    OrchestratorConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("oea.integration_test")


async def test_full_workflow():
    logger.info("Starting full integration test...")

    config = OrchestratorConfig(
        use_mock_bridge=True,
        max_parallel=4,
        enable_cache=True,
    )

    orchestrator = SpaceOrchestrator(config)

    await orchestrator.initialize()

    steps = [
        {
            "name": "下载 Sentinel-2 影像",
            "tool": "rs_download",
            "tool_id": "rs-agent.rs_download",
            "args": {
                "sensor": "sentinel2",
                "aoi": "Beijing",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "max_cloud_cover": 20,
            },
        },
        {
            "name": "影像预处理",
            "tool": "rs_preprocess",
            "tool_id": "rs-agent.rs_preprocess",
            "args": {
                "operations": ["radiometric_correction", "clip"],
            },
            "dependencies": ["node_000"],
        },
        {
            "name": "NDVI 计算",
            "tool": "rs_analyze",
            "tool_id": "rs-agent.rs_analyze",
            "args": {
                "analysis_type": "ndvi",
            },
            "dependencies": ["node_001"],
        },
    ]

    def on_progress(update):
        logger.info(f"Progress: {update['node_id']} - {update['status']}")

    result = await orchestrator.orchestrate(
        task_description="计算北京 Sentinel-2 影像的 NDVI",
        steps=steps,
        workspace_id="test_workspace",
        on_progress=on_progress,
    )

    logger.info(f"Result: {result}")

    assert result["success"]
    assert result["succeeded_count"] > 0
    assert result["failed_count"] == 0

    await orchestrator.close()

    logger.info("Integration test passed!")
    return result


def test_parallel_workflow():
    logger.info("Testing parallel workflow...")

    config = OrchestratorConfig(
        use_mock_bridge=True,
        max_parallel=4,
    )

    orchestrator = SpaceOrchestrator(config)

    async def run():
        await orchestrator.initialize()

        steps = [
            {
                "name": "下载影像 1",
                "tool_id": "rs-agent.rs_download",
                "args": {"input_path": "/data/scene1.tif"},
            },
            {
                "name": "下载影像 2",
                "tool_id": "rs-agent.rs_download",
                "args": {"input_path": "/data/scene2.tif"},
            },
            {
                "name": "下载影像 3",
                "tool_id": "rs-agent.rs_download",
                "args": {"input_path": "/data/scene3.tif"},
            },
        ]

        result = await orchestrator.orchestrate(
            task_description="批量下载多景影像",
            steps=steps,
        )

        await orchestrator.close()
        return result

    result = asyncio.run(run())

    assert result["success"]
    logger.info("Parallel workflow test passed!")
    return result


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OpenEarthAgent Integration Tests")
    logger.info("=" * 60)

    result1 = asyncio.run(test_full_workflow())
    print(f"\nFull Workflow Result: {result1}\n")

    result2 = test_parallel_workflow()
    print(f"\nParallel Workflow Result: {result2}\n")

    logger.info("All integration tests passed!")

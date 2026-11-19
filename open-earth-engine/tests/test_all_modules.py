import asyncio
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_earth_engine.types.dag_types import (
    DagGraph,
    DagNode,
    NodeStatus,
    NodeMetadata,
)
from open_earth_engine.orchestrator.cache_manager import (
    CacheManager,
    CacheConfig,
    CacheBackendType,
    CacheMetadata,
)
from open_earth_engine.orchestrator.parallel_optimizer import (
    ParallelOptimizer,
    ResourceMonitor,
    ParallelGroupType,
)
from open_earth_engine.registry.mcp_bridge import McpBridgeClient, BridgeResult
from open_earth_engine.registry.unified_tool_registry import (
    UnifiedToolRegistry,
    ExecutionMode,
)
from open_earth_engine.registry.cache_db import CacheDatabase
from open_earth_engine.migration.workflow_converter import (
    WorkflowConverter,
    LegacyRsAgentTask,
)
from open_earth_engine.migration.legacy_compat import LegacyScriptAdapter


class TestDagTypes(unittest.TestCase):
    def test_dag_node_creation(self):
        node = DagNode(
            node_id="test_001",
            name="Test Node",
            tool_name="rs_download",
            execution_mode="mcp",
        )
        self.assertEqual(node.status, NodeStatus.PENDING)
        self.assertEqual(node.parallelizable, False)

    def test_dag_graph_add_node(self):
        dag = DagGraph(graph_id="test_dag")
        node = DagNode(node_id="n1", name="Node 1")
        dag.add_node(node)
        self.assertIn("n1", dag.nodes)

    def test_dag_get_ready_nodes(self):
        dag = DagGraph(graph_id="test_ready")

        node1 = DagNode(node_id="n1", name="Node 1", status=NodeStatus.SUCCEEDED)
        node2 = DagNode(node_id="n2", name="Node 2", dependencies=["n1"])

        dag.add_node(node1)
        dag.add_node(node2)

        ready = dag.get_ready_nodes()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].node_id, "n2")


class TestCacheManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = CacheConfig(
            backend_type=CacheBackendType.LOCAL,
            local_root=self.temp_dir,
        )
        self.cache = CacheManager(self.config)

    def test_cache_key_generation(self):
        key1 = self.cache.get_cache_key(
            source_file="/data/image.tif",
            operation="ndvi",
            params={"band_nir": 8, "band_red": 4},
        )
        key2 = self.cache.get_cache_key(
            source_file="/data/image.tif",
            operation="ndvi",
            params={"band_nir": 8, "band_red": 4},
        )
        self.assertEqual(key1, key2)

        key3 = self.cache.get_cache_key(
            source_file="/data/image.tif",
            operation="ndwi",
            params={},
        )
        self.assertNotEqual(key1, key3)

    def test_local_backend_exists(self):
        async def test():
            key = "test1234567890"
            exists = await self.cache.backend.exists(key)
            self.assertFalse(exists)

        asyncio.run(test())


class TestParallelOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = ParallelOptimizer({"min_parallel_size": 2})

    def test_detect_multi_scene_parallel(self):
        dag = DagGraph(graph_id="test_parallel")

        for i in range(3):
            node = DagNode(
                node_id=f"scene_{i}",
                name=f"下载影像 {i}",
                tool_name="rs_download",
                tool_args={"input_path": f"/data/scene_{i}.tif"},
                metadata=NodeMetadata(),
            )
            dag.add_node(node)

        optimized = self.optimizer.optimize(dag)

        parallel_nodes = [
            n for n in optimized.nodes.values()
            if n.metadata.parallelizable
        ]

        self.assertGreater(len(parallel_nodes), 0)


class TestMcpBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = McpBridgeClient(use_mock=True)

    def test_mock_execution(self):
        async def test():
            result = await self.bridge.execute_tool(
                tool_id="rs-agent.rs_download",
                args={"sensor": "sentinel2", "aoi": "Beijing"},
            )
            self.assertTrue(result.success)
            self.assertIsNotNone(result.result)

        asyncio.run(test())

    def test_list_tools_mock(self):
        async def test():
            tools = await self.bridge.list_tools()
            self.assertGreater(len(tools), 0)

        asyncio.run(test())


class TestUnifiedToolRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = UnifiedToolRegistry({
            "use_mock_bridge": True,
        })

    def test_initialize_registry(self):
        async def test():
            await self.registry.initialize()
            tools = self.registry.list_tools()
            self.assertGreater(len(tools), 0)

        asyncio.run(test())

    def test_tool_matching(self):
        async def test():
            await self.registry.initialize()
            matched = self.registry.match_tool("下载 Sentinel-2 影像", "Sentinel-2")
            self.assertIsNotNone(matched)

        asyncio.run(test())


class TestCacheDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.mktemp(suffix=".json")
        self.db = CacheDatabase(db_path=self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_record_cache(self):
        entry = self.db.record_cache(
            cache_key="abc123",
            source_file="/data/test.tif",
            operation="ndvi",
            params={},
            file_size=1024,
        )
        self.assertEqual(entry.cache_key, "abc123")

    def test_get_hot_cache(self):
        for i in range(10):
            self.db.record_cache(
                cache_key=f"key_{i}",
                source_file=f"/data/{i}.tif",
                operation="ndvi",
                params={},
                file_size=1024,
            )

        hot = self.db.get_hot_cache_keys(min_access_count=1, limit=5)
        self.assertEqual(len(hot), 5)


class TestWorkflowConverter(unittest.TestCase):
    def setUp(self):
        self.converter = WorkflowConverter()

    def test_convert_simple_chain(self):
        legacy_task = LegacyRsAgentTask(
            task_id="test_task",
            description="Test conversion",
            steps=[
                {
                    "tool": "rs_download",
                    "args": {"sensor": "sentinel2", "aoi": "Beijing"},
                    "output_var": "downloaded",
                },
                {
                    "tool": "rs_preprocess",
                    "args": {"input_path": "{{downloaded}}", "operations": ["clip"]},
                },
            ],
        )

        converted = self.converter.convert_rs_agent_task(legacy_task)

        self.assertEqual(len(converted.nodes), 2)
        self.assertGreater(len(converted.edges), 0)

    def test_tool_mapping(self):
        self.assertEqual(
            WorkflowConverter.TOOL_MAPPING["rs_download"],
            "rs-agent.rs_download",
        )
        self.assertEqual(
            WorkflowConverter.TOOL_MAPPING["calculate_ndvi"],
            "rs-index.ndvi_calc",
        )


class TestLegacyScriptAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = LegacyScriptAdapter()

    def test_adapt_script_with_legacy_api(self):
        legacy_code = """
import numpy as np

result = calculate_ndvi(nir_band, red_band)
print(f"NDVI calculated: {result.shape}")
"""

        adapted = self.adapter.adapt_script(legacy_code)

        self.assertIn("OpenEarthAgent 脚本自动适配", adapted)
        self.assertIn("rs_engine.earth_agent_tools", adapted)

    def test_analyze_script(self):
        safe_code = """
result = calculate_ndvi(nir, red)
"""

        analysis = self.adapter.analyze_script(safe_code)
        self.assertTrue(analysis["uses_legacy_tools"])
        self.assertIn("calculate_ndvi", analysis["legacy_apis"])

    def test_analyze_dangerous_code(self):
        dangerous_code = """
import subprocess
result = subprocess.run(["rm", "-rf", "/tmp"])
"""

        analysis = self.adapter.analyze_script(dangerous_code)
        self.assertGreater(len(analysis["warnings"]), 0)


class TestResourceMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = ResourceMonitor()

    def test_get_snapshot(self):
        async def test():
            snapshot = await self.monitor.get_snapshot()
            self.assertGreater(snapshot.cpu_total, 0)
            self.assertGreater(snapshot.memory_total_gb, 0)

        asyncio.run(test())


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
New Modules Unit Tests

Tests for:
- TaskRouter (任务路由)
- TaskDecomposer (任务分解)
- WorkingMemory (工作内存)
- KnowledgeBase (知识库)
"""

import asyncio
import logging

from open_earth_engine.logging_config import setup_logging

setup_logging(level=logging.INFO)
logger = logging.getLogger("oea.new_modules_test")


def test_task_router():
    """Test TaskRouter - 任务路由测试"""
    logger.info("=" * 60)
    logger.info("Testing TaskRouter")
    logger.info("=" * 60)

    from open_earth_engine.planner.task_router import TaskRouter, TaskRoute, RouterConfig

    router = TaskRouter()

    test_cases = [
        {
            "name": "简单任务 - 标准路由",
            "task": "下载一景 Sentinel-2 影像",
            "expected_route": TaskRoute.STANDARD,
        },
        {
            "name": "多源数据 - OpenEarth 路由",
            "task": "同时使用 SAR 雷达影像、光学影像和矢量数据进行叠加分析",
            "expected_route": TaskRoute.OPEN_EARTH,
        },
        {
            "name": "自定义 GIS - OpenEarth 路由",
            "task": "对影像进行缓冲区分析，然后与矢量图层相交，最后计算分区统计",
            "expected_route": TaskRoute.OPEN_EARTH,
        },
        {
            "name": "多步骤任务 - OpenEarth 路由",
            "task": "第一步下载影像，第二步进行大气校正，第三步计算 NDVI，第四步进行分类，第五步输出结果",
            "expected_route": TaskRoute.OPEN_EARTH,
        },
        {
            "name": "时序融合分析 - OpenEarth 路由",
            "task": "对2023年和2024年的时序影像进行变化检测，然后分区统计变化区域",
            "expected_route": TaskRoute.OPEN_EARTH,
        },
        {
            "name": "NDVI 标准流程 - 标准路由",
            "task": "计算 NDVI 植被指数",
            "expected_route": TaskRoute.STANDARD,
        },
    ]

    passed = 0
    for tc in test_cases:
        complexity = router.route(tc["task"])
        is_match = complexity.route == tc["expected_route"]
        status = "✓" if is_match else "✗"
        logger.info(f"{status} {tc['name']}: {complexity.route.value} (expected: {tc['expected_route'].value})")
        if complexity.reasons:
            logger.info(f"   Reasons: {complexity.reasons}")
        if is_match:
            passed += 1

    logger.info(f"\nTaskRouter: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_task_router_manual_override():
    """Test TaskRouter manual override"""
    logger.info("\nTesting TaskRouter Manual Override")

    from open_earth_engine.planner.task_router import TaskRouter, TaskRoute

    router = TaskRouter()

    complexity = router.route(
        "简单任务",
        manual_override=TaskRoute.OPEN_EARTH,
    )
    assert complexity.route == TaskRoute.OPEN_EARTH
    logger.info("✓ Manual override to OPEN_EARTH works")

    complexity = router.route(
        "复杂任务",
        manual_override=TaskRoute.STANDARD,
    )
    assert complexity.route == TaskRoute.STANDARD
    logger.info("✓ Manual override to STANDARD works")

    return True


def test_task_decomposer():
    """Test TaskDecomposer - 任务分解测试"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing TaskDecomposer")
    logger.info("=" * 60)

    from open_earth_engine.planner.task_decomposer import TaskDecomposer, DecomposerConfig

    decomposer = TaskDecomposer(DecomposerConfig(use_mock=True))

    test_cases = [
        {
            "name": "NDVI 任务",
            "task": "计算北京地区 Sentinel-2 影像的 NDVI 植被指数",
            "min_steps": 2,
        },
        {
            "name": "水体指数任务",
            "task": "提取水体范围，计算 NDWI 指数",
            "min_steps": 2,
        },
        {
            "name": "变化检测任务",
            "task": "对两个时相的影像进行变化检测",
            "min_steps": 3,
        },
        {
            "name": "通用分析任务",
            "task": "下载影像然后进行分析计算",
            "min_steps": 2,
        },
    ]

    passed = 0
    for tc in test_cases:
        steps = asyncio.run(decomposer.decompose(tc["task"]))
        is_valid = len(steps) >= tc["min_steps"]
        status = "✓" if is_valid else "✗"
        logger.info(f"{status} {tc['name']}: {len(steps)} steps (expected >= {tc['min_steps']})")
        for step in steps:
            logger.info(f"   Step {step.step_number}: {step.description} [{step.execution_mode}]")
        if is_valid:
            passed += 1

    logger.info(f"\nTaskDecomposer: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_task_decomposer_force_steps():
    """Test TaskDecomposer with force_steps"""
    logger.info("\nTesting TaskDecomposer Force Steps")

    from open_earth_engine.planner.task_decomposer import TaskDecomposer

    decomposer = TaskDecomposer()

    force_steps = [
        {"name": "自定义步骤1", "tool": "custom_tool_1"},
        {"name": "自定义步骤2", "tool": "custom_tool_2", "dependencies": ["step_000"]},
    ]

    steps = asyncio.run(decomposer.decompose("task", force_steps=force_steps))
    assert len(steps) == 2
    assert steps[1].dependencies == ["step_000"]
    logger.info("✓ Force steps works correctly")

    return True


def test_working_memory():
    """Test WorkingMemory - 工作内存测试"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing WorkingMemory")
    logger.info("=" * 60)

    from open_earth_engine.memory.working_memory import WorkingMemory, MemoryConfig

    memory = WorkingMemory(task_id="test_task_001")

    logger.info("Adding task info...")
    memory.add_task_info("计算 NDVI 指数", {"sensor": "Sentinel-2", "region": "Beijing"})

    logger.info("Adding step progress...")
    memory.add_step_progress("step_000", 1, "running", {"progress": 50})

    logger.info("Adding tool result...")
    memory.add_tool_result(
        "rs-agent.rs_download",
        {"success": True},
        step_id="step_000",
        output_files=["/tmp/output.tif"],
    )

    logger.info("Adding observation...")
    memory.add_observation("云量较低，适合分析", source="system")

    logger.info("Testing retrieval...")

    recent = memory.get_recent(limit=5)
    assert len(recent) >= 4
    logger.info(f"✓ get_recent works: {len(recent)} entries")

    tool_results = memory.get_by_type("tool_result")
    assert len(tool_results) == 1
    logger.info(f"✓ get_by_type works: {len(tool_results)} tool results")

    step_entries = memory.get_by_step("step_000")
    assert len(step_entries) >= 1
    logger.info(f"✓ get_by_step works: {len(step_entries)} entries for step_000")

    search_results = memory.search("NDVI")
    assert len(search_results) >= 1
    logger.info(f"✓ search works: {len(search_results)} results for 'NDVI'")

    context = memory.build_context(max_tokens=2000)
    assert len(context) > 0
    logger.info(f"✓ build_context works: context length = {len(context)}")

    summary = memory.get_summary()
    assert summary["task_id"] == "test_task_001"
    logger.info(f"✓ get_summary works: total_entries = {summary['total_entries']}")

    history = memory.get_tool_history()
    assert len(history) == 1
    logger.info(f"✓ get_tool_history works: {len(history)} executions")

    return True


def test_working_memory_pruning():
    """Test WorkingMemory pruning"""
    logger.info("\nTesting WorkingMemory Pruning")

    from open_earth_engine.memory.working_memory import WorkingMemory, MemoryConfig

    config = MemoryConfig(max_entries=10, enable_pruning=True)
    memory = WorkingMemory(task_id="prune_test", config=config)

    for i in range(20):
        memory.add_observation(f"Observation {i}", importance=i % 3)

    summary = memory.get_summary()
    assert summary["total_entries"] <= 10
    logger.info(f"✓ Pruning works: {summary['total_entries']} entries after adding 20")

    return True


def test_knowledge_base():
    """Test KnowledgeBase - 知识库测试"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing KnowledgeBase")
    logger.info("=" * 60)

    from open_earth_engine.knowledge.knowledge_base import KnowledgeBase, KnowledgeBaseConfig

    kb = KnowledgeBase()

    logger.info("Testing tool fallback...")
    fallback = kb.get_fallback("rs-agent.rs_download")
    assert fallback is not None
    assert fallback.fallback_tool == "sandbox.gdal_download"
    logger.info(f"✓ Tool fallback found: {fallback.fallback_tool}")

    recommendation = kb.get_fallback_recommendation("rs-agent.rs_download", "Connection error")
    assert recommendation is not None
    assert recommendation["recommended_fallback"] == "sandbox.gdal_download"
    logger.info(f"✓ Fallback recommendation generated")

    logger.info("\nTesting search...")
    ndvi_results = kb.search("NDVI")
    assert len(ndvi_results) >= 1
    logger.info(f"✓ Search 'NDVI': {len(ndvi_results)} results")

    spectral_results = kb.search_by_tags(["spectral"])
    assert len(spectral_results) >= 2
    logger.info(f"✓ Search by tag 'spectral': {len(spectral_results)} results")

    logger.info("\nTesting tool documentation...")
    tool_doc = kb.get_tool_doc("rs-agent.rs_download")
    assert tool_doc is not None
    logger.info(f"✓ Tool documentation found: {tool_doc.title}")

    logger.info("\nTesting geospatial knowledge...")
    geo_knowledge = kb.get_geospatial_knowledge("坐标系")
    assert len(geo_knowledge) >= 1
    logger.info(f"✓ Geospatial knowledge search: {len(geo_knowledge)} results")

    logger.info("\nTesting best practices...")
    practices = kb.get_best_practices("变化检测")
    assert len(practices) >= 1
    logger.info(f"✓ Best practices search: {len(practices)} results")

    logger.info("\nTesting custom entry...")
    custom_entry = kb.add_entry(
        entry_type="custom",
        title="自定义知识",
        content="这是一条自定义的知识条目",
        tags=["custom", "test"],
        importance=5,
    )
    assert custom_entry is not None
    logger.info(f"✓ Custom entry added: {custom_entry.entry_id}")

    summary = kb.get_summary()
    logger.info(f"\n✓ KnowledgeBase summary: {summary['total_entries']} entries, "
                f"{summary['tool_fallbacks_count']} fallbacks")

    return True


def test_all_new_modules():
    """Run all new module tests"""
    logger.info("\n" + "=" * 60)
    logger.info("New Modules Test Suite")
    logger.info("=" * 60)

    tests = [
        ("TaskRouter", test_task_router),
        ("TaskRouter Manual Override", test_task_router_manual_override),
        ("TaskDecomposer", test_task_decomposer),
        ("TaskDecomposer Force Steps", test_task_decomposer_force_steps),
        ("WorkingMemory", test_working_memory),
        ("WorkingMemory Pruning", test_working_memory_pruning),
        ("KnowledgeBase", test_knowledge_base),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"\n✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{status}: {name}")

    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = test_all_new_modules()
    exit(0 if success else 1)

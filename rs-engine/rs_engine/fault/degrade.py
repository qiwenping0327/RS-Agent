"""
故障容错层 - 降级策略

当主处理方式失败时，自动降级到备选方案。
"""

import logging
from typing import Any, Callable

logger = logging.getLogger("rs-engine.fault")


# 降级策略注册表
_DEGRADE_STRATEGIES: dict[str, list[Callable]] = {}


def register_degrade_strategy(tool_name: str, fallback: Callable) -> None:
    """
    注册降级策略

    Args:
        tool_name: 工具名称
        fallback: 降级处理函数
    """
    if tool_name not in _DEGRADE_STRATEGIES:
        _DEGRADE_STRATEGIES[tool_name] = []
    _DEGRADE_STRATEGIES[tool_name].append(fallback)


async def try_degrade(tool_name: str, error: Exception, original_input: dict) -> dict[str, Any] | None:
    """
    尝试执行降级策略

    Args:
        tool_name: 工具名称
        error: 原始错误
        original_input: 原始输入参数

    Returns:
        降级结果，无可用策略时返回 None
    """
    strategies = _DEGRADE_STRATEGIES.get(tool_name, [])

    if not strategies:
        logger.warning("工具 %s 无可用降级策略", tool_name)
        return None

    for i, strategy in enumerate(strategies):
        try:
            logger.info(
                "工具 %s 执行降级策略 #%d (共 %d 个)",
                tool_name,
                i + 1,
                len(strategies),
            )
            result = await strategy(error, original_input)
            if result is not None:
                result["_degraded"] = True
                result["_degrade_strategy"] = i + 1
                return result
        except Exception as degrade_error:
            logger.warning(
                "降级策略 #%d 执行失败: %s", i + 1, str(degrade_error)[:200]
            )
            continue

    return None


# ---------------------------------------------------------------------------
# 内置降级策略
# ---------------------------------------------------------------------------


async def _download_degrade_lower_resolution(error: Exception, original_input: dict) -> dict[str, Any] | None:
    """
    下载降级: 降低分辨率要求

    将高分数据降级为较低分辨率数据源
    """
    sensor = original_input.get("sensor", "")
    degrade_map = {
        "gf2": "gf1",   # 1m -> 2m
        "gf1": "sentinel2",  # 8m -> 10m
        "sentinel2": "landsat8",  # 10m -> 30m
    }

    if sensor in degrade_map:
        degraded_sensor = degrade_map[sensor]
        logger.info("下载降级: %s -> %s", sensor, degraded_sensor)
        return {
            "sensor": degraded_sensor,
            "message": f"由于 {error}，已降级为 {degraded_sensor} 数据源",
        }

    return None


async def _analyze_degrade_simpler_method(error: Exception, original_input: dict) -> dict[str, Any] | None:
    """
    分析降级: 使用更简单的分析方法

    深度学习方法 -> 传统指数方法
    """
    analysis_type = original_input.get("analysis_type", "")

    # 分类降级为指数分析
    if analysis_type == "classification":
        logger.info("分析降级: classification -> ndvi")
        return {
            "analysis_type": "ndvi",
            "message": "分类分析不可用，已降级为 NDVI 指数分析",
        }

    # 变化检测降级为双时相对比
    if analysis_type == "change_detection":
        logger.info("分析降级: change_detection -> ndvi 差值法")
        return {
            "analysis_type": "ndvi",
            "params": {"method": "diff"},
            "message": "变化检测不可用，已降级为 NDVI 差值法",
        }

    return None


# 注册内置降级策略
register_degrade_strategy("rs_download", _download_degrade_lower_resolution)
register_degrade_strategy("rs_analyze", _analyze_degrade_simpler_method)

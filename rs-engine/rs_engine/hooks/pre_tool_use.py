"""
PreToolUse Hook 处理器

在遥感工具执行前进行参数校验和资源检查。

Hook 输出效果:
- updatedInput: 修改工具参数（参数自动补全）
- block: 阻止工具执行（参数校验失败或资源不足）
"""

import logging
import os
from typing import Any

from rs_engine.resource.quota import QuotaChecker, ResourceQuota
from rs_engine.resource.disk import DiskManager

logger = logging.getLogger("rs-engine.hooks")

# 全局资源检查器（延迟初始化）
_quota_checker: QuotaChecker | None = None


def _get_quota_checker() -> QuotaChecker:
    """获取全局资源检查器（懒加载）"""
    global _quota_checker
    if _quota_checker is None:
        workspace = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))
        _quota_checker = QuotaChecker(workspace)
    return _quota_checker


async def handle_pre_tool_use(hook_input: dict[str, Any]) -> dict[str, Any]:
    """
    处理 PreToolUse Hook

    1. 参数校验 - 检查必填参数和参数格式
    2. 资源检查 - 检查 CPU/GPU/磁盘配额
    3. 参数补全 - 自动补全默认参数

    Args:
        hook_input: Hook 输入，包含 toolName, toolInput 等字段

    Returns:
        Hook 输出，可包含 updatedInput 或 block
    """
    tool_name = hook_input.get("toolName", "")
    tool_input = hook_input.get("toolInput", {})

    logger.info("pre_tool_use: tool=%s, input=%s", tool_name, str(tool_input)[:200])

    # 提取短工具名 (mcp__rs_agent__rs_download -> rs_download)
    short_name = tool_name.rsplit("__", 1)[-1] if "__" in tool_name else tool_name

    # 1. 参数校验
    validation_error = _validate_params(short_name, tool_input)
    if validation_error:
        logger.warning("参数校验失败: %s", validation_error)
        return {"decision": "block", "reason": validation_error}

    # 2. 资源检查
    resource_ok, resource_msg = await _check_resources(short_name, tool_input)
    if not resource_ok:
        logger.warning("资源检查失败: %s", resource_msg)
        return {"decision": "block", "reason": resource_msg}

    # 3. 参数补全
    updated = _auto_complete_params(short_name, tool_input)
    if updated:
        logger.info("参数已补全: %s", updated)
        return {"hookSpecificOutput": {"updatedInput": updated}}

    return {}


def _validate_params(tool_name: str, tool_input: dict) -> str | None:
    """参数校验，返回错误信息或 None"""
    validators = {
        "rs_download": _validate_download,
        "rs_preprocess": _validate_preprocess,
        "rs_analyze": _validate_analyze,
    }

    validator = validators.get(tool_name)
    if validator:
        return validator(tool_input)
    return None


def _validate_download(params: dict) -> str | None:
    """校验 rs_download 参数"""
    if not params.get("sensor"):
        return "缺少必填参数: sensor"
    if not params.get("aoi"):
        return "缺少必填参数: aoi"
    if not params.get("start_date"):
        return "缺少必填参数: start_date"
    if not params.get("end_date"):
        return "缺少必填参数: end_date"

    # 校验传感器名称
    valid_sensors = ["sentinel2", "landsat8", "gf1", "gf2"]
    if params["sensor"] not in valid_sensors:
        return f"不支持的传感器: {params['sensor']}，支持: {', '.join(valid_sensors)}"

    # 校验 AOI 格式
    aoi = params["aoi"]
    if isinstance(aoi, dict) and "type" not in aoi:
        return "AOI 格式错误: 缺少 type 字段 (需要 GeoJSON 格式)"

    return None


def _validate_preprocess(params: dict) -> str | None:
    """校验 rs_preprocess 参数"""
    if not params.get("input_path"):
        return "缺少必填参数: input_path"
    if not params.get("operations"):
        return "缺少必填参数: operations"
    return None


def _validate_analyze(params: dict) -> str | None:
    """校验 rs_analyze 参数"""
    if not params.get("input_path"):
        return "缺少必填参数: input_path"
    if not params.get("analysis_type"):
        return "缺少必填参数: analysis_type"
    return None


def _auto_complete_params(tool_name: str, tool_input: dict) -> dict | None:
    """参数自动补全，返回补全后的参数或 None"""
    updated = {}

    if tool_name == "rs_download":
        if "max_cloud_cover" not in tool_input:
            updated["max_cloud_cover"] = 20
        if "output_dir" not in tool_input:
            sensor = tool_input.get("sensor", "sentinel2")
            updated["output_dir"] = os.path.join(os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')), "downloads", sensor)

    elif tool_name == "rs_analyze":
        analysis_type = tool_input.get("analysis_type", "")
        # 根据分析类型自动补全波段映射
        if analysis_type == "ndvi" and "params" not in tool_input:
            updated["params"] = {"red_band": "B04", "nir_band": "B08"}

    if updated:
        return {**tool_input, **updated}
    return None


async def _check_resources(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    """
    资源检查

    检查磁盘空间和 GPU 可用性。

    Returns:
        (是否通过, 描述信息)
    """
    checker = _get_quota_checker()
    return await checker.check(tool_name, tool_input)

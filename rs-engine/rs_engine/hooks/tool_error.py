"""
PostToolUseFailure Hook 处理器

当遥感工具执行失败时，提供故障诊断、降级建议和重试指引。

Hook 输出效果:
- additionalContext: 附加故障诊断信息和降级建议
- retry: 建议重试 (实际重试逻辑在 MCP Server 工具内部实现)

集成:
- 故障解决方案库 (fault_solutions.json)
- 降级策略 (degrade.py)
- RAG 知识检索
"""

import json
import logging
import os
from typing import Any

from rs_engine.fault.degrade import try_degrade

logger = logging.getLogger("rs-engine.hooks")

# 故障解决方案库路径
FAULT_SOLUTIONS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "fault_solutions.json"
)


def _load_fault_solutions() -> list[dict[str, Any]]:
    """加载故障解决方案库"""
    try:
        with open(FAULT_SOLUTIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("fault_solutions", [])
    except Exception:
        return []


FAULT_SOLUTIONS = _load_fault_solutions()


async def handle_tool_error(hook_input: dict[str, Any]) -> dict[str, Any]:
    """
    处理 PostToolUseFailure Hook

    1. 记录错误日志
    2. 从解决方案库匹配诊断信息
    3. 尝试降级策略
    4. 提供故障解决方案上下文

    Args:
        hook_input: Hook 输入，包含 toolName, error 等字段

    Returns:
        Hook 输出，可包含 additionalContext
    """
    tool_name = hook_input.get("toolName", "")
    error = hook_input.get("error", "未知错误")
    tool_input = hook_input.get("toolInput", {})

    logger.error("tool_error: tool=%s, error=%s", tool_name, error)

    # 提取短工具名
    short_name = tool_name.rsplit("__", 1)[-1] if "__" in tool_name else tool_name

    # 1. 从解决方案库匹配
    solution = _match_fault_solution(short_name, str(error))

    # 2. 尝试降级策略
    degrade_result = await try_degrade(short_name, Exception(str(error)), tool_input)
    degrade_info = ""
    if degrade_result:
        degrade_info = (
            f"\n降级方案: 已找到替代方案\n"
            f"  降级参数: {degrade_result}\n"
            f"  建议: 使用上述降级参数重新调用工具"
        )

    # 3. 生成上下文
    context_parts = [
        f"[遥感智能体故障诊断] 工具 {tool_name} 执行失败:",
        f"错误: {error}",
    ]

    if solution:
        context_parts.append(f"诊断: {solution['diagnosis']}")
        context_parts.append(f"解决方案: {solution['solution']}")
        context_parts.append(f"严重程度: {solution['severity']}")
    else:
        context_parts.append(f"诊断: {_diagnose_error(short_name, str(error))}")

    if degrade_info:
        context_parts.append(degrade_info)

    context_parts.append("建议: 请根据诊断信息调整参数后重试。")

    context = "\n".join(context_parts)
    return {"hookSpecificOutput": {"additionalContext": context}}


def _match_fault_solution(tool_name: str, error: str) -> dict[str, Any] | None:
    """
    从故障解决方案库匹配

    Args:
        tool_name: 工具名称
        error: 错误信息

    Returns:
        匹配的解决方案，无匹配返回 None
    """
    error_lower = error.lower()

    for solution in FAULT_SOLUTIONS:
        # 检查工具匹配
        pattern_tool = solution.get("tool", "*")
        if pattern_tool != "*" and pattern_tool != tool_name:
            continue

        # 检查错误模式匹配
        patterns = solution.get("error_pattern", "").split("|")
        if any(p.strip().lower() in error_lower for p in patterns):
            return solution

    return None


def _diagnose_error(tool_name: str, error: str) -> str:
    """根据错误信息诊断故障原因（fallback）"""
    error_lower = error.lower()

    if any(kw in error_lower for kw in ["timeout", "connection", "network", "refused"]):
        return "网络连接失败，可能是数据源服务不可用。建议检查网络连接后重试。"

    if any(kw in error_lower for kw in ["disk", "space", "no space left", "enospc"]):
        return "磁盘空间不足。建议清理工作空间或更换输出目录。"

    if any(kw in error_lower for kw in ["permission", "denied", "eacces", "forbidden"]):
        return "权限不足。建议检查文件/目录权限，或检查 API 凭证是否有效。"

    if any(kw in error_lower for kw in ["invalid", "value", "parameter", "argument"]):
        return "参数错误。建议检查输入参数格式和取值范围。"

    if any(kw in error_lower for kw in ["memory", "oom", "out of memory"]):
        return "内存不足。建议减小处理区域范围或降低分辨率。"

    tool_errors = {
        "rs_download": "影像下载失败。建议检查 AOI 范围、日期范围和传感器名称是否正确。",
        "rs_preprocess": "预处理失败。建议检查输入文件格式和预处理参数。",
        "rs_analyze": "分析失败。建议检查输入数据和分析参数。",
    }

    return tool_errors.get(tool_name, "未知错误类型，请查看详细日志。")

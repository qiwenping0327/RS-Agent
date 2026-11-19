"""
UserPromptSubmit Hook 处理器

当用户提交遥感相关提示时，为 LLM 附加遥感任务上下文信息，
帮助 LLM 选择合适的遥感工具和工作流。
"""

import logging
from typing import Any

logger = logging.getLogger("rs-engine.hooks")


async def handle_route_task(hook_input: dict[str, Any]) -> dict[str, Any]:
    """
    处理 UserPromptSubmit Hook

    分析用户输入，判断是否为遥感任务，附加上下文信息。

    Args:
        hook_input: Hook 输入，包含 sessionId, cwd, prompt 等字段

    Returns:
        Hook 输出，可包含 additionalContext 字段
    """
    prompt = hook_input.get("prompt", "")
    logger.info("route_task: prompt=%s", prompt[:100])

    # 遥感关键词检测
    rs_keywords = [
        "遥感", "卫星", "影像", "sentinel", "landsat", "高分",
        "ndvi", "ndwi", "sar", "insar", "radar",
        "download", "preprocess", "classify", "detect",
        "geotiff", "shapefile", "geojson", "crs", "projection",
        "raster", "vector", "polygon", "aoi",
    ]

    prompt_lower = prompt.lower()
    is_rs_task = any(kw in prompt_lower for kw in rs_keywords)

    if not is_rs_task:
        return {}

    # 构建智能上下文提示，引导 Agent 直接调用工具而非反复询问
    context = _build_context(prompt)

    return {"hookSpecificOutput": {"additionalContext": context}}


def _build_context(prompt: str) -> str:
    """
    根据用户输入构建上下文提示

    分析用户意图，生成具体的工作流建议和参数预填，
    引导 Agent 直接调用 MCP 工具而非反复询问用户。
    """
    from rs_engine.knowledge import resolve_aoi

    prompt_lower = prompt.lower()

    # 尝试从用户输入中提取 AOI
    aoi_hint = ""
    import re
    # 从"地区/市"等后缀前的文本中提取地名候选，逐个验证
    candidates = re.findall(r'([\u4e00-\u9fa5]{2,4})(?:地区|市|区域|周边|附近)', prompt)
    if not candidates:
        candidates = re.findall(r'([\u4e00-\u9fa5]{2,3})(?:的)', prompt)
    if not candidates:
        # 尝试直接找 2-3 字中文词
        candidates = re.findall(r'[\u4e00-\u9fa5]{2,3}', prompt)
        # 过滤掉常见动词
        verbs = {'搜索','查找','下载','分析','获取','寻找','处理','观测','帮我','请问','想要','需要','执行','进行','计算','生成'}
        candidates = [c for c in candidates if c not in verbs]
    # 遍历候选地名，尝试解析
    for candidate in candidates:
        # 尝试完整候选
        try:
            aoi = resolve_aoi(candidate)
            if aoi:
                import json
                aoi_hint = f"\n- 用户提到的区域「{candidate}」已解析为 GeoJSON: {json.dumps(aoi, ensure_ascii=False)}"
                break
        except Exception:
            pass
        # 候选可能包含动词前缀（如"搜索北京"），尝试截取后 2-3 字
        if len(candidate) > 3:
            for sub_len in (3, 2):
                sub = candidate[-sub_len:]
                try:
                    aoi = resolve_aoi(sub)
                    if aoi:
                        import json
                        aoi_hint = f"\n- 用户提到的区域「{sub}」已解析为 GeoJSON: {json.dumps(aoi, ensure_ascii=False)}"
                        break
                except Exception:
                    pass
            if aoi_hint:
                break

    # 检测传感器意图
    sensor_hint = ""
    if any(kw in prompt_lower for kw in ["sentinel", "哨兵", "s2"]):
        sensor_hint = "\n- 用户意图使用 Sentinel-2 传感器 (sensor='sentinel2')"
    elif any(kw in prompt_lower for kw in ["landsat", "陆地"]):
        sensor_hint = "\n- 用户意图使用 Landsat-8 传感器 (sensor='landsat8')"
    elif any(kw in prompt_lower for kw in ["高分", "gf"]):
        sensor_hint = "\n- 用户意图使用高分系列传感器"

    # 检测分析意图
    analysis_hint = ""
    if any(kw in prompt_lower for kw in ["搜索", "查找", "获取", "下载", "找", "数据"]):
        analysis_hint = "\n- 用户意图搜索/下载数据 → 请直接调用 rs_download 工具"
    elif any(kw in prompt_lower for kw in ["分析", "指数", "ndvi", "ndwi", "分类"]):
        analysis_hint = "\n- 用户意图执行分析 → 请先下载数据再调用 rs_analyze 工具"
    elif any(kw in prompt_lower for kw in ["预处理", "校正", "裁剪", "配准"]):
        analysis_hint = "\n- 用户意图执行预处理 → 请调用 rs_preprocess 工具"

    # 检测时间范围
    time_hint = ""
    year_match = re.search(r"(\d{4})\s*[-年]", prompt)
    if year_match:
        year = year_match.group(1)
        time_hint = f"\n- 用户提到的时间范围包含 {year} 年"

    context = (
        "[遥感智能体上下文] 用户正在执行遥感任务。\n\n"
        "可用 MCP 工具 (wire name 格式: mcp__rs_agent__<tool_name>):\n"
        "- mcp__rs_agent__rs_download: 下载卫星影像 (sensor: sentinel2/landsat8/gf1/gf2)\n"
        "- mcp__rs_agent__rs_preprocess: 影像预处理 (辐射校正/几何校正/裁剪/重采样)\n"
        "- mcp__rs_agent__rs_analyze: 智能分析 (NDVI/NDWI/分类/变化检测)\n"
        "- mcp__rs_agent__rs_visualize: 可视化 (缩略图/真彩色/假彩色/分类结果)\n"
        "- mcp__rs_agent__rs_report: 生成报告 (markdown/html/pdf)\n"
        "- mcp__rs_agent__rs_sar_analysis: SAR 数据分析\n"
        "- mcp__rs_agent__rs_model_inference: AI 模型推理\n\n"
        "重要指引:\n"
        "- 不要反复询问用户参数，而是根据上下文推断合理默认值后直接调用工具\n"
        "- aoi 参数支持中文地名（如 '北京'、'上海'），工具会自动解析为 GeoJSON\n"
        "- 如果用户只说地区名没有指定传感器，默认使用 sentinel2\n"
        "- 如果用户没有指定时间范围，默认使用最近 3 个月\n"
        "- 不要使用 AskUserQuestion，直接调用工具执行任务\n"
        f"{aoi_hint}{sensor_hint}{analysis_hint}{time_hint}"
    )

    return context

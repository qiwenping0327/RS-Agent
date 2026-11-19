"""
遥感知识库 - 空间编码

提供地名/坐标互查、空间编码转换等能力。
"""

import logging
from typing import Any

logger = logging.getLogger("rs-engine.knowledge")

# ---------------------------------------------------------------------------
# 常见遥感区域预设 AOI
# ---------------------------------------------------------------------------
PRESET_AOI: dict[str, dict[str, Any]] = {
    "北京": {
        "type": "Polygon",
        "coordinates": [[[116.0, 39.5], [117.0, 39.5], [117.0, 40.5], [116.0, 40.5], [116.0, 39.5]]],
    },
    "上海": {
        "type": "Polygon",
        "coordinates": [[[121.0, 30.5], [122.0, 30.5], [122.0, 31.5], [121.0, 31.5], [121.0, 30.5]]],
    },
    "广州": {
        "type": "Polygon",
        "coordinates": [[[113.0, 22.5], [114.0, 22.5], [114.0, 23.5], [113.0, 23.5], [113.0, 22.5]]],
    },
    "成都": {
        "type": "Polygon",
        "coordinates": [[[103.5, 30.0], [104.5, 30.0], [104.5, 31.0], [103.5, 31.0], [103.5, 30.0]]],
    },
    "武汉": {
        "type": "Polygon",
        "coordinates": [[[113.5, 29.5], [114.5, 29.5], [114.5, 30.5], [113.5, 30.5], [113.5, 29.5]]],
    },
    "深圳": {
        "type": "Polygon",
        "coordinates": [[[113.5, 22.0], [114.5, 22.0], [114.5, 22.8], [113.5, 22.8], [113.5, 22.0]]],
    },
}

# ---------------------------------------------------------------------------
# 地名别名映射（英文名 / 带后缀中文名 → 标准 PRESET_AOI 键）
# ---------------------------------------------------------------------------
_AOI_ALIASES: dict[str, str] = {
    # 北京别名
    "beijing": "北京", "beijing city": "北京", "peking": "北京",
    "北京地区": "北京", "北京市": "北京", "北京城区": "北京",
    # 上海别名
    "shanghai": "上海", "shanghai city": "上海",
    "上海地区": "上海", "上海市": "上海",
    # 广州别名
    "guangzhou": "广州", "guangzhou city": "广州", "canton": "广州",
    "广州地区": "广州", "广州市": "广州",
    # 成都别名
    "chengdu": "成都", "chengdu city": "成都",
    "成都地区": "成都", "成都市": "成都",
    # 武汉别名
    "wuhan": "武汉", "wuhan city": "武汉",
    "武汉地区": "武汉", "武汉市": "武汉",
    # 深圳别名
    "shenzhen": "深圳", "shenzhen city": "深圳",
    "深圳地区": "深圳", "深圳市": "深圳",
}

# ---------------------------------------------------------------------------
# CRS 坐标参考系统映射
# ---------------------------------------------------------------------------
COMMON_CRS: dict[str, str] = {
    "WGS84": "EPSG:4326",
    "CGCS2000": "EPSG:4490",
    "UTM_49N": "EPSG:32649",
    "UTM_50N": "EPSG:32650",
    "UTM_51N": "EPSG:32651",
    "WGS84_Pseudo_Mercator": "EPSG:3857",
    "GCJ02": "GCJ02",  # 国测局坐标（非标准 EPSG）
}


def resolve_aoi(aoi_input: str | dict) -> dict[str, Any] | None:
    """
    解析 AOI 输入

    支持:
    - GeoJSON 对象直接返回
    - 地名（中文）查找预设 AOI
    - 经纬度字符串 "lon,lat" 转为 Point

    Args:
        aoi_input: AOI 输入

    Returns:
        GeoJSON 对象
    """
    # 直接传入 GeoJSON
    if isinstance(aoi_input, dict):
        if "type" in aoi_input:
            return aoi_input
        return None

    # 字符串输入
    if isinstance(aoi_input, str):
        # 精确地名查找
        if aoi_input in PRESET_AOI:
            return PRESET_AOI[aoi_input]

        # 别名查找（不区分大小写）
        normalized = aoi_input.strip()
        alias_key = _AOI_ALIASES.get(normalized.lower())
        if alias_key and alias_key in PRESET_AOI:
            return PRESET_AOI[alias_key]

        # 模糊匹配：去除"市/地区/城区/省"等后缀后重试
        for suffix in ("地区", "市", "城区", "省", "区域", "市辖区"):
            if normalized.endswith(suffix):
                core = normalized[: -len(suffix)]
                if core in PRESET_AOI:
                    return PRESET_AOI[core]

        # 经纬度格式 "lon,lat" 或 "lon,lat,radius_km"
        parts = aoi_input.split(",")
        if len(parts) >= 2:
            try:
                lon = float(parts[0].strip())
                lat = float(parts[1].strip())
                radius_km = float(parts[2].strip()) if len(parts) > 2 else 10.0

                # 生成缓冲区多边形
                delta = radius_km / 111.0  # 粗略转换
                return {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon - delta, lat - delta],
                            [lon + delta, lat - delta],
                            [lon + delta, lat + delta],
                            [lon - delta, lat + delta],
                            [lon - delta, lat - delta],
                        ]
                    ],
                }
            except (ValueError, IndexError):
                return None

    return None


def get_crs_code(crs_name: str) -> str | None:
    """
    获取 CRS 编码

    Args:
        crs_name: CRS 名称或编码

    Returns:
        EPSG 编码
    """
    # 直接匹配
    if crs_name in COMMON_CRS:
        return COMMON_CRS[crs_name]

    # EPSG 编码直接返回
    if crs_name.upper().startswith("EPSG:"):
        return crs_name

    # 数字编码加前缀
    if crs_name.isdigit():
        return f"EPSG:{crs_name}"

    return None

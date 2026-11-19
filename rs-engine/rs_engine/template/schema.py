"""
任务模板 Schema 定义
"""

from typing import Any


# 模板 JSON Schema
TEMPLATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["id", "name", "tool", "params"],
    "properties": {
        "id": {
            "type": "string",
            "description": "模板唯一标识",
        },
        "name": {
            "type": "string",
            "description": "模板名称",
        },
        "description": {
            "type": "string",
            "description": "模板描述",
        },
        "category": {
            "type": "string",
            "enum": ["download", "preprocess", "analyze", "sar", "model", "visualize", "report"],
            "description": "模板分类",
        },
        "tool": {
            "type": "string",
            "description": "关联的 MCP 工具名称",
        },
        "params": {
            "type": "object",
            "description": "默认参数",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "标签",
        },
        "author": {
            "type": "string",
            "description": "作者",
        },
        "created_at": {
            "type": "string",
            "description": "创建时间",
        },
        "updated_at": {
            "type": "string",
            "description": "更新时间",
        },
    },
}

# 预置模板
BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "sentinel2-ndvi",
        "name": "Sentinel-2 NDVI 分析",
        "description": "下载 Sentinel-2 影像并计算 NDVI 植被指数",
        "category": "analyze",
        "tool": "rs_analyze",
        "params": {
            "sensor": "sentinel2",
            "analysis_type": "ndvi",
            "params": {"red_band": "B04", "nir_band": "B08"},
        },
        "tags": ["sentinel2", "ndvi", "vegetation"],
        "author": "rs-agent",
    },
    {
        "id": "landsat8-download",
        "name": "Landsat-8 影像下载",
        "description": "下载 Landsat-8 卫星影像",
        "category": "download",
        "tool": "rs_download",
        "params": {
            "sensor": "landsat8",
            "max_cloud_cover": 20,
        },
        "tags": ["landsat8", "download"],
        "author": "rs-agent",
    },
    {
        "id": "atmospheric-correction",
        "name": "大气校正",
        "description": "对遥感影像执行大气校正处理",
        "category": "preprocess",
        "tool": "rs_preprocess",
        "params": {
            "operations": ["radiometric_correction", "atmospheric_correction"],
        },
        "tags": ["preprocess", "atmospheric"],
        "author": "rs-agent",
    },
]

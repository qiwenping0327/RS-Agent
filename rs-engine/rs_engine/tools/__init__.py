"""
遥感工具定义 - MCP Tool Schema

每个工具定义包含:
- name: 工具名称（注册后变为 mcp__rs_agent__<name>）
- description: 工具描述（供 LLM 选择工具时参考）
- inputSchema: JSON Schema 格式的输入参数定义
"""

from mcp.types import Tool

# ---------------------------------------------------------------------------
# rs_download - 影像下载
# ---------------------------------------------------------------------------
RS_DOWNLOAD_TOOL = Tool(
    name="rs_download",
    description=(
        "下载卫星遥感影像。支持 Sentinel-2、Landsat-8、高分系列卫星。"
        "支持断点续跑：若任务中断，再次执行相同参数将从上次进度继续。"
        "返回下载文件列表和元数据信息。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "sensor": {
                "type": "string",
                "enum": ["sentinel2", "landsat8", "gf1", "gf2"],
                "description": "传感器名称",
            },
            "aoi": {
                "type": "object",
                "description": "感兴趣区域 (GeoJSON Polygon/Point 格式)",
            },
            "start_date": {
                "type": "string",
                "description": "起始日期 (YYYY-MM-DD)",
            },
            "end_date": {
                "type": "string",
                "description": "结束日期 (YYYY-MM-DD)",
            },
            "max_cloud_cover": {
                "type": "integer",
                "description": "最大云覆盖百分比 (默认 20)",
                "default": 20,
            },
            "output_dir": {
                "type": "string",
                "description": "输出目录 (默认: <RS_WORKSPACE>/downloads/<sensor>)",
            },
        },
        "required": ["sensor", "aoi", "start_date", "end_date"],
    },
)

# ---------------------------------------------------------------------------
# rs_preprocess - 预处理
# ---------------------------------------------------------------------------
RS_PREPROCESS_TOOL = Tool(
    name="rs_preprocess",
    description=(
        "遥感影像预处理。支持辐射校正、几何校正、裁剪拼接、重采样等操作。"
        "可组合多个操作按顺序执行。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "输入影像路径或目录",
            },
            "operations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "radiometric_correction",
                        "atmospheric_correction",
                        "geometric_correction",
                        "clip",
                        "mosaic",
                        "resample",
                    ],
                },
                "description": "预处理操作列表（按顺序执行）",
            },
            "params": {
                "type": "object",
                "description": "操作参数 (如 resample 的 target_resolution 等)",
            },
            "output_dir": {
                "type": "string",
                "description": "输出目录",
            },
        },
        "required": ["input_path", "operations"],
    },
)

# ---------------------------------------------------------------------------
# rs_analyze - 智能分析
# ---------------------------------------------------------------------------
RS_ANALYZE_TOOL = Tool(
    name="rs_analyze",
    description=(
        "遥感影像智能分析。支持 NDVI/NDWI/EVI 等指数计算、地物分类、变化检测。"
        "分析完成后自动生成缩略图预览。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "输入影像路径或目录",
            },
            "analysis_type": {
                "type": "string",
                "enum": ["ndvi", "ndwi", "evi", "savi", "ndbi", "mndwi", "classification", "change_detection", "spectral_index"],
                "description": "分析类型。spectral_index 需配合 index 参数指定具体指数",
            },
            "index": {
                "type": "string",
                "enum": ["ndvi", "ndwi", "evi", "savi", "ndbi", "mndwi"],
                "description": "当 analysis_type=spectral_index 时，指定具体光谱指数",
            },
            "params": {
                "type": "object",
                "description": "分析参数 (如波段映射、分类方法等)",
            },
            "output_dir": {
                "type": "string",
                "description": "输出目录",
            },
        },
        "required": ["input_path", "analysis_type"],
    },
)

# ---------------------------------------------------------------------------
# rs_visualize - 可视化
# ---------------------------------------------------------------------------
RS_VISUALIZE_TOOL = Tool(
    name="rs_visualize",
    description=(
        "遥感影像可视化。支持缩略图生成、真彩色/假彩色合成、指数叠加显示。"
        "输出 PNG 格式图片。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "输入影像路径",
            },
            "vis_type": {
                "type": "string",
                "enum": ["true_color", "false_color", "index_overlay", "thumbnail", "classified"],
                "description": "可视化类型 (默认 thumbnail)",
            },
            "params": {
                "type": "object",
                "description": "可视化参数 (如 sensor, max_size 等)",
            },
            "output_dir": {
                "type": "string",
                "description": "输出目录",
            },
        },
        "required": ["input_path"],
    },
)

# ---------------------------------------------------------------------------
# rs_report - 报告生成
# ---------------------------------------------------------------------------
RS_REPORT_TOOL = Tool(
    name="rs_report",
    description=(
        "生成遥感分析报告。支持 Markdown/HTML/PDF 格式。"
        "报告包含数据来源、处理流程、分析结果和可视化。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "task_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "任务 ID 列表",
            },
            "format": {
                "type": "string",
                "enum": ["markdown", "html", "pdf"],
                "description": "报告格式 (默认 markdown)",
            },
            "title": {
                "type": "string",
                "description": "报告标题",
            },
            "summary": {
                "type": "string",
                "description": "报告摘要",
            },
            "output_path": {
                "type": "string",
                "description": "输出文件路径",
            },
        },
        "required": [],
    },
)

# ---------------------------------------------------------------------------
# rs_sar_analysis - SAR 分析
# ---------------------------------------------------------------------------
RS_SAR_ANALYSIS_TOOL = Tool(
    name="rs_sar_analysis",
    description=(
        "SAR 遥感影像分析。支持极化分解、InSAR 形变监测、建筑物提取、水体/船只检测。"
        "需要 Sentinel-1 数据。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "输入 SAR 影像路径",
            },
            "analysis_type": {
                "type": "string",
                "enum": ["polarimetric", "insar", "building_extraction", "water_detection", "ship_detection"],
                "description": "SAR 分析类型",
            },
            "params": {
                "type": "object",
                "description": "分析参数",
            },
            "output_dir": {
                "type": "string",
                "description": "输出目录",
            },
        },
        "required": ["input_path", "analysis_type"],
    },
)

# ---------------------------------------------------------------------------
# rs_model_inference - 模型推理
# ---------------------------------------------------------------------------
RS_MODEL_INFERENCE_TOOL = Tool(
    name="rs_model_inference",
    description=(
        "遥感深度学习模型推理。支持目标检测(YOLOv8)、语义分割(U-Net/DeepLabV3+)、"
        "变化检测(BIT/SNUNet)。自动 GPU/CPU 回退。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "输入影像路径",
            },
            "task_type": {
                "type": "string",
                "enum": ["object_detection", "semantic_segmentation", "change_detection"],
                "description": "推理任务类型",
            },
            "model_name": {
                "type": "string",
                "description": "模型名称 (默认自动选择)",
            },
            "params": {
                "type": "object",
                "description": "推理参数 (如 batch_size, overlap 等)",
            },
            "output_dir": {
                "type": "string",
                "description": "输出目录",
            },
        },
        "required": ["input_path", "task_type"],
    },
)

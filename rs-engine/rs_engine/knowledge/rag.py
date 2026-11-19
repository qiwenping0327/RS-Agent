"""
遥感知识库 - RAG 检索

基于关键词匹配和向量相似度的知识检索模块。
将遥感领域知识转化为可检索的文档片段，供 Hook 和工具使用。

阶段一: 基于关键词的检索
阶段二: 基于嵌入向量的语义检索 (需 sentence-transformers)
"""

import json
import logging
import os
from typing import Any

from rs_engine.knowledge.band_mapping import SENSOR_BANDS, SPECTRAL_INDICES
from rs_engine.knowledge.spatial_geocode import PRESET_AOI, COMMON_CRS

logger = logging.getLogger("rs-engine.knowledge.rag")

# ---------------------------------------------------------------------------
# 知识文档片段
# ---------------------------------------------------------------------------
KNOWLEDGE_DOCS: list[dict[str, Any]] = []

def _build_knowledge_docs() -> list[dict[str, Any]]:
    """
    从知识库构建可检索的文档片段

    每个片段包含:
    - id: 唯一标识
    - category: 分类 (sensor, index, region, crs, workflow, faq)
    - title: 标题
    - content: 文本内容
    - keywords: 关键词列表
    """
    docs: list[dict[str, Any]] = []
    doc_id = 0

    # --- 传感器知识 ---
    for sensor_key, sensor_info in SENSOR_BANDS.items():
        bands_desc = "\n".join(
            f"  - {k}: {v['name']} ({v['resolution']}m, {v['wavelength']})"
            for k, v in sensor_info["bands"].items()
        )
        docs.append({
            "id": f"sensor_{sensor_key}",
            "category": "sensor",
            "title": f"{sensor_info['name']} 传感器",
            "content": (
                f"{sensor_info['name']} 传感器信息:\n"
                f"波段列表:\n{bands_desc}\n"
                f"真彩色合成: {sensor_info.get('rgb_bands', [])}\n"
                f"假彩色合成: {sensor_info.get('false_color_bands', [])}"
            ),
            "keywords": [sensor_key, sensor_info["name"].lower(), "sensor", "传感器"],
        })
        doc_id += 1

    # --- 光谱指数知识 ---
    for idx_key, idx_info in SPECTRAL_INDICES.items():
        band_mappings = []
        for sensor, mapping in idx_info.get("band_mapping", {}).items():
            band_mappings.append(f"  - {sensor}: {mapping}")
        band_map_str = "\n".join(band_mappings)

        docs.append({
            "id": f"index_{idx_key}",
            "category": "index",
            "title": f"{idx_info['name']} ({idx_key.upper()})",
            "content": (
                f"{idx_info['name']}:\n"
                f"  公式: {idx_info['formula']}\n"
                f"  值域: {idx_info['range']}\n"
                f"  说明: {idx_info['description']}\n"
                f"波段映射:\n{band_map_str}"
            ),
            "keywords": [idx_key, idx_info["name"].lower(), "index", "指数", "spectral"],
        })
        doc_id += 1

    # --- 区域知识 ---
    for region, aoi in PRESET_AOI.items():
        coords = aoi.get("coordinates", [[]])[0] if aoi.get("coordinates") else []
        if coords:
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            center_lon = sum(lons) / len(lons)
            center_lat = sum(lats) / len(lats)
            docs.append({
                "id": f"region_{region}",
                "category": "region",
                "title": f"{region} 区域",
                "content": (
                    f"{region} 区域预设 AOI:\n"
                    f"  中心坐标: ({center_lon:.2f}, {center_lat:.2f})\n"
                    f"  经度范围: {min(lons):.2f} ~ {max(lons):.2f}\n"
                    f"  纬度范围: {min(lats):.2f} ~ {max(lats):.2f}\n"
                    f"  GeoJSON: {json.dumps(aoi, ensure_ascii=False)}"
                ),
                "keywords": [region.lower(), "region", "区域", "aoi"],
            })
            doc_id += 1

    # --- CRS 知识 ---
    for crs_name, crs_code in COMMON_CRS.items():
        docs.append({
            "id": f"crs_{crs_name}",
            "category": "crs",
            "title": f"{crs_name} 坐标参考系",
            "content": f"{crs_name} 坐标参考系: {crs_code}",
            "keywords": [crs_name.lower(), crs_code.lower(), "crs", "投影", "坐标系"],
        })
        doc_id += 1

    # --- 工作流知识 ---
    workflow_docs = [
        {
            "id": "workflow_download",
            "category": "workflow",
            "title": "遥感影像下载流程",
            "content": (
                "遥感影像下载标准流程:\n"
                "1. 确定传感器类型 (sentinel2/landsat8/gf1/gf2)\n"
                "2. 定义感兴趣区域 (AOI, GeoJSON 格式)\n"
                "3. 设定时间范围和云覆盖阈值\n"
                "4. 调用 rs_download 工具\n"
                "5. 检查下载结果元数据\n"
                "注意: Sentinel-2 需要 Copernicus API 凭证，Landsat-8 需要 USGS 凭证"
            ),
            "keywords": ["download", "下载", "sentinel", "landsat", "高分", "影像获取"],
        },
        {
            "id": "workflow_preprocess",
            "category": "workflow",
            "title": "遥感影像预处理流程",
            "content": (
                "遥感影像预处理标准流程:\n"
                "1. 辐射校正 (Radiometric Correction)\n"
                "2. 大气校正 (Atmospheric Correction) - 转换为地表反射率\n"
                "3. 几何校正 (Geometric Correction)\n"
                "4. 裁剪 (Clip) - 提取研究区域\n"
                "5. 重采样 (Resample) - 统一分辨率\n"
                "注意: 操作顺序很重要，建议按上述顺序执行"
            ),
            "keywords": ["preprocess", "预处理", "校正", "辐射", "大气", "几何", "裁剪", "重采样"],
        },
        {
            "id": "workflow_ndvi",
            "category": "workflow",
            "title": "NDVI 植被指数分析流程",
            "content": (
                "NDVI 植被指数分析标准流程:\n"
                "1. 下载多光谱影像 (需包含红光和近红外波段)\n"
                "2. 预处理 (至少大气校正)\n"
                "3. 调用 rs_analyze，设置 analysis_type=ndvi\n"
                "4. 波段映射: Sentinel-2 使用 B04(红) B08(近红外)\n"
                "5. 解译结果: <0 水体, 0-0.2 裸土, 0.2-0.5 稀疏植被, >0.5 茂密植被"
            ),
            "keywords": ["ndvi", "植被", "vegetation", "绿色", "森林", "农田"],
        },
        {
            "id": "workflow_change_detection",
            "category": "workflow",
            "title": "变化检测流程",
            "content": (
                "遥感变化检测标准流程:\n"
                "1. 获取两个时期的影像 (相同区域、相近季节)\n"
                "2. 分别预处理 (确保一致的辐射和几何校正)\n"
                "3. 调用 rs_analyze，设置 analysis_type=change_detection\n"
                "4. 结果为二值图: 0=未变化, 1=变化\n"
                "5. 可结合分类结果确定变化类型"
            ),
            "keywords": ["change", "变化", "检测", "detection", "对比", "时序"],
        },
    ]
    docs.extend(workflow_docs)

    # --- FAQ 知识 ---
    faq_docs = [
        {
            "id": "faq_cloud_cover",
            "category": "faq",
            "title": "云覆盖阈值设置建议",
            "content": (
                "云覆盖阈值设置建议:\n"
                "- 0-10%: 适用于精细定量分析，可用影像较少\n"
                "- 10-20%: 推荐值，平衡影像质量和可用性\n"
                "- 20-50%: 可用于大范围浏览，需掩膜处理云区域\n"
                "- >50%: 不推荐，云影响过大\n"
                "注意: Sentinel-2 L2A 产品已做云掩膜，但厚云区域数据仍不可靠"
            ),
            "keywords": ["cloud", "云", "覆盖", "阈值", "cloud_cover"],
        },
        {
            "id": "faq_resolution",
            "category": "faq",
            "title": "空间分辨率选择建议",
            "content": (
                "空间分辨率选择建议:\n"
                "- 1m (GF-2): 建筑物、道路、车辆检测\n"
                "- 2-4m (GF-1/GF-2): 城市规划、精细地物分类\n"
                "- 10m (Sentinel-2): 农业监测、植被分析、区域制图\n"
                "- 30m (Landsat-8): 大范围土地覆盖、长期变化监测\n"
                "- 60m+ (Sentinel-2 B01/B09/B10): 大气校正辅助波段\n"
                "选择原则: 在满足需求的前提下选择最低分辨率，降低数据量和处理时间"
            ),
            "keywords": ["resolution", "分辨率", "精度", "空间", "选择"],
        },
    ]
    docs.extend(faq_docs)

    return docs


# 初始化知识文档
KNOWLEDGE_DOCS = _build_knowledge_docs()


def search_knowledge(
    query: str,
    category: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    检索知识库

    Args:
        query: 查询文本
        category: 按分类过滤 (sensor, index, region, crs, workflow, faq)
        top_k: 返回前 k 个结果

    Returns:
        匹配的知识文档列表，按相关度降序排列
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored: list[tuple[float, dict[str, Any]]] = []

    for doc in KNOWLEDGE_DOCS:
        if category and doc.get("category") != category:
            continue

        score = 0.0

        # 关键词匹配评分
        for kw in doc.get("keywords", []):
            if kw.lower() in query_lower:
                score += 2.0
            # 部分匹配
            for qw in query_words:
                if qw in kw.lower() or kw.lower() in qw:
                    score += 0.5

        # 标题匹配
        if query_lower in doc["title"].lower():
            score += 5.0

        # 内容匹配
        if query_lower in doc["content"].lower():
            score += 1.0

        if score > 0:
            scored.append((score, doc))

    # 按分数降序排列
    scored.sort(key=lambda x: x[0], reverse=True)

    return [doc for _, doc in scored[:top_k]]


def get_context_for_tool(tool_name: str, tool_input: dict) -> str:
    """
    根据工具调用自动生成上下文

    Args:
        tool_name: 工具名称
        tool_input: 工具输入参数

    Returns:
        格式化的上下文文本
    """
    contexts = []

    # 根据工具类型检索相关知识
    if tool_name == "rs_download":
        sensor = tool_input.get("sensor", "")
        if sensor:
            results = search_knowledge(sensor, category="sensor", top_k=1)
            contexts.extend(r["content"] for r in results)

    elif tool_name == "rs_analyze":
        analysis_type = tool_input.get("analysis_type", "")
        if analysis_type:
            results = search_knowledge(analysis_type, category="index", top_k=2)
            contexts.extend(r["content"] for r in results)

    elif tool_name == "rs_preprocess":
        results = search_knowledge("预处理", category="workflow", top_k=1)
        contexts.extend(r["content"] for r in results)

    return "\n\n".join(contexts) if contexts else ""

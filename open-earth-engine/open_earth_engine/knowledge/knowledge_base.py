from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("oea.knowledge")


@dataclass
class KnowledgeEntry:
    entry_id: str
    entry_type: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    importance: int = 0

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "tags": self.tags,
            "importance": self.importance,
        }


@dataclass
class ToolFallbackDoc:
    tool_id: str
    fallback_tool: str
    reason: str
    conditions: list[str] = field(default_factory=list)


@dataclass
class KnowledgeBaseConfig:
    enable_tool_fallback: bool = True
    enable_geospatial_knowledge: bool = True
    max_search_results: int = 10


class KnowledgeBase:
    """
    知识库 - 工具替代方案 + 遥感知识文档

    职责:
    1. 存储工具替代方案文档
    2. 代码执行失败时提供回退建议
    3. 遥感专业知识检索
    4. 与现有 MCP 工具池联动

    与 OpenEarthAgent 的关系:
    - 两层工具库: 基础函数 + 专家级执行模板
    - 多领域知识库: 支持离线检索
    - 工具替代方案: 执行失败时自动回退
    """

    ENTRY_TYPE_TOOL_FALLBACK = "tool_fallback"
    ENTRY_TYPE_GEOKNOWLEDGE = "geoknowledge"
    ENTRY_TYPE_TOOL_DOC = "tool_doc"
    ENTRY_TYPE_BEST_PRACTICE = "best_practice"

    def __init__(self, config: KnowledgeBaseConfig = None):
        self.config = config or KnowledgeBaseConfig()
        self._entries: dict[str, KnowledgeEntry] = {}
        self._tag_index: dict[str, list[str]] = {}
        self._tool_fallbacks: dict[str, ToolFallbackDoc] = {}

        self._initialize_default_knowledge()

    def _initialize_default_knowledge(self) -> None:
        """
        初始化默认知识库
        """
        self._add_tool_fallback_docs()
        self._add_geospatial_knowledge()
        self._add_tool_documentation()
        self._add_best_practices()

    def _add_tool_fallback_docs(self) -> None:
        """
        添加工具替代方案
        """
        fallbacks = [
            ToolFallbackDoc(
                tool_id="rs-agent.rs_download",
                fallback_tool="sandbox.gdal_download",
                reason="MCP下载服务不可用时，使用GDAL直接下载",
                conditions=["网络连接正常", "支持HTTP/HTTPS协议"],
            ),
            ToolFallbackDoc(
                tool_id="rs-agent.rs_preprocess",
                fallback_tool="sandbox.rasterio_preprocess",
                reason="MCP预处理服务不可用时，使用Rasterio自定义处理",
                conditions=["输入为标准GeoTIFF格式"],
            ),
            ToolFallbackDoc(
                tool_id="rs-agent.rs_analyze",
                fallback_tool="sandbox.numpy_analysis",
                reason="MCP分析服务不可用时，使用NumPy自定义计算",
                conditions=["需要自定义指数计算"],
            ),
        ]

        for fb in fallbacks:
            self._tool_fallbacks[fb.tool_id] = fb

            entry = KnowledgeEntry(
                entry_id=f"fallback_{fb.tool_id.replace('.', '_')}",
                entry_type=self.ENTRY_TYPE_TOOL_FALLBACK,
                title=f"Fallback for {fb.tool_id}",
                content=f"When {fb.tool_id} fails, use {fb.fallback_tool}. Reason: {fb.reason}",
                metadata={
                    "tool_id": fb.tool_id,
                    "fallback_tool": fb.fallback_tool,
                    "conditions": fb.conditions,
                },
                tags=["fallback", fb.tool_id, fb.fallback_tool],
                importance=8,
            )
            self._add_entry(entry)

    def _add_geospatial_knowledge(self) -> None:
        """
        添加地理空间知识
        """
        knowledge_items = [
            {
                "title": "NDVI 指数计算",
                "content": "NDVI = (NIR - Red) / (NIR + Red)。范围 [-1, 1]，正值表示植被，负值表示水体/建筑。",
                "tags": ["ndvi", "植被指数", "spectral"],
                "metadata": {"formula": "(NIR - Red) / (NIR + Red)", "range": "[-1, 1]"},
            },
            {
                "title": "NDWI 水体指数",
                "content": "NDWI = (Green - NIR) / (Green + NIR)。用于提取水体信息，正值表示水体。",
                "tags": ["ndwi", "水体指数", "spectral"],
                "metadata": {"formula": "(Green - NIR) / (Green + NIR)"},
            },
            {
                "title": "NDBI 建筑指数",
                "content": "NDBI = (SWIR - NIR) / (SWIR + NIR)。用于提取建筑用地信息。",
                "tags": ["ndbi", "建筑指数", "spectral"],
                "metadata": {"formula": "(SWIR - NIR) / (SWIR + NIR)"},
            },
            {
                "title": "坐标系投影转换",
                "content": "常见坐标系：WGS84 (EPSG:4326) 地理坐标，UTM (如 EPSG:32650) 投影坐标。使用 GDAL/OGR 进行转换。",
                "tags": ["projection", "坐标系", "gdal"],
                "metadata": {"wgs84": "EPSG:4326", "utm_zone50n": "EPSG:32650"},
            },
            {
                "title": "栅格矢量转换",
                "content": "栅格转矢量使用 GDAL Polygonize，矢量转栅格使用 GDAL Rasterize。注意分辨率和属性字段匹配。",
                "tags": ["raster", "vector", "conversion", "gdal"],
                "metadata": {"raster_to_vector": "gdal.Polygonize", "vector_to_raster": "gdal.Rasterize"},
            },
            {
                "title": "分区统计 (Zonal Statistics)",
                "content": "使用矢量图层作为分区，统计每个分区内栅格值的均值、总和、最大值、最小值等。",
                "tags": ["zonal", "分区统计", "statistics"],
                "metadata": {"metrics": ["mean", "sum", "max", "min", "std", "count"]},
            },
        ]

        for i, item in enumerate(knowledge_items):
            entry = KnowledgeEntry(
                entry_id=f"geo_{i:03d}",
                entry_type=self.ENTRY_TYPE_GEOKNOWLEDGE,
                title=item["title"],
                content=item["content"],
                metadata=item["metadata"],
                tags=item["tags"],
                importance=5,
            )
            self._add_entry(entry)

    def _add_tool_documentation(self) -> None:
        """
        添加工具文档
        """
        tool_docs = [
            {
                "tool_id": "rs-agent.rs_download",
                "content": "遥感影像下载工具。支持Sentinel-1/2、Landsat、高分系列等卫星数据下载。",
                "tags": ["download", "data_acquisition"],
                "params": ["satellite", "region", "start_date", "end_date", "cloud_cover"],
            },
            {
                "tool_id": "rs-agent.rs_preprocess",
                "content": "遥感影像预处理。包含辐射校正、大气校正、几何校正等步骤。",
                "tags": ["preprocess", "correction"],
                "params": ["input_path", "output_path", "correction_type"],
            },
            {
                "tool_id": "rs-agent.rs_analyze",
                "content": "遥感影像分析。支持NDVI、NDWI等光谱指数计算，变化检测等。",
                "tags": ["analysis", "spectral_index"],
                "params": ["input_path", "analysis_type", "bands", "output_path"],
            },
        ]

        for i, doc in enumerate(tool_docs):
            entry = KnowledgeEntry(
                entry_id=f"tooldoc_{i:03d}",
                entry_type=self.ENTRY_TYPE_TOOL_DOC,
                title=f"Documentation for {doc['tool_id']}",
                content=doc["content"],
                metadata={"tool_id": doc["tool_id"], "params": doc["params"]},
                tags=doc["tags"] + [doc["tool_id"]],
                importance=6,
            )
            self._add_entry(entry)

    def _add_best_practices(self) -> None:
        """
        添加最佳实践
        """
        practices = [
            {
                "title": "多景影像处理工作流",
                "content": "1. 批量下载 → 2. 并行预处理 → 3. 镶嵌/拼接 → 4. 统一分析。注意时间同步和坐标系统一。",
                "tags": ["workflow", "batch", "multi_scene"],
            },
            {
                "title": "变化检测最佳实践",
                "content": "确保两个时相影像：1. 物候期相近 2. 云量低 3. 坐标系一致 4. 辐射归一化处理。",
                "tags": ["change_detection", "best_practice"],
            },
            {
                "title": "数据缓存策略",
                "content": "原始影像长期缓存，中间结果按任务缓存，结果文件持久化到WorkSpace输出目录。",
                "tags": ["cache", "performance", "storage"],
            },
        ]

        for i, practice in enumerate(practices):
            entry = KnowledgeEntry(
                entry_id=f"best_{i:03d}",
                entry_type=self.ENTRY_TYPE_BEST_PRACTICE,
                title=practice["title"],
                content=practice["content"],
                tags=practice["tags"],
                importance=7,
            )
            self._add_entry(entry)

    def _add_entry(self, entry: KnowledgeEntry) -> None:
        """
        添加条目到索引
        """
        self._entries[entry.entry_id] = entry

        for tag in entry.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(entry.entry_id)

    def get_fallback(self, tool_id: str) -> Optional[ToolFallbackDoc]:
        """
        获取工具的回退方案
        """
        if not self.config.enable_tool_fallback:
            return None
        return self._tool_fallbacks.get(tool_id)

    def get_fallback_recommendation(self, tool_id: str, error: str) -> Optional[dict]:
        """
        获取失败时的回退建议
        """
        fallback = self.get_fallback(tool_id)
        if not fallback:
            return None

        return {
            "original_tool": tool_id,
            "recommended_fallback": fallback.fallback_tool,
            "reason": fallback.reason,
            "conditions": fallback.conditions,
            "error_context": error,
        }

    def search(
        self,
        query: str,
        entry_types: list[str] = None,
        tags: list[str] = None,
    ) -> list[KnowledgeEntry]:
        """
        搜索知识库
        """
        query_lower = query.lower()
        results = []

        for entry in self._entries.values():
            if entry_types and entry.entry_type not in entry_types:
                continue

            if tags and not any(t in entry.tags for t in tags):
                continue

            entry_text = f"{entry.title} {entry.content} {' '.join(entry.tags)}".lower()
            if query_lower in entry_text:
                results.append(entry)

        results.sort(key=lambda e: (-e.importance, e.title))
        return results[: self.config.max_search_results]

    def search_by_tags(self, tags: list[str]) -> list[KnowledgeEntry]:
        """
        按标签搜索
        """
        entry_ids = set()
        for tag in tags:
            if tag in self._tag_index:
                entry_ids.update(self._tag_index[tag])

        results = [self._entries[eid] for eid in entry_ids if eid in self._entries]
        results.sort(key=lambda e: -e.importance)
        return results[: self.config.max_search_results]

    def get_tool_doc(self, tool_id: str) -> Optional[KnowledgeEntry]:
        """
        获取工具文档
        """
        for entry in self._entries.values():
            if entry.entry_type == self.ENTRY_TYPE_TOOL_DOC:
                if entry.metadata.get("tool_id") == tool_id:
                    return entry
        return None

    def get_geospatial_knowledge(self, topic: str) -> list[KnowledgeEntry]:
        """
        获取地理空间知识
        """
        if not self.config.enable_geospatial_knowledge:
            return []
        return self.search(topic, entry_types=[self.ENTRY_TYPE_GEOKNOWLEDGE])

    def get_best_practices(self, context: str) -> list[KnowledgeEntry]:
        """
        获取相关最佳实践
        """
        return self.search(context, entry_types=[self.ENTRY_TYPE_BEST_PRACTICE])

    def add_entry(
        self,
        entry_type: str,
        title: str,
        content: str,
        tags: list[str] = None,
        metadata: dict[str, Any] = None,
        importance: int = 0,
    ) -> KnowledgeEntry:
        """
        添加新的知识条目
        """
        import uuid

        entry = KnowledgeEntry(
            entry_id=f"custom_{uuid.uuid4().hex[:8]}",
            entry_type=entry_type,
            title=title,
            content=content,
            metadata=metadata or {},
            tags=tags or [],
            importance=importance,
        )
        self._add_entry(entry)
        logger.info(f"Added knowledge entry: {title}")
        return entry

    def get_all_tools_with_docs(self) -> list[dict]:
        """
        获取所有工具及其文档
        """
        tools = []
        for entry in self._entries.values():
            if entry.entry_type == self.ENTRY_TYPE_TOOL_DOC:
                tools.append({
                    "tool_id": entry.metadata.get("tool_id"),
                    "title": entry.title,
                    "content": entry.content,
                    "tags": entry.tags,
                    "params": entry.metadata.get("params", []),
                })
        return tools

    def get_summary(self) -> dict:
        """
        获取知识库摘要
        """
        type_counts = {}
        for entry in self._entries.values():
            et = entry.entry_type
            type_counts[et] = type_counts.get(et, 0) + 1

        return {
            "total_entries": len(self._entries),
            "entries_by_type": type_counts,
            "total_tags": len(self._tag_index),
            "tool_fallbacks_count": len(self._tool_fallbacks),
        }

    def to_dict(self) -> dict:
        """
        序列化为字典
        """
        return {
            "config": {
                "enable_tool_fallback": self.config.enable_tool_fallback,
                "enable_geospatial_knowledge": self.config.enable_geospatial_knowledge,
                "max_search_results": self.config.max_search_results,
            },
            "entries": [e.to_dict() for e in self._entries.values()],
            "summary": self.get_summary(),
        }

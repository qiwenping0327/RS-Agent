"""
知识库数据库 - SQLite 持久化存储

提供知识条目的 CRUD 操作和向量索引管理。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("oea.knowledge_db")

ENTRY_TYPE_GEOKNOWLEDGE = "geoknowledge"
ENTRY_TYPE_TOOL_DOC = "tool_doc"
ENTRY_TYPE_TOOL_FALLBACK = "tool_fallback"
ENTRY_TYPE_BEST_PRACTICE = "best_practice"
ENTRY_TYPE_WORKFLOW = "workflow"
ENTRY_TYPE_FAQ = "faq"
ENTRY_TYPE_CUSTOM = "custom"

ENTRY_TYPES = [
    ENTRY_TYPE_GEOKNOWLEDGE,
    ENTRY_TYPE_TOOL_DOC,
    ENTRY_TYPE_TOOL_FALLBACK,
    ENTRY_TYPE_BEST_PRACTICE,
    ENTRY_TYPE_WORKFLOW,
    ENTRY_TYPE_FAQ,
    ENTRY_TYPE_CUSTOM,
]


@dataclass
class KnowledgeEntry:
    """知识条目"""
    entry_id: str
    entry_type: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    access_count: int = 0
    last_accessed_at: datetime = None
    is_active: bool = True
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "importance": self.importance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "is_active": self.is_active,
            "version": self.version,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "KnowledgeEntry":
        return cls(
            entry_id=row["entry_id"],
            entry_type=row["entry_type"],
            title=row["title"],
            content=row["content"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            importance=row["importance"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            access_count=row["access_count"],
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]) if row["last_accessed_at"] else None,
            is_active=bool(row["is_active"]),
            version=row["version"],
        )


class KnowledgeDatabase:
    """知识库 SQLite 数据库"""

    def __init__(self, db_path: str = "./knowledge.db"):
        self.db_path = db_path
        self._ensure_db()
        self._ensure_default_data()

    def _ensure_db(self) -> None:
        """确保数据库和表存在"""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)) or ".", exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    entry_id TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT,
                    importance INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    version INTEGER DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entry_type ON knowledge_entries(entry_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_active ON knowledge_entries(is_active)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance ON knowledge_entries(importance DESC)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_collections (
                    collection_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_entries (
                    collection_id TEXT,
                    entry_id TEXT,
                    added_at TEXT,
                    PRIMARY KEY (collection_id, entry_id),
                    FOREIGN KEY (entry_id) REFERENCES knowledge_entries(entry_id)
                )
            """)

            conn.commit()

    def _ensure_default_data(self) -> None:
        """确保默认知识数据存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM knowledge_entries")
            count = cursor.fetchone()["count"]

            if count == 0:
                self._init_default_knowledge(conn)

    def _init_default_knowledge(self, conn: sqlite3.Connection) -> None:
        """初始化默认知识库"""
        default_entries = [
            {
                "entry_type": ENTRY_TYPE_GEOKNOWLEDGE,
                "title": "NDVI 指数计算",
                "content": "NDVI = (NIR - Red) / (NIR + Red)。范围 [-1, 1]，正值表示植被，负值表示水体/建筑。\n\n解译参考：\n- < 0: 水体、云、雪\n- 0 - 0.2: 裸土、岩石\n- 0.2 - 0.5: 稀疏植被、农田\n- > 0.5: 茂密植被、森林",
                "tags": ["ndvi", "植被指数", "spectral", "遥感基础"],
                "metadata": {"formula": "(NIR - Red) / (NIR + Red)", "range": "[-1, 1]"},
                "importance": 5,
            },
            {
                "entry_type": ENTRY_TYPE_GEOKNOWLEDGE,
                "title": "NDWI 水体指数",
                "content": "NDWI = (Green - NIR) / (Green + NIR)。用于提取水体信息，正值表示水体。\n\n适用场景：\n- 水体范围提取\n- 洪水监测\n- 湿地调查",
                "tags": ["ndwi", "水体指数", "spectral", "遥感基础"],
                "metadata": {"formula": "(Green - NIR) / (Green + NIR)"},
                "importance": 5,
            },
            {
                "entry_type": ENTRY_TYPE_GEOKNOWLEDGE,
                "title": "坐标系投影转换",
                "content": "常见坐标系：\n- WGS84 (EPSG:4326): 地理坐标，经纬度\n- UTM Zone 50N (EPSG:32650): 北京地区投影坐标\n- UTM Zone 49N (EPSG:32649): 上海地区投影坐标\n\n使用 GDAL/OGR 进行转换时需注意：\n1. 源坐标系和目标坐标系的定义\n2. 数据精度损失\n3. 投影变形",
                "tags": ["projection", "坐标系", "gdal", "投影转换"],
                "metadata": {"wgs84": "EPSG:4326", "utm_zone50n": "EPSG:32650"},
                "importance": 5,
            },
            {
                "entry_type": ENTRY_TYPE_GEOKNOWLEDGE,
                "title": "分区统计 (Zonal Statistics)",
                "content": "使用矢量图层作为分区，统计每个分区内栅格值的统计指标。\n\n常用统计指标：\n- mean: 均值\n- sum: 总和\n- max: 最大值\n- min: 最小值\n- std: 标准差\n- count: 有效像元数\n- median: 中位数",
                "tags": ["zonal", "分区统计", "statistics", "栅格分析"],
                "metadata": {"metrics": ["mean", "sum", "max", "min", "std", "count", "median"]},
                "importance": 6,
            },
            {
                "entry_type": ENTRY_TYPE_BEST_PRACTICE,
                "title": "变化检测最佳实践",
                "content": "确保两个时相影像满足以下条件：\n1. 物候期相近（避免季节差异）\n2. 云量低（建议 < 20%）\n3. 坐标系一致\n4. 辐射归一化处理\n5. 分辨率一致\n\n推荐流程：\n1. 预处理（辐射校正、几何校正）\n2. 变化检测算法（差异法、变换法、分类后比较）\n3. 精度验证",
                "tags": ["change_detection", "best_practice", "变化检测"],
                "metadata": {},
                "importance": 7,
            },
            {
                "entry_type": ENTRY_TYPE_TOOL_DOC,
                "title": "rs_download 工具文档",
                "content": "遥感影像下载工具。支持 Sentinel-1/2、Landsat、高分系列等卫星数据下载。\n\n参数说明：\n- satellite: 卫星类型 (sentinel2, landsat8, gf1, gf2)\n- region: 区域范围 (GeoJSON 或 WKT)\n- start_date: 开始日期 (YYYY-MM-DD)\n- end_date: 结束日期 (YYYY-MM-DD)\n- cloud_cover: 云量阈值 (0-100)",
                "tags": ["download", "data_acquisition", "rs_download"],
                "metadata": {"tool_id": "rs-agent.rs_download", "params": ["satellite", "region", "start_date", "end_date", "cloud_cover"]},
                "importance": 6,
            },
            {
                "entry_type": ENTRY_TYPE_TOOL_DOC,
                "title": "rs_preprocess 工具文档",
                "content": "遥感影像预处理工具。包含辐射校正、大气校正、几何校正等步骤。\n\n参数说明：\n- input_path: 输入影像路径\n- output_path: 输出影像路径\n- correction_type: 校正类型 (radiometric, atmospheric, geometric)\n\n注意：校正顺序很重要，建议按上述顺序执行。",
                "tags": ["preprocess", "correction", "rs_preprocess", "预处理"],
                "metadata": {"tool_id": "rs-agent.rs_preprocess", "params": ["input_path", "output_path", "correction_type"]},
                "importance": 6,
            },
            {
                "entry_type": ENTRY_TYPE_TOOL_DOC,
                "title": "rs_analyze 工具文档",
                "content": "遥感影像分析工具。支持 NDVI、NDWI 等光谱指数计算，变化检测等。\n\n参数说明：\n- input_path: 输入影像路径\n- analysis_type: 分析类型 (ndvi, ndwi, change_detection)\n- bands: 波段设置 (可选)\n- output_path: 输出路径",
                "tags": ["analysis", "spectral_index", "rs_analyze", "分析"],
                "metadata": {"tool_id": "rs-agent.rs_analyze", "params": ["input_path", "analysis_type", "bands", "output_path"]},
                "importance": 6,
            },
            {
                "entry_type": ENTRY_TYPE_WORKFLOW,
                "title": "NDVI 植被指数分析流程",
                "content": "NDVI 植被指数分析标准流程：\n\n1. 数据获取\n   - 下载多光谱影像（需包含红光和近红外波段）\n   - Sentinel-2: B04(红) B08(近红外)\n   - Landsat-8: B4(红) B5(近红外)\n\n2. 预处理\n   - 辐射校正\n   - 大气校正（转换为地表反射率）\n   - 裁剪研究区域\n\n3. 指数计算\n   - 调用 rs_analyze，设置 analysis_type=ndvi\n\n4. 结果解译\n   - < 0: 水体、云、雪\n   - 0-0.2: 裸土、岩石\n   - 0.2-0.5: 稀疏植被、农田\n   - > 0.5: 茂密植被、森林",
                "tags": ["workflow", "ndvi", "植被", "分析流程"],
                "metadata": {"steps": ["download", "preprocess", "analyze", "interpret"]},
                "importance": 7,
            },
            {
                "entry_type": ENTRY_TYPE_FAQ,
                "title": "云覆盖阈值设置建议",
                "content": "云覆盖阈值设置建议：\n\n- 0-10%: 适用于精细定量分析，可用影像较少\n- 10-20%: 推荐值，平衡影像质量和可用性\n- 20-50%: 可用于大范围浏览，需掩膜处理云区域\n- >50%: 不推荐，云影响过大\n\n注意：Sentinel-2 L2A 产品已做云掩膜，但厚云区域数据仍不可靠。",
                "tags": ["cloud", "云", "覆盖", "阈值", "faq"],
                "metadata": {"recommended_threshold": 20},
                "importance": 5,
            },
            {
                "entry_type": ENTRY_TYPE_FAQ,
                "title": "空间分辨率选择建议",
                "content": "空间分辨率选择建议：\n\n- 1m (GF-2): 建筑物、道路、车辆检测\n- 2-4m (GF-1/GF-2): 城市规划、精细地物分类\n- 10m (Sentinel-2): 农业监测、植被分析、区域制图\n- 30m (Landsat-8): 大范围土地覆盖、长期变化监测\n- 60m+ (Sentinel-2 B01/B09/B10): 大气校正辅助波段\n\n选择原则：在满足需求的前提下选择最低分辨率，降低数据量和处理时间。",
                "tags": ["resolution", "分辨率", "精度", "空间", "faq"],
                "metadata": {"resolution_levels": {"high": "1-4m", "medium": "10-30m", "low": "60m+"}},
                "importance": 5,
            },
        ]

        cursor = conn.cursor()
        now = datetime.now().isoformat()

        for entry in default_entries:
            entry_id = f"default_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO knowledge_entries 
                (entry_id, entry_type, title, content, tags, metadata, importance, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                entry_id,
                entry["entry_type"],
                entry["title"],
                entry["content"],
                json.dumps(entry["tags"], ensure_ascii=False),
                json.dumps(entry["metadata"], ensure_ascii=False),
                entry["importance"],
                now,
                now,
            ))

        conn.commit()
        logger.info(f"Initialized default knowledge base with {len(default_entries)} entries")

    @contextmanager
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_entry(
        self,
        entry_type: str,
        title: str,
        content: str,
        tags: list[str] = None,
        metadata: dict[str, Any] = None,
        importance: int = 0,
    ) -> KnowledgeEntry:
        """创建知识条目"""
        entry_id = f"entry_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge_entries 
                (entry_id, entry_type, title, content, tags, metadata, importance, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                entry_id,
                entry_type,
                title,
                content,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(metadata or {}, ensure_ascii=False),
                importance,
                now,
                now,
            ))
            conn.commit()

        return self.get_entry(entry_id)

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """获取知识条目"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM knowledge_entries WHERE entry_id = ?
            """, (entry_id,))
            row = cursor.fetchone()
            return KnowledgeEntry.from_row(dict(row)) if row else None

    def update_entry(
        self,
        entry_id: str,
        title: str = None,
        content: str = None,
        tags: list[str] = None,
        metadata: dict[str, Any] = None,
        importance: int = None,
        entry_type: str = None,
    ) -> Optional[KnowledgeEntry]:
        """更新知识条目"""
        entry = self.get_entry(entry_id)
        if not entry:
            return None

        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata, ensure_ascii=False))
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if entry_type is not None:
            updates.append("entry_type = ?")
            params.append(entry_type)

        if not updates:
            return entry

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        updates.append("version = version + 1")
        params.append(entry_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE knowledge_entries 
                SET {', '.join(updates)}
                WHERE entry_id = ?
            """, params)
            conn.commit()

        return self.get_entry(entry_id)

    def delete_entry(self, entry_id: str) -> bool:
        """删除知识条目（软删除）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE knowledge_entries 
                SET is_active = 0, updated_at = ?
                WHERE entry_id = ?
            """, (datetime.now().isoformat(), entry_id))
            conn.commit()
            return cursor.rowcount > 0

    def list_entries(
        self,
        entry_type: str = None,
        tag: str = None,
        search: str = None,
        limit: int = 100,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> list[KnowledgeEntry]:
        """列出知识条目"""
        conditions = []
        params = []

        if not include_inactive:
            conditions.append("is_active = 1")

        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        if tag:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if search:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM knowledge_entries 
                WHERE {where_clause}
                ORDER BY importance DESC, updated_at DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            rows = cursor.fetchall()
            return [KnowledgeEntry.from_row(dict(row)) for row in rows]

    def count_entries(
        self,
        entry_type: str = None,
        tag: str = None,
        search: str = None,
        include_inactive: bool = False,
    ) -> int:
        """统计知识条目数量"""
        conditions = []
        params = []

        if not include_inactive:
            conditions.append("is_active = 1")

        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        if tag:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if search:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT COUNT(*) as count FROM knowledge_entries 
                WHERE {where_clause}
            """, params)
            return cursor.fetchone()["count"]

    def record_access(self, entry_id: str) -> None:
        """记录访问"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE knowledge_entries 
                SET access_count = access_count + 1, last_accessed_at = ?
                WHERE entry_id = ?
            """, (now, entry_id))
            conn.commit()

    def get_all_for_indexing(self) -> list[tuple[str, str, dict]]:
        """获取所有条目用于构建向量索引"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT entry_id, title, content, tags, metadata, entry_type
                FROM knowledge_entries 
                WHERE is_active = 1
            """)

            results = []
            for row in cursor.fetchall():
                tags = json.loads(row["tags"]) if row["tags"] else []
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                text = f"{row['title']}\n{row['content']}\n{' '.join(tags)}"
                results.append((
                    row["entry_id"],
                    text,
                    {
                        "entry_type": row["entry_type"],
                        "title": row["title"],
                        "tags": tags,
                        **metadata,
                    },
                ))

            return results

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT entry_type, COUNT(*) as count 
                FROM knowledge_entries 
                WHERE is_active = 1
                GROUP BY entry_type
            """)
            by_type = {row["entry_type"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as total FROM knowledge_entries WHERE is_active = 1")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT SUM(access_count) as total FROM knowledge_entries")
            total_accesses = cursor.fetchone()["total"] or 0

            return {
                "total_entries": total,
                "entries_by_type": by_type,
                "total_accesses": total_accesses,
                "entry_types": ENTRY_TYPES,
            }

    def export_entries(self, entry_ids: list[str] = None) -> list[dict]:
        """导出知识条目"""
        if entry_ids:
            entries = [self.get_entry(eid) for eid in entry_ids]
            entries = [e for e in entries if e]
        else:
            entries = self.list_entries(limit=10000)

        return [e.to_dict() for e in entries]

    def import_entries(self, entries: list[dict], overwrite: bool = False) -> int:
        """导入知识条目"""
        count = 0
        for entry_data in entries:
            entry_id = entry_data.get("entry_id")

            existing = self.get_entry(entry_id) if entry_id else None

            if existing and not overwrite:
                continue

            if existing:
                self.update_entry(
                    entry_id=entry_id,
                    title=entry_data.get("title"),
                    content=entry_data.get("content"),
                    tags=entry_data.get("tags"),
                    metadata=entry_data.get("metadata"),
                    importance=entry_data.get("importance"),
                    entry_type=entry_data.get("entry_type"),
                )
            else:
                self.create_entry(
                    entry_type=entry_data.get("entry_type", ENTRY_TYPE_CUSTOM),
                    title=entry_data.get("title", ""),
                    content=entry_data.get("content", ""),
                    tags=entry_data.get("tags", []),
                    metadata=entry_data.get("metadata", {}),
                    importance=entry_data.get("importance", 0),
                )
            count += 1

        return count

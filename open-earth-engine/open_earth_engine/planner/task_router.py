from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("oea.router")


class TaskRoute(str, Enum):
    STANDARD = "standard"
    OPEN_EARTH = "open_earth"
    MIXED = "mixed"


@dataclass
class TaskComplexity:
    score: int
    route: TaskRoute
    reasons: list[str] = field(default_factory=list)
    multi_source: bool = False
    custom_gis: bool = False
    unknown_sensor: bool = False
    multi_step: bool = False
    fusion_analysis: bool = False


@dataclass
class RouterConfig:
    min_complexity_score: int = 2
    enable_manual_override: bool = True
    complexity_weights: dict[str, int] = field(default_factory=lambda: {
        "multi_source": 3,
        "custom_gis": 2,
        "unknown_sensor": 2,
        "multi_step": 2,
        "fusion_analysis": 3,
    })
    known_sensors: list[str] = field(default_factory=lambda: [
        "GF1", "GF2", "GF3", "GF4", "GF5", "GF6", "GF7",
        "GF-1", "GF-2", "GF-3", "GF-4", "GF-5", "GF-6", "GF-7",
        "Sentinel1", "Sentinel2", "Sentinel-1", "Sentinel-2",
        "Landsat8", "Landsat9", "Landsat-8", "Landsat-9",
        "SAR", "MODIS",
    ])


class TaskRouter:
    """
    任务路由器 - 量化分流规则

    职责:
    1. 判定任务复杂度
    2. 决定任务路由方向（标准工具 / OpenEarth 增强）
    3. 支持人工强制切换

    触发 OpenEarthAgent 分支的任一条件:
    - 多源数据同时参与分析 (SAR+光学+矢量叠加)
    - 需要自定义矢量栅格联动、缓冲区、相交、擦除、分区统计等复杂GIS运算
    - 非标准高分/Sentinel已知传感器、自定义波段组合
    - 3步以上串联自定义流程，现有工具无法链式覆盖
    - 时序变化检测+空间统计融合
    """

    def __init__(self, config: RouterConfig = None):
        self.config = config or RouterConfig()

        self._custom_gis_keywords = [
            "缓冲区", "buffer",
            "相交", "intersect", "intersection",
            "擦除", "erase", "difference",
            "分区统计", "zonal", "zonal_stats", "zonal statistics",
            "栅格转矢量", "raster_to_vector", "polygonize",
            "矢量转栅格", "vector_to_raster", "rasterize",
            "叠加分析", "overlay",
            "裁剪", "clip",
            "融合", "merge", "dissolve",
            "空间连接", "spatial_join", "spatial join",
            "拓扑检查", "topology",
            "网络分析", "network",
            "邻近分析", "proximity", "nearest",
        ]

        self._data_type_keywords = {
            "SAR": ["sar", "sentinel1", "sentinel-1", "雷达", "合成孔径雷达"],
            "光学": ["optical", "sentinel2", "sentinel-2", "landsat", "gf", "高分", "可见光"],
            "矢量": ["vector", "shp", "shapefile", "geojson", "矢量"],
            "栅格": ["raster", "tiff", "geotiff", "栅格"],
        }

        self._fusion_keywords = [
            "时序", "时间序列", "time series",
            "变化检测", "change detection", "change_detection",
            "叠加分析", "融合", "fusion",
        ]

    def route(
        self,
        task_description: str,
        input_data_meta: dict[str, Any] = None,
        manual_override: Optional[TaskRoute] = None,
    ) -> TaskComplexity:
        """
        主路由方法
        """
        if manual_override and self.config.enable_manual_override:
            logger.info(f"Using manual override: {manual_override}")
            return TaskComplexity(
                score=0,
                route=manual_override,
                reasons=[f"Manual override to {manual_override.value}"],
            )

        input_data_meta = input_data_meta or {}
        reasons = []
        score = 0

        complexity = TaskComplexity(
            score=0,
            route=TaskRoute.STANDARD,
            reasons=[],
        )

        complexity.multi_source = self._check_multi_source(task_description, input_data_meta)
        if complexity.multi_source:
            score += self.config.complexity_weights["multi_source"]
            reasons.append("多源数据同时参与分析 (SAR+光学+矢量)")

        complexity.custom_gis = self._check_custom_gis(task_description)
        if complexity.custom_gis:
            score += self.config.complexity_weights["custom_gis"]
            reasons.append("需要自定义GIS运算 (缓冲区/相交/擦除/分区统计等)")

        complexity.unknown_sensor = self._check_unknown_sensor(task_description, input_data_meta)
        if complexity.unknown_sensor:
            score += self.config.complexity_weights["unknown_sensor"]
            reasons.append("非标准传感器或自定义波段组合")

        complexity.multi_step = self._check_multi_step(task_description)
        if complexity.multi_step:
            score += self.config.complexity_weights["multi_step"]
            reasons.append("3步以上串联自定义流程")

        complexity.fusion_analysis = self._check_fusion_analysis(task_description)
        if complexity.fusion_analysis:
            score += self.config.complexity_weights["fusion_analysis"]
            reasons.append("时序变化检测+空间统计融合")

        complexity.score = score
        complexity.reasons = reasons

        if score >= self.config.min_complexity_score:
            complexity.route = TaskRoute.OPEN_EARTH
            logger.info(f"Routing to OpenEarth (score={score}, reasons={reasons})")
        else:
            complexity.route = TaskRoute.STANDARD
            logger.info(f"Routing to Standard tools (score={score})")

        return complexity

    def _check_multi_source(
        self,
        task_description: str,
        input_data_meta: dict[str, Any],
    ) -> bool:
        """
        检查是否多源数据同时参与分析
        """
        data_types = input_data_meta.get("data_types", [])
        if isinstance(data_types, list) and len(data_types) >= 3:
            return True

        task_lower = task_description.lower()
        found_types = set()

        for data_type, keywords in self._data_type_keywords.items():
            for kw in keywords:
                if kw.lower() in task_lower:
                    found_types.add(data_type)
                    break

        return len(found_types) >= 3

    def _check_custom_gis(self, task_description: str) -> bool:
        """
        检查是否需要自定义GIS运算
        """
        task_lower = task_description.lower()
        return any(kw.lower() in task_lower for kw in self._custom_gis_keywords)

    def _check_unknown_sensor(
        self,
        task_description: str,
        input_data_meta: dict[str, Any],
    ) -> bool:
        """
        检查是否为非标准传感器
        """
        sensor = input_data_meta.get("sensor", "")
        if sensor:
            sensor_upper = str(sensor).upper()
            known_upper = [s.upper() for s in self.config.known_sensors]
            if not any(known in sensor_upper for known in known_upper):
                return True

        task_upper = task_description.upper()
        for known in self.config.known_sensors:
            if known.upper() in task_upper:
                return False

        custom_band_patterns = [
            r"band\s*\d+",
            r"波段\s*\d+",
            r"自定义波段",
            r"custom.*band",
        ]
        for pattern in custom_band_patterns:
            if re.search(pattern, task_description, re.IGNORECASE):
                return True

        return False

    def _check_multi_step(self, task_description: str) -> bool:
        """
        检查是否为3步以上串联流程
        """
        step_patterns = [
            r"第[一二三四五六七八九十\d]+步",
            r"step\s*\d+",
            r"然后.*再.*然后",
            r"then.*then.*then",
        ]

        for pattern in step_patterns:
            matches = re.findall(pattern, task_description, re.IGNORECASE)
            if len(matches) >= 3:
                return True

        connectors = ["然后", "接着", "然后再", "再然后", "之后", "之后再", "下一步"]
        count = sum(task_description.count(c) for c in connectors)
        if count >= 2:
            return True

        step_markers = ["1.", "2.", "3.", "①", "②", "③"]
        found_markers = sum(1 for m in step_markers if m in task_description)
        if found_markers >= 3:
            return True

        return False

    def _check_fusion_analysis(self, task_description: str) -> bool:
        """
        检查是否为时序+空间统计融合
        """
        task_lower = task_description.lower()

        has_time_series = any(
            kw.lower() in task_lower
            for kw in ["时序", "时间序列", "变化检测", "time series", "change detection"]
        )

        has_spatial_stats = any(
            kw.lower() in task_lower
            for kw in ["分区", "叠加", "统计", "zonal", "overlay", "statistics", "stats"]
        )

        return has_time_series and has_spatial_stats

    def explain_route(self, complexity: TaskComplexity) -> str:
        """
        生成路由决策的解释文本
        """
        if complexity.route == TaskRoute.STANDARD:
            if not complexity.reasons:
                return "任务简单，适合使用标准MCP工具"
            return (
                f"任务复杂度评分 {complexity.score} < 阈值 {self.config.min_complexity_score}，"
                f"建议使用标准MCP工具"
            )
        else:
            return (
                f"任务复杂度评分 {complexity.score} >= 阈值 {self.config.min_complexity_score}，"
                f"触发OpenEarthAgent增强模式。原因：{'; '.join(complexity.reasons)}"
            )

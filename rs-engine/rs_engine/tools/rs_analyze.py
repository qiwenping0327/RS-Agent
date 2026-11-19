"""
遥感影像智能分析工具

支持 NDVI/NDWI/EVI/SAVI 等光谱指数计算、地物分类、变化检测。

特性:
- 自动波段映射: 根据传感器和指数类型自动匹配波段
- 分类功能: 支持简单阈值分类
- 变化检测: 双时相影像差异分析
- 缩略图预览: 分析完成后自动生成预览图
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

from rs_engine.fault import BreakpointManager
from rs_engine.knowledge import get_index_band_mapping, get_sensor_info, get_rgb_bands

logger = logging.getLogger("rs-engine.tools.analyze")

WORKSPACE = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))


class RsAnalyzeTool:
    """遥感影像智能分析工具"""

    # 支持的分析类型
    ANALYSIS_TYPES = {
        "ndvi": "归一化植被指数",
        "ndwi": "归一化水体指数",
        "evi": "增强植被指数",
        "savi": "土壤调节植被指数",
        "ndbi": "归一化建筑指数",
        "mndwi": "改进水体指数",
        "classification": "地物分类",
        "change_detection": "变化检测",
        "spectral_index": "光谱指数计算",
    }

    # 分析类型别名映射
    ANALYSIS_ALIASES: dict[str, str] = {
        "spectral_index": None,  # 需要额外 index 参数
        "spectral": None,
        "index": None,
    }

    def __init__(self, workspace: str | None = None):
        self.workspace = workspace or WORKSPACE
        self.breakpoint = BreakpointManager(self.workspace)

    async def execute(self, arguments: dict[str, Any]) -> str:
        """
        执行智能分析

        Args:
            arguments: MCP 工具输入参数

        Returns:
            执行结果描述
        """
        input_path = arguments.get("input_path", "")
        analysis_type = arguments.get("analysis_type", "ndvi").lower().strip()
        params = arguments.get("params", {})
        output_dir = arguments.get("output_dir", os.path.join(self.workspace, "analysis"))

        if not input_path:
            return "错误: 缺少 input_path 参数"

        # 处理 spectral_index 类型 - 从 index 参数获取具体指数
        if analysis_type in ("spectral_index", "spectral", "index"):
            index_name = arguments.get("index", params.get("index", "ndvi")).lower().strip()
            if index_name in ("ndvi", "ndwi", "evi", "savi", "ndbi", "mndwi"):
                analysis_type = index_name
            else:
                valid = ", ".join(k for k in self.ANALYSIS_TYPES if k not in ("spectral_index", "ndbi", "mndwi"))
                return f"不支持的光谱指数: {index_name}\n支持的指数: {valid}"

        if analysis_type not in self.ANALYSIS_TYPES:
            valid = ", ".join(self.ANALYSIS_TYPES.keys())
            return f"不支持的分析类型: {analysis_type}\n支持的类型: {valid}"

        os.makedirs(output_dir, exist_ok=True)

        analysis_name = self.ANALYSIS_TYPES[analysis_type]
        logger.info("开始分析: %s (%s)", analysis_name, analysis_type)

        # 根据分析类型分发
        try:
            if analysis_type in ("ndvi", "ndwi", "evi", "savi", "ndbi", "mndwi"):
                result = await self._calc_spectral_index(
                    input_path, analysis_type, params, output_dir
                )
            elif analysis_type == "classification":
                result = await self._classify(input_path, params, output_dir)
            elif analysis_type == "change_detection":
                result = await self._change_detection(input_path, params, output_dir)
            else:
                return f"未实现的分析类型: {analysis_type}"

            return result

        except Exception as exc:
            logger.exception("分析失败: %s", exc)
            return f"分析失败: {exc}"

    async def _calc_spectral_index(
        self, input_path: str, index_name: str, params: dict, output_dir: str
    ) -> str:
        """计算光谱指数"""
        # 获取波段映射
        sensor = params.get("sensor", "sentinel2")
        band_map = get_index_band_mapping(index_name, sensor)

        if not band_map and not params.get("bands"):
            return (
                f"无法自动匹配 {index_name} 在 {sensor} 上的波段。\n"
                f"请在 params.bands 中手动指定波段映射，例如:\n"
                f'  "params": {{"bands": {{"nir": "B08", "red": "B04"}}}}'
            )

        # 合并自动映射和手动覆盖
        bands = {**band_map, **params.get("bands", {})} if band_map else params.get("bands", {})

        # 检测可用库
        has_numpy = self._check_numpy()

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        output_path = os.path.join(output_dir, f"{index_name}_{timestamp}.tif")
        preview_path = os.path.join(output_dir, f"{index_name}_{timestamp}_preview.png")

        if has_numpy and self._check_rasterio():
            return await self._calc_index_rasterio(
                input_path, index_name, bands, output_path, preview_path, sensor
            )
        elif has_numpy:
            return self._calc_index_simulated(
                input_path, index_name, bands, output_path, preview_path, sensor
            )
        else:
            return self._calc_index_simulated(
                input_path, index_name, bands, output_path, preview_path, sensor
            )

    async def _calc_index_rasterio(
        self, input_path, index_name, bands, output_path, preview_path, sensor
    ) -> str:
        """使用 rasterio 计算光谱指数"""
        import numpy as np
        import rasterio

        with rasterio.open(input_path) as src:
            profile = src.profile.copy()
            profile.update(count=1, dtype="float32")

            # 读取波段
            band_data = {}
            for role, band_name in bands.items():
                band_idx = list(src.descriptions or []).index(band_name) + 1 if band_name in (src.descriptions or []) else None
                if band_idx is None:
                    # 尝试按名称映射到波段号
                    sensor_info = get_sensor_info(sensor)
                    if sensor_info and band_name in sensor_info.get("bands", {}):
                        band_names = list(sensor_info["bands"].keys())
                        band_idx = band_names.index(band_name) + 1
                    else:
                        return f"无法在影像中找到波段: {band_name}"
                band_data[role] = src.read(band_idx).astype(np.float32)

        # 计算指数
        result = self._compute_index(index_name, band_data, params={})

        # 写入结果
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(result, 1)

        # 生成预览
        self._generate_preview(result, preview_path, index_name)

        stats = self._calc_stats(result)

        return (
            f"{index_name.upper()} 指数计算完成:\n"
            f"  输入: {input_path}\n"
            f"  输出: {output_path}\n"
            f"  预览: {preview_path}\n"
            f"  波段映射: {bands}\n"
            f"  统计: min={stats['min']:.4f}, max={stats['max']:.4f}, "
            f"mean={stats['mean']:.4f}, std={stats['std']:.4f}"
        )

    def _calc_index_simulated(
        self, input_path, index_name, bands, output_path, preview_path, sensor
    ) -> str:
        """模拟光谱指数计算"""
        import numpy as np

        # 生成模拟结果
        result = np.random.uniform(-0.5, 0.8, (256, 256)).astype(np.float32)

        # 保存模拟结果
        np.save(output_path.replace(".tif", ".npy"), result)

        # 生成预览
        self._generate_preview(result, preview_path, index_name)

        # 保存元数据
        metadata = {
            "index": index_name,
            "bands": bands,
            "sensor": sensor,
            "input_path": input_path,
            "output_path": output_path,
            "preview_path": preview_path,
            "timestamp": datetime.now().isoformat(),
            "status": "simulated",
        }
        with open(output_path.replace(".tif", "_meta.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        stats = self._calc_stats(result)

        return (
            f"{index_name.upper()} 指数计算完成 (模拟模式):\n"
            f"  输入: {input_path}\n"
            f"  输出: {output_path}\n"
            f"  预览: {preview_path}\n"
            f"  波段映射: {bands}\n"
            f"  统计: min={stats['min']:.4f}, max={stats['max']:.4f}, "
            f"mean={stats['mean']:.4f}\n"
            f"  提示: 安装 rasterio/GDAL 以获取真实计算结果"
        )

    @staticmethod
    def _compute_index(index_name: str, band_data: dict, params: dict) -> "np.ndarray":
        """
        计算光谱指数

        Args:
            index_name: 指数名称
            band_data: 波段数据字典 {role: ndarray}
            params: 额外参数
        """
        import numpy as np

        # 避免 0 除
        eps = 1e-10

        if index_name == "ndvi":
            nir = band_data.get("nir", np.zeros((256, 256)))
            red = band_data.get("red", np.zeros((256, 256)))
            return (nir - red) / (nir + red + eps)

        elif index_name == "ndwi":
            green = band_data.get("green", np.zeros((256, 256)))
            nir = band_data.get("nir", np.zeros((256, 256)))
            return (green - nir) / (green + nir + eps)

        elif index_name == "evi":
            nir = band_data.get("nir", np.zeros((256, 256)))
            red = band_data.get("red", np.zeros((256, 256)))
            blue = band_data.get("blue", np.zeros((256, 256)))
            return 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1 + eps)

        elif index_name == "savi":
            nir = band_data.get("nir", np.zeros((256, 256)))
            red = band_data.get("red", np.zeros((256, 256)))
            L = params.get("L", 0.5)
            return (1 + L) * (nir - red) / (nir + red + L + eps)

        elif index_name == "ndbi":
            swir = band_data.get("swir", np.zeros((256, 256)))
            nir = band_data.get("nir", np.zeros((256, 256)))
            return (swir - nir) / (swir + nir + eps)

        elif index_name == "mndwi":
            green = band_data.get("green", np.zeros((256, 256)))
            swir = band_data.get("swir", np.zeros((256, 256)))
            return (green - swir) / (green + swir + eps)

        else:
            raise ValueError(f"未知指数: {index_name}")

    @staticmethod
    def _generate_preview(data: "np.ndarray", output_path: str, index_name: str) -> None:
        """生成缩略图预览"""
        try:
            import numpy as np
            from PIL import Image

            # 归一化到 0-255
            valid = data[~np.isnan(data)]
            if len(valid) == 0:
                return

            p2, p98 = np.percentile(valid, (2, 98))
            normalized = np.clip((data - p2) / (p98 - p2 + 1e-10), 0, 1)
            img_data = (normalized * 255).astype(np.uint8)

            # 应用色彩映射
            colored = _apply_colormap(img_data, index_name)
            img = Image.fromarray(colored)
            img.save(output_path)

        except Exception as exc:
            logger.warning("生成预览失败: %s", exc)

    @staticmethod
    def _calc_stats(data: "np.ndarray") -> dict:
        """计算统计信息"""
        import numpy as np

        valid = data[~np.isnan(data)]
        if len(valid) == 0:
            return {"min": 0, "max": 0, "mean": 0, "std": 0}

        return {
            "min": float(np.min(valid)),
            "max": float(np.max(valid)),
            "mean": float(np.mean(valid)),
            "std": float(np.std(valid)),
        }

    async def _classify(self, input_path: str, params: dict, output_dir: str) -> str:
        """地物分类"""
        method = params.get("method", "threshold")
        classes = params.get("classes", ["water", "vegetation", "urban", "bare_soil"])
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        output_path = os.path.join(output_dir, f"classification_{timestamp}.npy")
        preview_path = os.path.join(output_dir, f"classification_{timestamp}_preview.png")

        # 模拟分类结果
        try:
            import numpy as np
            result = np.random.randint(0, len(classes), (256, 256)).astype(np.uint8)
            np.save(output_path, result)
            self._generate_classification_preview(result, preview_path, classes)
        except ImportError:
            pass

        return (
            f"地物分类完成 (模拟模式):\n"
            f"  输入: {input_path}\n"
            f"  方法: {method}\n"
            f"  分类: {classes}\n"
            f"  输出: {output_path}\n"
            f"  预览: {preview_path}"
        )

    async def _change_detection(self, input_path: str, params: dict, output_dir: str) -> str:
        """变化检测"""
        method = params.get("method", "diff")
        threshold = params.get("threshold", 0.2)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        output_path = os.path.join(output_dir, f"change_{timestamp}.npy")
        preview_path = os.path.join(output_dir, f"change_{timestamp}_preview.png")

        # 模拟变化检测结果
        try:
            import numpy as np
            result = np.random.choice([0, 1], (256, 256), p=[0.85, 0.15]).astype(np.uint8)
            np.save(output_path, result)
            self._generate_change_preview(result, preview_path)
        except ImportError:
            pass

        return (
            f"变化检测完成 (模拟模式):\n"
            f"  输入: {input_path}\n"
            f"  方法: {method}\n"
            f"  阈值: {threshold}\n"
            f"  输出: {output_path}\n"
            f"  预览: {preview_path}"
        )

    @staticmethod
    def _generate_classification_preview(data: "np.ndarray", output_path: str, classes: list) -> None:
        """生成分类预览"""
        try:
            from PIL import Image

            colors = [
                (0, 0, 255),    # 水 - 蓝
                (0, 255, 0),    # 植被 - 绿
                (255, 0, 0),    # 建筑 - 红
                (210, 180, 140), # 裸土 - 棕
                (128, 128, 128), # 其他 - 灰
            ]

            rgb = np.zeros((*data.shape, 3), dtype=np.uint8)
            for i, color in enumerate(colors[:len(classes)]):
                mask = data == i
                rgb[mask] = color

            img = Image.fromarray(rgb)
            img.save(output_path)
        except Exception:
            pass

    @staticmethod
    def _generate_change_preview(data: "np.ndarray", output_path: str) -> None:
        """生成变化检测预览"""
        try:
            from PIL import Image
            import numpy as np

            rgb = np.zeros((*data.shape, 3), dtype=np.uint8)
            rgb[data == 0] = (0, 0, 0)       # 未变化 - 黑
            rgb[data == 1] = (255, 255, 0)    # 变化 - 黄

            img = Image.fromarray(rgb)
            img.save(output_path)
        except Exception:
            pass

    @staticmethod
    def _check_numpy() -> bool:
        try:
            import numpy
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_rasterio() -> bool:
        try:
            import rasterio
            return True
        except ImportError:
            return False


def _apply_colormap(gray: "np.ndarray", index_name: str) -> "np.ndarray":
    """
    应用色彩映射到灰度图

    根据指数类型选择合适的色彩方案。
    """
    import numpy as np

    h, w = gray.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    if index_name in ("ndvi", "evi", "savi"):
        # 植被指数: 蓝(低) -> 黄(中) -> 绿(高)
        for i in range(h):
            for j in range(w):
                v = gray[i, j]
                if v < 85:
                    rgb[i, j] = [0, 0, int(v * 3)]
                elif v < 170:
                    t = (v - 85) / 85.0
                    rgb[i, j] = [int(255 * t), int(255 * t), int(255 * (1 - t))]
                else:
                    t = (v - 170) / 85.0
                    rgb[i, j] = [0, int(255 * (1 - t * 0.5)), 0]

    elif index_name in ("ndwi", "mndwi"):
        # 水体指数: 棕(低) -> 白(中) -> 蓝(高)
        for i in range(h):
            for j in range(w):
                v = gray[i, j]
                if v < 128:
                    rgb[i, j] = [int(139 * (1 - v / 128)), int(90 * (1 - v / 128)), 0]
                else:
                    t = (v - 128) / 127.0
                    rgb[i, j] = [0, 0, int(255 * t)]

    else:
        # 默认: 灰度
        rgb[:, :, 0] = gray
        rgb[:, :, 1] = gray
        rgb[:, :, 2] = gray

    return rgb


# 工具实例
rs_analyze_tool = RsAnalyzeTool()

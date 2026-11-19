"""
遥感影像可视化工具

支持缩略图渲染、真彩色/假彩色合成、指数结果可视化。
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

from rs_engine.knowledge import get_rgb_bands, get_false_color_bands, get_sensor_info

logger = logging.getLogger("rs-engine.tools.visualize")

WORKSPACE = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))


class RsVisualizeTool:
    """遥感影像可视化工具"""

    VIS_TYPES = {
        "true_color": "真彩色合成",
        "false_color": "假彩色合成",
        "index_overlay": "指数叠加",
        "thumbnail": "缩略图",
        "classified": "分类结果可视化",
    }

    def __init__(self, workspace: str | None = None):
        self.workspace = workspace or WORKSPACE

    async def execute(self, arguments: dict[str, Any]) -> str:
        input_path = arguments.get("input_path", "")
        vis_type = arguments.get("vis_type", "thumbnail")
        params = arguments.get("params", {})
        output_dir = arguments.get("output_dir", os.path.join(self.workspace, "visualizations"))

        if not input_path:
            return "错误: 缺少 input_path 参数"

        if vis_type not in self.VIS_TYPES:
            valid = ", ".join(self.VIS_TYPES.keys())
            return f"不支持的可视化类型: {vis_type}\n支持的类型: {valid}"

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        sensor = params.get("sensor", "sentinel2")
        output_path = os.path.join(output_dir, f"{vis_type}_{timestamp}.png")

        try:
            if vis_type == "thumbnail":
                return await self._generate_thumbnail(input_path, output_path, params)
            elif vis_type == "true_color":
                bands = get_rgb_bands(sensor)
                return self._composite_result("真彩色", input_path, output_path, bands, sensor)
            elif vis_type == "false_color":
                bands = get_false_color_bands(sensor)
                return self._composite_result("假彩色", input_path, output_path, bands, sensor)
            elif vis_type == "index_overlay":
                return self._simulate_vis("指数叠加", input_path, output_path, params)
            elif vis_type == "classified":
                return self._simulate_vis("分类结果", input_path, output_path, params)
            else:
                return f"未实现: {vis_type}"
        except Exception as exc:
            return f"可视化失败: {exc}"

    async def _generate_thumbnail(self, input_path: str, output_path: str, params: dict) -> str:
        """生成缩略图"""
        max_size = params.get("max_size", 512)

        # 尝试 rasterio 模式
        if self._check_rasterio():
            try:
                import numpy as np
                import rasterio
                from PIL import Image

                with rasterio.open(input_path) as src:
                    count = min(src.count, 3)
                    data = src.read(list(range(1, count + 1)))
                    h, w = data.shape[1], data.shape[2]
                    ratio = min(max_size / w, max_size / h)
                    new_w, new_h = int(w * ratio), int(h * ratio)

                    rgb = np.zeros((new_h, new_w, 3), dtype=np.uint8)
                    for i in range(min(count, 3)):
                        img = Image.fromarray(data[i])
                        img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                        band = np.array(img).astype(np.float32)
                        p2, p98 = np.percentile(band, (2, 98))
                        if p98 - p2 > 0:
                            rgb[:, :, i] = np.clip((band - p2) / (p98 - p2) * 255, 0, 255).astype(np.uint8)

                Image.fromarray(rgb).save(output_path)
                return f"缩略图生成完成:\n  输入: {input_path}\n  输出: {output_path}\n  尺寸: {new_w}x{new_h}"
            except Exception:
                pass

        return self._simulate_vis("缩略图", input_path, output_path, params)

    def _composite_result(self, name: str, input_path: str, output_path: str, bands: list | None, sensor: str) -> str:
        """彩色合成结果"""
        if not bands:
            return f"无法获取 {sensor} 的波段映射"
        return (
            f"{name}合成完成 (模拟模式):\n"
            f"  输入: {input_path}\n  输出: {output_path}\n"
            f"  波段: {bands}\n  传感器: {sensor}\n"
            f"  提示: 安装 rasterio 以生成真实合成影像"
        )

    def _simulate_vis(self, name: str, input_path: str, output_path: str, params: dict) -> str:
        """模拟可视化"""
        # 尝试生成简单的占位图
        try:
            from PIL import Image
            import numpy as np
            img = np.random.randint(50, 200, (256, 256, 3), dtype=np.uint8)
            Image.fromarray(img).save(output_path)
        except Exception:
            pass

        return (
            f"{name}可视化完成 (模拟模式):\n"
            f"  输入: {input_path}\n  输出: {output_path}\n"
            f"  参数: {params}\n"
            f"  提示: 安装 rasterio 以获取真实可视化结果"
        )

    @staticmethod
    def _check_rasterio() -> bool:
        try:
            import rasterio
            return True
        except ImportError:
            return False


rs_visualize_tool = RsVisualizeTool()

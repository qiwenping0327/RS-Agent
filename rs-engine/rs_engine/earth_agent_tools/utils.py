"""
Earth-Agent 工具辅助函数

提供遥感影像读写功能，支持 GDAL 缺失时的降级处理。
原始项目: https://github.com/opendatalab/Earth-Agent
"""

import logging
import numpy as np

logger = logging.getLogger("rs-engine.earth_agent_tools")

# 尝试导入 GDAL
try:
    from osgeo import gdal
    HAS_GDAL = True
except ImportError:
    HAS_GDAL = False
    logger.warning("GDAL 未安装，部分 GeoTIFF 读写功能不可用")

# 尝试导入 rasterio（作为 GDAL 的替代方案）
try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


def read_image(file_path: str) -> np.ndarray:
    """读取遥感影像文件，返回 NumPy 数组"""
    if HAS_GDAL:
        ds = gdal.Open(file_path)
        if ds is None:
            raise RuntimeError(f"无法打开文件: {file_path}")
        if ds.RasterCount == 1:
            img = ds.GetRasterBand(1).ReadAsArray()
        else:
            img = np.stack([ds.GetRasterBand(i + 1).ReadAsArray() for i in range(ds.RasterCount)], axis=-1)
            if img.ndim == 3:
                img = np.transpose(img, (1, 2, 0))
        ds = None
        return img
    elif HAS_RASTERIO:
        with rasterio.open(file_path) as src:
            img = src.read()
            if img.shape[0] == 1:
                return img[0]
            return np.transpose(img, (1, 2, 0))
    else:
        raise RuntimeError("读取影像需要 GDAL 或 rasterio，请安装其中一个")


def read_image_uint8(file_path: str) -> np.ndarray:
    """读取遥感影像并归一化为 uint8"""
    img = read_image(file_path)
    img = img.astype(np.float32)
    min_val, max_val = img.min(), img.max()
    if max_val == min_val:
        return np.zeros_like(img, dtype=np.uint8)
    return ((img - min_val) / (max_val - min_val) * 255).astype(np.uint8)


def get_geotransform(file_path):
    """获取影像的地理变换参数和投影信息"""
    if HAS_GDAL:
        ds = gdal.Open(file_path)
        if ds is None:
            return None, None
        geo = ds.GetGeoTransform()
        proj = ds.GetProjection()
        ds = None
        if geo == (0, 1.0, 0, 0, 0, 1.0):
            return None, None
        return geo, proj
    elif HAS_RASTERIO:
        with rasterio.open(file_path) as src:
            if src.transform.is_identity:
                return None, None
            return src.transform, src.crs.to_wkt() if src.crs else None
    else:
        raise RuntimeError("获取地理信息需要 GDAL 或 rasterio")

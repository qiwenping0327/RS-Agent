"""
遥感知识库 - 传感器波段映射

提供不同卫星传感器的波段信息，用于自动参数补全。
"""

import logging
from typing import Any

logger = logging.getLogger("rs-engine.knowledge")

# ---------------------------------------------------------------------------
# 传感器波段定义
# ---------------------------------------------------------------------------
SENSOR_BANDS: dict[str, dict[str, Any]] = {
    "sentinel2": {
        "name": "Sentinel-2 MSI",
        "bands": {
            "B01": {"name": "Coastal aerosol", "resolution": 60, "wavelength": "443nm"},
            "B02": {"name": "Blue", "resolution": 10, "wavelength": "490nm"},
            "B03": {"name": "Green", "resolution": 10, "wavelength": "560nm"},
            "B04": {"name": "Red", "resolution": 10, "wavelength": "665nm"},
            "B05": {"name": "Vegetation Red Edge", "resolution": 20, "wavelength": "705nm"},
            "B06": {"name": "Vegetation Red Edge", "resolution": 20, "wavelength": "740nm"},
            "B07": {"name": "Vegetation Red Edge", "resolution": 20, "wavelength": "783nm"},
            "B08": {"name": "NIR", "resolution": 10, "wavelength": "842nm"},
            "B8A": {"name": "Narrow NIR", "resolution": 20, "wavelength": "865nm"},
            "B09": {"name": "Water vapour", "resolution": 60, "wavelength": "945nm"},
            "B11": {"name": "SWIR", "resolution": 20, "wavelength": "1610nm"},
            "B12": {"name": "SWIR", "resolution": 20, "wavelength": "2190nm"},
        },
        "rgb_bands": ["B04", "B03", "B02"],
        "false_color_bands": ["B08", "B04", "B03"],
    },
    "landsat8": {
        "name": "Landsat-8 OLI/TIRS",
        "bands": {
            "B01": {"name": "Coastal aerosol", "resolution": 30, "wavelength": "443nm"},
            "B02": {"name": "Blue", "resolution": 30, "wavelength": "482nm"},
            "B03": {"name": "Green", "resolution": 30, "wavelength": "562nm"},
            "B04": {"name": "Red", "resolution": 30, "wavelength": "655nm"},
            "B05": {"name": "NIR", "resolution": 30, "wavelength": "865nm"},
            "B06": {"name": "SWIR 1", "resolution": 30, "wavelength": "1610nm"},
            "B07": {"name": "SWIR 2", "resolution": 30, "wavelength": "2200nm"},
            "B08": {"name": "Panchromatic", "resolution": 15, "wavelength": "590nm"},
            "B09": {"name": "Cirrus", "resolution": 30, "wavelength": "1375nm"},
            "B10": {"name": "Thermal 1", "resolution": 100, "wavelength": "10900nm"},
            "B11": {"name": "Thermal 2", "resolution": 100, "wavelength": "12000nm"},
        },
        "rgb_bands": ["B04", "B03", "B02"],
        "false_color_bands": ["B05", "B04", "B03"],
    },
    "gf1": {
        "name": "高分一号 PMS",
        "bands": {
            "B01": {"name": "Blue", "resolution": 8, "wavelength": "450-520nm"},
            "B02": {"name": "Green", "resolution": 8, "wavelength": "520-590nm"},
            "B03": {"name": "Red", "resolution": 8, "wavelength": "630-690nm"},
            "B04": {"name": "NIR", "resolution": 8, "wavelength": "770-890nm"},
        },
        "rgb_bands": ["B03", "B02", "B01"],
        "false_color_bands": ["B04", "B03", "B02"],
    },
    "gf2": {
        "name": "高分二号 PMS",
        "bands": {
            "B01": {"name": "Blue", "resolution": 4, "wavelength": "450-520nm"},
            "B02": {"name": "Green", "resolution": 4, "wavelength": "520-590nm"},
            "B03": {"name": "Red", "resolution": 4, "wavelength": "630-690nm"},
            "B04": {"name": "NIR", "resolution": 4, "wavelength": "770-890nm"},
        },
        "rgb_bands": ["B03", "B02", "B01"],
        "false_color_bands": ["B04", "B03", "B02"],
    },
}

# ---------------------------------------------------------------------------
# 遥感指数波段映射
# ---------------------------------------------------------------------------
SPECTRAL_INDICES: dict[str, dict[str, Any]] = {
    "ndvi": {
        "name": "Normalized Difference Vegetation Index",
        "formula": "(NIR - Red) / (NIR + Red)",
        "range": [-1, 1],
        "band_mapping": {
            "sentinel2": {"nir": "B08", "red": "B04"},
            "landsat8": {"nir": "B05", "red": "B04"},
            "gf1": {"nir": "B04", "red": "B03"},
            "gf2": {"nir": "B04", "red": "B03"},
        },
        "description": "植被绿度指标，值越高表示植被越茂盛",
    },
    "ndwi": {
        "name": "Normalized Difference Water Index",
        "formula": "(Green - NIR) / (Green + NIR)",
        "range": [-1, 1],
        "band_mapping": {
            "sentinel2": {"green": "B03", "nir": "B08"},
            "landsat8": {"green": "B03", "nir": "B05"},
            "gf1": {"green": "B02", "nir": "B04"},
            "gf2": {"green": "B02", "nir": "B04"},
        },
        "description": "水体指数，正值通常表示水体",
    },
    "evi": {
        "name": "Enhanced Vegetation Index",
        "formula": "2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)",
        "range": [-1, 1],
        "band_mapping": {
            "sentinel2": {"nir": "B08", "red": "B04", "blue": "B02"},
            "landsat8": {"nir": "B05", "red": "B04", "blue": "B02"},
            "gf1": {"nir": "B04", "red": "B03", "blue": "B01"},
            "gf2": {"nir": "B04", "red": "B03", "blue": "B01"},
        },
        "description": "增强植被指数，减少大气和土壤背景影响",
    },
    "savi": {
        "name": "Soil-Adjusted Vegetation Index",
        "formula": "(1 + L) * (NIR - Red) / (NIR + Red + L)",
        "range": [-1, 1],
        "band_mapping": {
            "sentinel2": {"nir": "B08", "red": "B04"},
            "landsat8": {"nir": "B05", "red": "B04"},
            "gf1": {"nir": "B04", "red": "B03"},
            "gf2": {"nir": "B04", "red": "B03"},
        },
        "params": {"L": 0.5},
        "description": "土壤调节植被指数，适用于稀疏植被区域",
    },
    "ndbi": {
        "name": "Normalized Difference Built-up Index",
        "formula": "(SWIR - NIR) / (SWIR + NIR)",
        "range": [-1, 1],
        "band_mapping": {
            "sentinel2": {"swir": "B11", "nir": "B08"},
            "landsat8": {"swir": "B06", "nir": "B05"},
        },
        "description": "建筑用地指数，正值通常表示建筑区域",
    },
    "mndwi": {
        "name": "Modified NDWI",
        "formula": "(Green - SWIR) / (Green + SWIR)",
        "range": [-1, 1],
        "band_mapping": {
            "sentinel2": {"green": "B03", "swir": "B11"},
            "landsat8": {"green": "B03", "swir": "B06"},
        },
        "description": "改进水体指数，更好地消除建筑影响",
    },
}


def get_index_band_mapping(index_name: str, sensor: str) -> dict[str, str] | None:
    """
    获取指定指数在指定传感器上的波段映射

    Args:
        index_name: 指数名称 (如 ndvi)
        sensor: 传感器名称 (如 sentinel2)

    Returns:
        波段映射字典，如 {"nir": "B08", "red": "B04"}
    """
    index_info = SPECTRAL_INDICES.get(index_name.lower())
    if not index_info:
        return None

    mapping = index_info.get("band_mapping", {}).get(sensor)
    return mapping


def get_sensor_info(sensor: str) -> dict[str, Any] | None:
    """
    获取传感器详细信息

    Args:
        sensor: 传感器名称

    Returns:
        传感器信息字典
    """
    return SENSOR_BANDS.get(sensor)


def get_rgb_bands(sensor: str) -> list[str] | None:
    """
    获取传感器真彩色合成波段

    Args:
        sensor: 传感器名称

    Returns:
        RGB 波段名称列表
    """
    info = SENSOR_BANDS.get(sensor)
    if info:
        return info.get("rgb_bands")
    return None


def get_false_color_bands(sensor: str) -> list[str] | None:
    """
    获取传感器假彩色合成波段

    Args:
        sensor: 传感器名称

    Returns:
        假彩色波段名称列表
    """
    info = SENSOR_BANDS.get(sensor)
    if info:
        return info.get("false_color_bands")
    return None

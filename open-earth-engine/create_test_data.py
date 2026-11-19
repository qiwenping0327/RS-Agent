"""
创建测试数据集 - 多波段测试影像用于 NDVI 计算

创建一个模拟的 Sentinel-2 测试影像（包含 NIR、Red、Green、Blue 波段）
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
import os

DATA_DIR = "/root/PilotDeck/data/test_scenes"
os.makedirs(DATA_DIR, exist_ok=True)


def create_test_image(output_path, width=512, height=512, seed=42):
    """
    创建测试影像
    - 包含 4 个波段：B02(蓝), B03(绿), B04(红), B08(近红外)
    - 模拟植被区（高 NDVI）、水体区（低 NDVI）、建筑区（中 NDVI）
    """
    np.random.seed(seed)

    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": 4,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_bounds(116.0, 39.0, 117.0, 40.0, width, height),
        "nodata": 0.0,
    }

    red = np.random.uniform(0.1, 0.4, (height, width)).astype(np.float32)
    nir = np.random.uniform(0.2, 0.6, (height, width)).astype(np.float32)
    green = np.random.uniform(0.15, 0.45, (height, width)).astype(np.float32)
    blue = np.random.uniform(0.1, 0.35, (height, width)).astype(np.float32)

    for y in range(height):
        for x in range(width):
            cx, cy = width / 2, height / 2
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max(width, height)

            if dist < 0.15:
                nir[y, x] = np.random.uniform(0.5, 0.7)
                red[y, x] = np.random.uniform(0.1, 0.2)
            elif dist < 0.35:
                nir[y, x] = np.random.uniform(0.1, 0.2)
                red[y, x] = np.random.uniform(0.4, 0.6)
            else:
                nir[y, x] = np.random.uniform(0.15, 0.25)
                red[y, x] = np.random.uniform(0.2, 0.3)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(blue, 1)
        dst.write(green, 2)
        dst.write(red, 3)
        dst.write(nir, 4)

        dst.set_band_description(1, "B02")
        dst.set_band_description(2, "B03")
        dst.set_band_description(3, "B04")
        dst.set_band_description(4, "B08")

    return output_path


def create_test_image_v2(output_path, width=512, height=512, seed=43):
    """
    创建第二个测试影像（用于变化检测）
    """
    np.random.seed(seed)

    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": 4,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_bounds(116.0, 39.0, 117.0, 40.0, width, height),
        "nodata": 0.0,
    }

    red = np.random.uniform(0.15, 0.45, (height, width)).astype(np.float32)
    nir = np.random.uniform(0.15, 0.5, (height, width)).astype(np.float32)
    green = np.random.uniform(0.2, 0.5, (height, width)).astype(np.float32)
    blue = np.random.uniform(0.12, 0.4, (height, width)).astype(np.float32)

    for y in range(height):
        for x in range(width):
            cx, cy = width / 3, height / 3
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max(width, height)

            if dist < 0.2:
                nir[y, x] = np.random.uniform(0.1, 0.25)
                red[y, x] = np.random.uniform(0.45, 0.65)
            elif y < height / 2 and x > width / 2:
                nir[y, x] = np.random.uniform(0.55, 0.75)
                red[y, x] = np.random.uniform(0.08, 0.18)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(blue, 1)
        dst.write(green, 2)
        dst.write(red, 3)
        dst.write(nir, 4)

        dst.set_band_description(1, "B02")
        dst.set_band_description(2, "B03")
        dst.set_band_description(3, "B04")
        dst.set_band_description(4, "B08")

    return output_path


def create_water_body_test_image(output_path, width=512, height=512, seed=44):
    """
    创建水体测试影像（用于 NDWI 计算）
    """
    np.random.seed(seed)

    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": 4,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_bounds(120.0, 30.0, 121.0, 31.0, width, height),
        "nodata": 0.0,
    }

    green = np.random.uniform(0.2, 0.5, (height, width)).astype(np.float32)
    nir = np.random.uniform(0.25, 0.55, (height, width)).astype(np.float32)
    red = np.random.uniform(0.15, 0.4, (height, width)).astype(np.float32)
    blue = np.random.uniform(0.15, 0.4, (height, width)).astype(np.float32)

    center_y = int(height * 0.3)
    center_x = int(width * 0.5)
    for y in range(height):
        for x in range(width):
            dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2) / (height * 0.3)
            if dist < 1.0:
                green[y, x] = np.random.uniform(0.35, 0.55)
                nir[y, x] = np.random.uniform(0.05, 0.15)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(blue, 1)
        dst.write(green, 2)
        dst.write(red, 3)
        dst.write(nir, 4)

        dst.set_band_description(1, "B02")
        dst.set_band_description(2, "B03")
        dst.set_band_description(3, "B04")
        dst.set_band_description(4, "B08")

    return output_path


if __name__ == "__main__":
    print("创建测试数据集...")

    image1 = create_test_image(
        os.path.join(DATA_DIR, "beijing_test_scene_2024-01-01.tif")
    )
    print(f"  创建: {image1}")

    image2 = create_test_image_v2(
        os.path.join(DATA_DIR, "beijing_test_scene_2024-07-01.tif")
    )
    print(f"  创建: {image2}")

    image3 = create_water_body_test_image(
        os.path.join(DATA_DIR, "yangtze_test_scene.tif")
    )
    print(f"  创建: {image3}")

    print(f"\n测试数据目录: {DATA_DIR}")
    print("可用的测试场景:")
    print(f"  1. beijing_test_scene_2024-01-01.tif - 北京冬季场景 (低植被)")
    print(f"  2. beijing_test_scene_2024-07-01.tif - 北京夏季场景 (高植被)")
    print(f"  3. yangtze_test_scene.tif - 长江水体场景 (用于 NDWI)")

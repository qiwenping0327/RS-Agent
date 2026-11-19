"""
遥感智能分析 Agent - 环境检查脚本

检查运行环境是否满足要求，包括 Python 版本、依赖包、GDAL、GPU 等。

使用方式:
    python check_rs_env.py
"""

import sys


def check_python_version() -> bool:
    """检查 Python 版本"""
    required = (3, 10)
    current = sys.version_info[:2]
    ok = current >= required
    status = "✓" if ok else "✗"
    print(f"  {status} Python 版本: {current[0]}.{current[1]} (需要 >={required[0]}.{required[1]})")
    return ok


def check_package(package_name: str, import_name: str | None = None) -> bool:
    """检查 Python 包是否可用"""
    name = import_name or package_name
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", "未知版本")
        print(f"  ✓ {package_name}: {version}")
        return True
    except ImportError:
        print(f"  ✗ {package_name}: 未安装")
        return False


def check_gdal() -> bool:
    """检查 GDAL"""
    try:
        from osgeo import gdal

        version = gdal.__version__
        print(f"  ✓ GDAL: {version}")
        return True
    except ImportError:
        print("  ✗ GDAL: 未安装 (遥感影像处理核心依赖)")
        return False


def check_gpu() -> bool:
    """检查 GPU"""
    try:
        import torch

        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            name = torch.cuda.get_device_name(0) if count > 0 else "未知"
            print(f"  ✓ GPU: {name} (x{count})")
            return True
        else:
            print("  - GPU: CUDA 可用但未检测到 GPU")
            return False
    except ImportError:
        print("  - GPU: PyTorch 未安装 (可选依赖)")
        return False


def check_disk_space() -> bool:
    """检查磁盘空间"""
    import shutil

    try:
        usage = shutil.disk_usage(__import__("os").environ.get("RS_WORKSPACE", "/workspace") if __import__("os").path.exists(__import__("os").environ.get("RS_WORKSPACE", "/workspace")) else ".")
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        status = "✓" if free_gb > 50 else "⚠"
        print(f"  {status} 磁盘空间: {free_gb:.1f}GB 可用 / {total_gb:.1f}GB 总计")
        return free_gb > 50
    except Exception:
        print("  ⚠ 磁盘空间: 无法检查")
        return False


def main():
    print("=" * 60)
    print("遥感智能分析 Agent - 环境检查")
    print("=" * 60)

    all_ok = True

    print("\n[1] Python 版本")
    all_ok &= check_python_version()

    print("\n[2] 核心依赖")
    core_packages = [
        ("mcp", "mcp"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("rasterio", "rasterio"),
        ("numpy", "numpy"),
        ("shapely", "shapely"),
        ("geopandas", "geopandas"),
        ("pyproj", "pyproj"),
        ("Pillow", "PIL"),
        ("requests", "requests"),
    ]
    for pkg, imp in core_packages:
        all_ok &= check_package(pkg, imp)

    print("\n[3] GDAL")
    check_gdal()  # 不计入 all_ok，GDAL 安装复杂

    print("\n[4] GPU (可选)")
    check_gpu()

    print("\n[5] 磁盘空间")
    check_disk_space()

    print("\n" + "=" * 60)
    if all_ok:
        print("✓ 环境检查通过，可以运行 rs-agent")
    else:
        print("✗ 部分依赖缺失，请安装后重试")
        print("  安装命令: pip install -r requirements.txt")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

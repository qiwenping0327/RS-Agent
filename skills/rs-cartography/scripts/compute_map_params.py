#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遥感影像出图参数计算器
Aesthetic Remote Sensing Map - Map Parameter Calculator

根据卫星/像元分辨率、出图尺寸、打印分辨率，计算：
  - 所需影像像元数
  - 制图比例尺 1:n
  - 重采样建议
  - 文字磅值建议
  - 留白建议

用法：
  python compute_map_params.py --satellite GF-2 --width 120 --height 90 --dpi 150
  python compute_map_params.py --resolution 0.8 --width 60 --height 90 --dpi 180 --medium silk
  python compute_map_params.py --list-satellites

也可 import 后在 Python 中调用 compute()。
"""

import argparse
import sys
import math

# 国产陆地卫星主要载荷像元分辨率 (m)
SATELLITES = {
    "GF-7":      {"resolution": 0.65, "bits": 11, "note": "全色0.65m"},
    "GF-2":      {"resolution": 0.8,  "bits": 10, "note": "全色0.8m/多光谱3.2m"},
    "GF-1":      {"resolution": 2.0,  "bits": 10, "note": "全色2m/多光谱8m(混叠慎锐化)"},
    "ZY-3":      {"resolution": 2.1,  "bits": 10, "note": "三线阵立体"},
    "ZY1-02C":   {"resolution": 2.36, "bits": 10, "note": "缺蓝波段(近似真彩色法2)"},
    "CBERS-04":  {"resolution": 5.0,  "bits": 10, "note": "缺蓝波段"},
    "QuickBird": {"resolution": 0.61, "bits": 11, "note": ""},
    "IKONOS":    {"resolution": 1.0,  "bits": 11, "note": ""},
    "Landsat-8": {"resolution": 15.0, "bits": 12, "note": "多光谱30m/全色15m"},
    "Sentinel-2":{"resolution": 10.0, "bits": 12, "note": "多光谱10m"},
    "SPOT-5":    {"resolution": 2.5,  "bits": 8,  "note": "缺蓝波段"},
}

# 标准推荐打印分辨率
RECOMMEND_DPI = 150
DPI_LOWER = 127
DPI_UPPER = 180
RESAMPLE_MIN_DPI = 300  # 重采样后不低于
SAR_DPI = (200, 250)    # SAR 影像推荐区间


def compute(resolution_m, width_cm, height_cm, dpi, medium="photo", sample_ratio=1.0):
    """
    计算出图参数。

    Args:
        resolution_m: 像元空间分辨率 (m)
        width_cm: 出图宽度 (cm, 含留白)
        height_cm: 出图高度 (cm, 含留白)
        dpi: 打印分辨率 (DPI)
        medium: 介质 "photo"(相纸) 或 "silk"(绢丝布)
        sample_ratio: 抽样比例 (1.0=全分辨率, 0.5=抽样一半)

    Returns:
        dict: 计算结果
    """
    # 像元数 = 边长(cm) × DPI / 2.54
    pixels_w = int(round(width_cm * dpi / 2.54))
    pixels_h = int(round(height_cm * dpi / 2.54))

    # 制图比例尺 1:n = 像元分辨率(m) × DPI / 25.4 × 1000
    n = resolution_m * dpi / 25.4 * 1000 * sample_ratio

    # 实际地面覆盖范围 (km)
    ground_w_km = pixels_w * resolution_m * sample_ratio / 1000.0
    ground_h_km = pixels_h * resolution_m * sample_ratio / 1000.0

    # mm/pixel
    mm_per_pixel = 25.4 / dpi

    # 文件大小估算 (8位/通道, 3通道, 未压缩)
    file_size_mb = pixels_w * pixels_h * 3 / (1024 * 1024)

    # 文字磅值建议 (依据表3, 磅值 ≈ 宽cm/3.5 取整, 上部磅值=宽cm~宽cm+10)
    # 表3: 100cm→30, 110→32, 120→34, 130→36, 140→38, 150→40 → 磅值≈宽/3.4
    body_point = max(20, round(width_cm / 3.4))
    title_point = (width_cm, width_cm + 10)

    # 留白建议
    if medium == "photo":
        margin = {
            "rod_top_bottom": "8-10cm",
            "rod_left_right": "5cm",
            "frame_with_text_top_bottom": "9cm",
            "frame_with_text_left_right": "9cm",
            "frame_no_text_top_bottom": "6cm",
        }
        actual_image = "实际影像约 110cm×75cm (穿杆/装框后)"
    else:  # silk
        margin = {"note": "绢丝布无留白，直接装裱，短边≤68cm"}
        actual_image = "60cm×90cm 竖版直接装裱"

    # 重采样建议
    resample_advice = ""
    if pixels_w > 20000 or pixels_h > 20000:
        # 建议重采样到打印分辨率不低于 300DPI
        target_w_300 = int(round(width_cm * RESAMPLE_MIN_DPI / 2.54))
        target_h_300 = int(round(height_cm * RESAMPLE_MIN_DPI / 2.54))
        resample_advice = (
            f"像元数过多({pixels_w}×{pixels_h})，建议立方卷积重采样至 "
            f"约 {target_w_300}×{target_h_300} (300DPI)，打印质量不降且文件更小。"
        )

    # 分辨率适应性建议
    dpi_advice = ""
    if dpi < DPI_LOWER:
        dpi_advice = f"DPI={dpi} 低于下限{DPI_LOWER}，成像条件好时可提比例尺，否则建议提高。"
    elif dpi > DPI_UPPER:
        dpi_advice = f"DPI={dpi} 高于上限{DPI_UPPER}，像元数偏多，可适度降低以提高比例尺(质量允许时)。"
    else:
        dpi_advice = f"DPI={dpi} 在推荐区间[{DPI_LOWER},{DPI_UPPER}]，{RECOMMEND_DPI}DPI为标准推荐。"

    return {
        "resolution_m": resolution_m,
        "width_cm": width_cm,
        "height_cm": height_cm,
        "dpi": dpi,
        "medium": medium,
        "pixels_w": pixels_w,
        "pixels_h": pixels_h,
        "pixels_total": pixels_w * pixels_h,
        "map_scale_n": int(round(n)),
        "map_scale": f"1:{int(round(n)):,}",
        "ground_coverage_km": f"{ground_w_km:.1f}km × {ground_h_km:.1f}km",
        "mm_per_pixel": round(mm_per_pixel, 3),
        "file_size_mb_est": round(file_size_mb, 1),
        "body_text_point": body_point,
        "title_text_point": title_point,
        "margin": margin,
        "actual_image": actual_image,
        "resample_advice": resample_advice,
        "dpi_advice": dpi_advice,
    }


def format_scale(n):
    """格式化比例尺: 1:n，n保留2-3位有效数字低位补零，后三位与前部空一格。"""
    s = str(n)
    if len(s) <= 3:
        return f"1:{s}"
    # 后三位与前部空一格
    return f"1:{s[:-3]} {s[-3:]}"


def print_result(r):
    """友好打印计算结果。"""
    print("=" * 60)
    print("  遥感影像出图参数计算结果")
    print("=" * 60)
    print(f"像元分辨率:     {r['resolution_m']} m")
    print(f"出图尺寸:       {r['width_cm']}cm × {r['height_cm']}cm ({r['medium']})")
    print(f"打印分辨率:     {r['dpi']} DPI  ({r['mm_per_pixel']} mm/pixel)")
    print("-" * 60)
    print(f"所需影像像元:   {r['pixels_w']} × {r['pixels_h']} = {r['pixels_total']:,} 像元")
    print(f"制图比例尺:     {format_scale(r['map_scale_n'])}  (n={r['map_scale_n']:,})")
    print(f"地面覆盖范围:   {r['ground_coverage_km']}")
    print(f"文件大小估算:   ~{r['file_size_mb_est']} MB (8位/3通道/未压缩)")
    print("-" * 60)
    print(f"正文磅值建议:   {r['body_text_point']} 磅 (左下/正下/右下)")
    print(f"标题磅值建议:   {r['title_text_point'][0]}-{r['title_text_point'][1]} 磅 (上部)")
    print(f"留白设置:       {r['actual_image']}")
    if isinstance(r['margin'], dict):
        for k, v in r['margin'].items():
            print(f"  {k}: {v}")
    print("-" * 60)
    print(f"DPI 建议: {r['dpi_advice']}")
    if r['resample_advice']:
        print(f"重采样建议: {r['resample_advice']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="遥感影像出图参数计算器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --satellite GF-2 --width 120 --height 90 --dpi 150
  %(prog)s --resolution 0.8 --width 60 --height 90 --dpi 180 --medium silk
  %(prog)s --list-satellites
        """,
    )
    parser.add_argument("--satellite", help="卫星名称 (如 GF-2, GF-1, ZY-3)")
    parser.add_argument("--resolution", type=float, help="像元分辨率 (m)，与 --satellite 二选一")
    parser.add_argument("--width", type=float, default=120, help="出图宽度 cm (默认120)")
    parser.add_argument("--height", type=float, default=90, help="出图高度 cm (默认90)")
    parser.add_argument("--dpi", type=int, default=150, help="打印分辨率 DPI (默认150)")
    parser.add_argument("--medium", choices=["photo", "silk"], default="photo", help="介质: photo相纸/silk绢丝布 (默认photo)")
    parser.add_argument("--sample-ratio", type=float, default=1.0, help="抽样比例 (默认1.0全分辨率)")
    parser.add_argument("--list-satellites", action="store_true", help="列出支持的卫星")

    args = parser.parse_args()

    if args.list_satellites:
        print("支持的卫星:")
        print(f"{'名称':<14}{'分辨率(m)':<12}{'比特':<8}备注")
        print("-" * 60)
        for name, info in SATELLITES.items():
            print(f"{name:<14}{info['resolution']:<12}{info['bits']:<8}{info['note']}")
        return

    # 确定分辨率
    if args.resolution is not None:
        resolution = args.resolution
        sat_name = f"自定义({resolution}m)"
    elif args.satellite is not None:
        sat_name = args.satellite
        if sat_name not in SATELLITES:
            print(f"错误: 未知卫星 '{sat_name}'，使用 --list-satellites 查看支持的卫星", file=sys.stderr)
            sys.exit(1)
        resolution = SATELLITES[sat_name]["resolution"]
    else:
        parser.error("必须指定 --satellite 或 --resolution")

    r = compute(
        resolution_m=resolution,
        width_cm=args.width,
        height_cm=args.height,
        dpi=args.dpi,
        medium=args.medium,
        sample_ratio=args.sample_ratio,
    )
    r["satellite"] = sat_name
    print_result(r)


if __name__ == "__main__":
    main()

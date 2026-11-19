"""
资源管控层 - 磁盘管控
"""

import logging
import os
import shutil
from typing import Any

logger = logging.getLogger("rs-engine.resource")


class DiskManager:
    """
    磁盘空间管控

    监控工作空间磁盘使用，支持配额检查和清理建议。
    """

    def __init__(self, workspace: str = "", quota_mb: float = 102400):
        if not workspace:
            workspace = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))
        self.workspace = workspace
        self.quota_mb = quota_mb

    def get_usage(self) -> dict[str, float]:
        """
        获取磁盘使用情况

        Returns:
            {"used_mb": ..., "total_mb": ..., "free_mb": ..., "usage_percent": ...}
        """
        target = self.workspace
        try:
            usage = shutil.disk_usage(target)
        except FileNotFoundError:
            logger.warning("路径 %s 不存在，回退到根目录检测磁盘空间", target)
            try:
                usage = shutil.disk_usage("/")
            except Exception as e:
                logger.error("获取磁盘使用情况失败: %s", e)
                return {"used_mb": 0, "total_mb": 0, "free_mb": 0, "usage_percent": 0}
        except Exception as e:
            logger.error("获取磁盘使用情况失败: %s", e)
            return {"used_mb": 0, "total_mb": 0, "free_mb": 0, "usage_percent": 0}

        used_mb = usage.used / (1024 * 1024)
        total_mb = usage.total / (1024 * 1024)
        free_mb = total_mb - used_mb
        percent = (used_mb / total_mb * 100) if total_mb > 0 else 0

        return {
            "used_mb": round(used_mb, 1),
            "total_mb": round(total_mb, 1),
            "free_mb": round(free_mb, 1),
            "usage_percent": round(percent, 1),
        }

    def check_quota(self, required_mb: float = 0) -> tuple[bool, str]:
        """
        检查磁盘配额

        Args:
            required_mb: 所需空间 (MB)

        Returns:
            (是否满足, 描述信息)
        """
        usage = self.get_usage()
        free_mb = usage["free_mb"]

        if free_mb < required_mb:
            return False, f"磁盘空间不足: 需要 {required_mb:.0f}MB, 可用 {free_mb:.0f}MB"

        if usage["usage_percent"] > 90:
            return False, f"磁盘使用率超过 90% ({usage['usage_percent']:.1f}%), 请清理空间"

        return True, "磁盘空间充足"

    def scan_large_files(self, path: str | None = None, top_n: int = 10) -> list[dict[str, Any]]:
        """
        扫描大文件

        Args:
            path: 扫描路径，默认工作空间
            top_n: 返回前 N 个大文件

        Returns:
            文件列表，按大小降序排列
        """
        target = path or self.workspace
        files = []

        for root, _, filenames in os.walk(target):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                try:
                    size = os.path.getsize(filepath)
                    files.append({"path": filepath, "size_mb": round(size / (1024 * 1024), 2)})
                except OSError:
                    continue

        files.sort(key=lambda x: x["size_mb"], reverse=True)
        return files[:top_n]

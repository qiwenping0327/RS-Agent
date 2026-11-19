"""
资源管控层 - 配额检查
"""

import logging
import os
import shutil
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("rs-engine.resource")


@dataclass
class ResourceQuota:
    """资源配额配置"""

    cpu_cores: int = 2
    memory_mb: int = 8192
    disk_mb: int = 102400  # 100GB
    gpu_count: int = 1


@dataclass
class ResourceUsage:
    """当前资源使用情况"""

    cpu_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_used_mb: float = 0.0
    gpu_used: int = 0
    gpu_total: int = 0


class QuotaChecker:
    """
    资源配额检查器

    检查当前系统资源是否满足任务需求。
    通过 PreToolUse Hook 调用，在工具执行前判断资源是否充足。
    """

    def __init__(self, workspace: str = "", quota: ResourceQuota | None = None):
        if not workspace:
            workspace = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))
        self.workspace = workspace
        self.quota = quota or ResourceQuota()
        self._gpu_available = self._detect_gpu()

    def _detect_gpu(self) -> bool:
        """检测 GPU 是否可用"""
        try:
            import torch
            available = torch.cuda.is_available()
            if available:
                device_count = torch.cuda.device_count()
                logger.info("检测到 %d 个 GPU", device_count)
                return True
        except ImportError:
            pass

        # 尝试通过 nvidia-smi 检测
        try:
            result = os.popen("nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null")
            if result.read().strip():
                logger.info("通过 nvidia-smi 检测到 GPU")
                return True
        except Exception:
            pass

        logger.info("未检测到 GPU，将使用 CPU 模式")
        return False

    def get_disk_usage(self, path: str | None = None) -> tuple[float, float]:
        """
        获取磁盘使用情况

        Returns:
            (used_mb, total_mb)
        """
        target = path or self.workspace
        try:
            usage = shutil.disk_usage(target)
            return usage.used / (1024 * 1024), usage.total / (1024 * 1024)
        except FileNotFoundError:
            # workspace 路径不存在时，回退到根目录检测
            logger.warning("路径 %s 不存在，回退到根目录检测磁盘空间", target)
            try:
                usage = shutil.disk_usage("/")
                return usage.used / (1024 * 1024), usage.total / (1024 * 1024)
            except Exception:
                return 0.0, 0.0
        except Exception:
            logger.error("获取磁盘使用情况失败: %s", target)
            return 0.0, 0.0

    async def check(self, tool_name: str, tool_input: dict[str, Any]) -> tuple[bool, str]:
        """
        检查资源是否充足

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            (是否充足, 描述信息)
        """
        # 检查磁盘空间
        used_mb, total_mb = self.get_disk_usage()
        free_mb = total_mb - used_mb

        # 估算所需磁盘空间
        estimated_mb = self._estimate_disk_need(tool_name, tool_input)
        if estimated_mb > 0 and free_mb < estimated_mb:
            return (
                False,
                f"磁盘空间不足: 需要 {estimated_mb:.0f}MB, 可用 {free_mb:.0f}MB",
            )

        # 检查 GPU 需求
        needs_gpu = tool_name in ("rs_model_inference", "rs_sar_analysis")
        if needs_gpu and not self._gpu_available:
            logger.warning(
                "工具 %s 需要 GPU，但当前环境无 GPU，将使用 CPU 模式（速度较慢）",
                tool_name,
            )

        return True, "资源检查通过"

    def _estimate_disk_need(self, tool_name: str, tool_input: dict) -> float:
        """
        估算工具所需磁盘空间 (MB)

        基于经验值粗略估算，实际消耗可能不同。
        """
        estimates = {
            "rs_download": 5000,     # 单次下载约 5GB
            "rs_preprocess": 3000,   # 预处理中间文件约 3GB
            "rs_analyze": 2000,      # 分析结果约 2GB
            "rs_sar_analysis": 4000, # SAR 数据较大
            "rs_model_inference": 1000,  # 推理结果较小
            "rs_visualize": 500,
            "rs_report": 50,
        }
        return estimates.get(tool_name, 0)

    @property
    def gpu_available(self) -> bool:
        """GPU 是否可用"""
        return self._gpu_available

    def get_status(self) -> dict[str, Any]:
        """获取资源状态概览"""
        used_mb, total_mb = self.get_disk_usage()
        return {
            "disk": {
                "used_mb": round(used_mb, 1),
                "total_mb": round(total_mb, 1),
                "free_mb": round(total_mb - used_mb, 1),
            },
            "gpu": {
                "available": self._gpu_available,
                "count": 0,  # TODO: 实现精确 GPU 计数
            },
            "quota": {
                "cpu_cores": self.quota.cpu_cores,
                "memory_mb": self.quota.memory_mb,
                "disk_mb": self.quota.disk_mb,
                "gpu_count": self.quota.gpu_count,
            },
        }

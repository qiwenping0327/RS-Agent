"""
资源管控层 - GPU 调度队列
"""

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger("rs-engine.resource")


class GpuScheduler:
    """
    GPU 调度队列

    通过 CUDA_VISIBLE_DEVICES 环境变量控制 GPU 分配，
    支持多任务并发时自动排队等待 GPU 资源。
    """

    def __init__(self, gpu_count: int | None = None):
        """
        Args:
            gpu_count: 可用 GPU 数量，None 时自动检测
        """
        self._gpu_count = gpu_count or self._detect_gpu_count()
        self._semaphore = asyncio.Semaphore(max(self._gpu_count, 1))
        self._gpu_in_use: set[int] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _detect_gpu_count() -> int:
        """检测可用 GPU 数量"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.device_count()
        except ImportError:
            pass

        # 从环境变量读取
        cuda_devices = os.environ.get("CUDA_VISIBLE_DEVICES", "")
        if cuda_devices and cuda_devices != "-1":
            return len(cuda_devices.split(","))

        return 0

    @property
    def gpu_count(self) -> int:
        """可用 GPU 数量"""
        return self._gpu_count

    async def acquire(self, task_id: str = "") -> int | None:
        """
        获取一个 GPU

        Args:
            task_id: 任务 ID（用于日志）

        Returns:
            GPU 索引，无 GPU 可用时返回 None
        """
        if self._gpu_count == 0:
            return None

        await self._semaphore.acquire()

        async with self._lock:
            # 分配空闲 GPU
            for i in range(self._gpu_count):
                if i not in self._gpu_in_use:
                    self._gpu_in_use.add(i)
                    logger.info("GPU #%d 分配给任务 %s", i, task_id)
                    return i

        # 不应该到达这里（信号量保证有资源）
        self._semaphore.release()
        return None

    async def release(self, gpu_index: int, task_id: str = "") -> None:
        """
        释放 GPU

        Args:
            gpu_index: GPU 索引
            task_id: 任务 ID
        """
        async with self._lock:
            self._gpu_in_use.discard(gpu_index)
            logger.info("GPU #%d 已释放 (任务 %s)", gpu_index, task_id)

        self._semaphore.release()

    def get_status(self) -> dict[str, Any]:
        """获取 GPU 调度状态"""
        return {
            "total": self._gpu_count,
            "in_use": list(self._gpu_in_use),
            "available": self._gpu_count - len(self._gpu_in_use),
        }

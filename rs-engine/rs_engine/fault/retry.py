"""
故障容错层 - 指数退避重试
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger("rs-engine.fault")

T = TypeVar("T")

# 默认重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # 秒
DEFAULT_MAX_DELAY = 60.0  # 秒
DEFAULT_JITTER = 0.1  # 10% 随机抖动


def exponential_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: float = DEFAULT_JITTER,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        jitter: 随机抖动比例
        retryable_exceptions: 可重试的异常类型

    使用示例:
        @exponential_backoff(max_retries=3, base_delay=2.0)
        async def download_sentinel_data(...):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        # 计算退避延迟
                        delay = min(base_delay * (2**attempt), max_delay)
                        # 添加随机抖动
                        jitter_amount = delay * jitter * random.random()
                        total_delay = delay + jitter_amount

                        logger.warning(
                            "第 %d 次重试 (共 %d 次): %s, 等待 %.1f 秒",
                            attempt + 1,
                            max_retries,
                            str(exc)[:200],
                            total_delay,
                        )
                        await asyncio.sleep(total_delay)
                    else:
                        logger.error(
                            "重试 %d 次后仍然失败: %s", max_retries, str(exc)[:200]
                        )

            raise last_exception  # type: ignore

        return wrapper

    return decorator


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    **kwargs,
) -> Any:
    """
    函数式重试接口

    Args:
        func: 要重试的异步函数
        *args: 函数位置参数
        max_retries: 最大重试次数
        base_delay: 基础延迟
        **kwargs: 函数关键字参数

    Returns:
        函数返回值
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries:
                delay = min(DEFAULT_BASE_DELAY * (2**attempt), DEFAULT_MAX_DELAY)
                logger.warning(
                    "第 %d 次重试: %s, 等待 %.1f 秒",
                    attempt + 1,
                    str(exc)[:200],
                    delay,
                )
                await asyncio.sleep(delay)

    raise last_exception  # type: ignore

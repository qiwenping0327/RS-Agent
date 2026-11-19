from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("oea.cache")


class CacheBackendType(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    HYBRID = "hybrid"


@dataclass
class CacheMetadata:
    cache_key: str
    source_file: str
    operation: str
    params: dict[str, Any]
    file_size: int
    crs: Optional[str] = None
    resolution: Optional[tuple[float, float]] = None
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: int = 7 * 24 * 3600
    backend: str = "local"


@dataclass
class CacheConfig:
    backend_type: CacheBackendType = CacheBackendType.LOCAL
    local_root: str = "/tmp/oea_cache"
    max_size_gb: float = 100.0
    ttl_seconds: int = 7 * 24 * 3600
    s3_bucket: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_region: str = "us-east-1"
    hybrid_local_gb: float = 50.0


class LocalFileBackend:
    """本地文件缓存后端"""

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.metadata_dir = os.path.join(root_dir, ".metadata")
        os.makedirs(self.root_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)

    def _get_data_path(self, cache_key: str) -> str:
        subdir = cache_key[:2] if len(cache_key) >= 2 else "xx"
        return os.path.join(self.root_dir, subdir, f"{cache_key}.tif")

    def _get_meta_path(self, cache_key: str) -> str:
        return os.path.join(self.metadata_dir, f"{cache_key}.json")

    async def exists(self, cache_key: str) -> bool:
        return os.path.exists(self._get_data_path(cache_key))

    async def get(self, cache_key: str, local_path: str) -> bool:
        src = self._get_data_path(cache_key)
        if not os.path.exists(src):
            return False
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(src, local_path)
        await self.update_access(cache_key)
        return True

    async def put(
        self,
        cache_key: str,
        local_path: str,
        metadata: CacheMetadata,
    ) -> bool:
        dst = self._get_data_path(cache_key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(local_path, dst)

        meta_path = self._get_meta_path(cache_key)
        with open(meta_path, "w") as f:
            json.dump({
                "cache_key": metadata.cache_key,
                "source_file": metadata.source_file,
                "operation": metadata.operation,
                "params": metadata.params,
                "file_size": metadata.file_size,
                "crs": metadata.crs,
                "resolution": metadata.resolution,
                "created_at": metadata.created_at,
                "accessed_at": metadata.accessed_at,
                "access_count": metadata.access_count,
                "ttl_seconds": metadata.ttl_seconds,
                "backend": metadata.backend,
            }, f, default=str)

        return True

    async def delete(self, cache_key: str) -> bool:
        data_path = self._get_data_path(cache_key)
        meta_path = self._get_meta_path(cache_key)
        deleted = False
        if os.path.exists(data_path):
            os.remove(data_path)
            deleted = True
        if os.path.exists(meta_path):
            os.remove(meta_path)
            deleted = True
        return deleted

    async def get_metadata(self, cache_key: str) -> Optional[CacheMetadata]:
        meta_path = self._get_meta_path(cache_key)
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
            return CacheMetadata(**data)
        except Exception:
            return None

    async def update_access(self, cache_key: str) -> None:
        meta = await self.get_metadata(cache_key)
        if meta:
            meta.accessed_at = time.time()
            meta.access_count += 1
            meta_path = self._get_meta_path(cache_key)
            with open(meta_path, "w") as f:
                json.dump({
                    "cache_key": meta.cache_key,
                    "source_file": meta.source_file,
                    "operation": meta.operation,
                    "params": meta.params,
                    "file_size": meta.file_size,
                    "crs": meta.crs,
                    "resolution": meta.resolution,
                    "created_at": meta.created_at,
                    "accessed_at": meta.accessed_at,
                    "access_count": meta.access_count,
                    "ttl_seconds": meta.ttl_seconds,
                    "backend": meta.backend,
                }, f, default=str)


class S3Backend:
    """S3 对象存储缓存后端"""

    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._metadata_store: dict[str, CacheMetadata] = {}

    def _get_s3_key(self, cache_key: str) -> str:
        subdir = cache_key[:2] if len(cache_key) >= 2 else "xx"
        return f"cache/{subdir}/{cache_key}.tif"

    def _get_meta_key(self, cache_key: str) -> str:
        return f"cache/metadata/{cache_key}.json"

    async def exists(self, cache_key: str) -> bool:
        if cache_key in self._metadata_store:
            return True
        return cache_key in self._metadata_store

    async def get(self, cache_key: str, local_path: str) -> bool:
        if cache_key not in self._metadata_store:
            return False

        meta = self._metadata_store[cache_key]
        if meta and os.path.exists(local_path):
            await self.update_access(cache_key)
            return True

        return False

    async def put(
        self,
        cache_key: str,
        local_path: str,
        metadata: CacheMetadata,
    ) -> bool:
        self._metadata_store[cache_key] = metadata
        logger.info(f"Cached to S3 (simulated): {cache_key}")
        return True

    async def delete(self, cache_key: str) -> bool:
        if cache_key in self._metadata_store:
            del self._metadata_store[cache_key]
            return True
        return False

    async def get_metadata(self, cache_key: str) -> Optional[CacheMetadata]:
        return self._metadata_store.get(cache_key)

    async def update_access(self, cache_key: str) -> None:
        if cache_key in self._metadata_store:
            meta = self._metadata_store[cache_key]
            meta.accessed_at = time.time()
            meta.access_count += 1


class HybridBackend:
    """混合缓存后端（本地 L1 + S3 L2）"""

    def __init__(self, local: LocalFileBackend, s3: S3Backend, local_cache_gb: float = 50.0):
        self.local = local
        self.s3 = s3
        self.local_cache_gb = local_cache_gb

    async def exists(self, cache_key: str) -> bool:
        if await self.local.exists(cache_key):
            return True
        return await self.s3.exists(cache_key)

    async def get(self, cache_key: str, local_path: str) -> bool:
        if await self.local.exists(cache_key):
            return await self.local.get(cache_key, local_path)

        if await self.s3.exists(cache_key):
            meta = await self.s3.get_metadata(cache_key)
            if meta:
                await self.local.put(cache_key, local_path, meta)
                return True

        return False

    async def put(
        self,
        cache_key: str,
        local_path: str,
        metadata: CacheMetadata,
    ) -> bool:
        await self.local.put(cache_key, local_path, metadata)
        await self.s3.put(cache_key, local_path, metadata)
        return True

    async def delete(self, cache_key: str) -> bool:
        local_ok = await self.local.delete(cache_key)
        s3_ok = await self.s3.delete(cache_key)
        return local_ok or s3_ok

    async def get_metadata(self, cache_key: str) -> Optional[CacheMetadata]:
        meta = await self.local.get_metadata(cache_key)
        if meta:
            return meta
        return await self.s3.get_metadata(cache_key)

    async def update_access(self, cache_key: str) -> None:
        await self.local.update_access(cache_key)


class CacheManager:
    """缓存管理器 - 可配置后端"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.backend = self._create_backend(config)
        self.task_cache_root = os.path.join(config.local_root, "tasks")
        os.makedirs(self.task_cache_root, exist_ok=True)

    def _create_backend(self, config: CacheConfig):
        if config.backend_type == CacheBackendType.LOCAL:
            return LocalFileBackend(config.local_root)

        if config.backend_type == CacheBackendType.S3:
            bucket = config.s3_bucket or "oea-cache"
            return S3Backend(
                bucket=bucket,
                endpoint_url=config.s3_endpoint,
                access_key=config.s3_access_key,
                secret_key=config.s3_secret_key,
                region=config.s3_region,
            )

        if config.backend_type == CacheBackendType.HYBRID:
            local = LocalFileBackend(config.local_root)
            bucket = config.s3_bucket or "oea-cache"
            s3 = S3Backend(
                bucket=bucket,
                endpoint_url=config.s3_endpoint,
                access_key=config.s3_access_key,
                secret_key=config.s3_secret_key,
                region=config.s3_region,
            )
            return HybridBackend(local, s3, config.hybrid_local_gb)

        raise ValueError(f"Unknown backend type: {config.backend_type}")

    def get_cache_key(
        self,
        source_file: str,
        operation: str,
        params: dict[str, Any],
    ) -> str:
        normalized = json.dumps({
            "source": source_file,
            "operation": operation,
            "params": dict(sorted(params.items())),
        }, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()

    def get_task_cache_path(self, task_id: str, cache_key: str) -> str:
        task_dir = os.path.join(self.task_cache_root, task_id)
        os.makedirs(task_dir, exist_ok=True)
        return os.path.join(task_dir, f"{cache_key}.tif")

    async def check_cache(
        self,
        cache_key: str,
        local_path: str,
    ) -> bool:
        if await self.backend.exists(cache_key):
            logger.info(f"Cache hit: {cache_key}")
            return await self.backend.get(cache_key, local_path)
        logger.info(f"Cache miss: {cache_key}")
        return False

    async def save_to_cache(
        self,
        source_path: str,
        cache_key: str,
        metadata: CacheMetadata,
    ) -> bool:
        if not os.path.exists(source_path):
            return False

        success = await self.backend.put(cache_key, source_path, metadata)
        if success:
            logger.info(f"Cached: {cache_key}")
        return success

    async def preheat(
        self,
        cache_keys: list[str],
        concurrency: int = 5,
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}

        for key in cache_keys:
            temp_path = f"/tmp/preheat_{key}.tif"
            success = await self.check_cache(key, temp_path)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            results[key] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Preheat completed: {success_count}/{len(cache_keys)}")
        return results

    async def get_benchmark_images(
        self,
        sensors: list[str],
        regions: list[str],
        years: list[int],
    ) -> list[str]:
        keys = []
        for sensor in sensors:
            for region in regions:
                for year in years:
                    key = self.get_cache_key(
                        source_file=f"benchmark/{sensor}/{region}/{year}",
                        operation="preprocess",
                        params={"region": region, "year": year},
                    )
                    keys.append(key)
        return keys

    async def cleanup_expired(self) -> int:
        removed = 0
        now = time.time()

        if not os.path.exists(self.config.local_root):
            return 0

        for root, dirs, files in os.walk(self.config.local_root):
            for f in files:
                if f.endswith(".tif"):
                    fpath = os.path.join(root, f)
                    try:
                        stat = os.stat(fpath)
                        if now - stat.st_mtime > self.config.ttl_seconds:
                            os.remove(fpath)
                            removed += 1
                    except Exception:
                        pass

        logger.info(f"Cleanup: removed {removed} expired files")
        return removed

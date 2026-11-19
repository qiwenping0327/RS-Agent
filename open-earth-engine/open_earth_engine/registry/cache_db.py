from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = __import__("logging").getLogger("oea.cache_db")


@dataclass
class CacheEntry:
    cache_key: str
    source_file: str
    operation: str
    params: dict[str, Any]
    file_size: int = 0
    crs: Optional[str] = None
    resolution_x: Optional[float] = None
    resolution_y: Optional[float] = None
    access_count: int = 0
    created_at: datetime = None
    accessed_at: datetime = None
    expires_at: datetime = None
    backend: str = "local"


class CacheDatabase:
    """缓存元数据数据库"""

    def __init__(self, db_path: str = "./cache_metadata.json"):
        self.db_path = db_path
        self._entries: dict[str, CacheEntry] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                for key, entry_data in data.items():
                    entry = CacheEntry(
                        cache_key=entry_data.get("cache_key", key),
                        source_file=entry_data.get("source_file", ""),
                        operation=entry_data.get("operation", ""),
                        params=entry_data.get("params", {}),
                        file_size=entry_data.get("file_size", 0),
                        crs=entry_data.get("crs"),
                        resolution_x=entry_data.get("resolution_x"),
                        resolution_y=entry_data.get("resolution_y"),
                        access_count=entry_data.get("access_count", 0),
                        backend=entry_data.get("backend", "local"),
                    )
                    self._entries[key] = entry
            except Exception as e:
                logger.warning(f"Failed to load cache DB: {e}")

    def _save(self):
        try:
            data = {}
            for key, entry in self._entries.items():
                data[key] = {
                    "cache_key": entry.cache_key,
                    "source_file": entry.source_file,
                    "operation": entry.operation,
                    "params": entry.params,
                    "file_size": entry.file_size,
                    "crs": entry.crs,
                    "resolution_x": entry.resolution_x,
                    "resolution_y": entry.resolution_y,
                    "access_count": entry.access_count,
                    "backend": entry.backend,
                }
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save cache DB: {e}")

    def record_cache(
        self,
        cache_key: str,
        source_file: str,
        operation: str,
        params: dict,
        file_size: int,
        crs: str = None,
        resolution: tuple[float, float] = None,
        ttl_days: int = 7,
        backend: str = "local",
    ) -> CacheEntry:
        now = datetime.now()
        from datetime import timedelta

        if cache_key in self._entries:
            entry = self._entries[cache_key]
            entry.accessed_at = now
            entry.access_count += 1
        else:
            entry = CacheEntry(
                cache_key=cache_key,
                source_file=source_file,
                operation=operation,
                params=params,
                file_size=file_size,
                crs=crs,
                resolution_x=resolution[0] if resolution else None,
                resolution_y=resolution[1] if resolution else None,
                access_count=1,
                created_at=now,
                accessed_at=now,
                expires_at=now + timedelta(days=ttl_days),
                backend=backend,
            )
            self._entries[cache_key] = entry

        self._save()
        return entry

    def query_by_operation(
        self,
        operation: str,
        limit: int = 100,
    ) -> list[CacheEntry]:
        results = []
        for entry in self._entries.values():
            if entry.operation == operation:
                results.append(entry)

        results.sort(key=lambda e: e.accessed_at if e.accessed_at else datetime.min, reverse=True)
        return results[:limit]

    def cleanup_expired(self) -> int:
        now = datetime.now()
        expired = []

        for key, entry in self._entries.items():
            if entry.expires_at and entry.expires_at < now:
                expired.append(key)

        for key in expired:
            del self._entries[key]

        if expired:
            self._save()

        return len(expired)

    def get_hot_cache_keys(
        self,
        min_access_count: int = 0,
        limit: int = 100,
    ) -> list[str]:
        hot = [
            entry.cache_key
            for entry in self._entries.values()
            if entry.access_count >= min_access_count
        ]
        hot.sort(key=lambda k: self._entries[k].access_count if k in self._entries else 0, reverse=True)
        return hot[:limit]

    def get_all_keys(self) -> list[str]:
        return list(self._entries.keys())

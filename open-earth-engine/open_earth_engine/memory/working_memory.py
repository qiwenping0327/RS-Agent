from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("oea.memory")


@dataclass
class MemoryEntry:
    entry_id: str
    entry_type: str
    content: dict[str, Any]
    created_at: float
    importance: int = 0
    tags: list[str] = field(default_factory=list)
    step_reference: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "content": self.content,
            "created_at": self.created_at,
            "importance": self.importance,
            "tags": self.tags,
            "step_reference": self.step_reference,
        }


@dataclass
class MemoryConfig:
    max_entries: int = 1000
    max_context_length: int = 8000
    enable_pruning: bool = True
    persistence_enabled: bool = False
    persistence_path: Optional[str] = None


class WorkingMemory:
    """
    工作内存 - 任务执行上下文管理

    职责:
    1. 存储任务执行过程中的上下文信息
    2. 管理工具调用历史和结果
    3. 记录中间数据和错误信息
    4. 支持上下文检索和重要性排序
    5. 自动修剪旧条目

    对应 OpenEarthAgent 中的 Working Memory 概念:
    - 空间接地的工作内存 (Spatially Grounded Working Memory)
    - 记录工具执行观察 (Tool Execution Observations)
    - 支持多步推理的上下文保持
    """

    ENTRY_TYPE_TASK = "task"
    ENTRY_TYPE_STEP = "step"
    ENTRY_TYPE_TOOL_RESULT = "tool_result"
    ENTRY_TYPE_ERROR = "error"
    ENTRY_TYPE_OBSERVATION = "observation"
    ENTRY_TYPE_USER_INPUT = "user_input"

    def __init__(
        self,
        task_id: Optional[str] = None,
        config: MemoryConfig = None,
    ):
        self.task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        self.config = config or MemoryConfig()
        self._entries: list[MemoryEntry] = []
        self._tags_index: dict[str, list[str]] = {}

    def add_task_info(
        self,
        task_description: str,
        metadata: dict[str, Any] = None,
    ) -> MemoryEntry:
        """
        添加任务信息
        """
        entry = MemoryEntry(
            entry_id=f"task_{uuid.uuid4().hex[:8]}",
            entry_type=self.ENTRY_TYPE_TASK,
            content={
                "description": task_description,
                "metadata": metadata or {},
                "started_at": time.time(),
            },
            created_at=time.time(),
            importance=10,
            tags=["task_info"],
        )
        self._add_entry(entry)
        logger.info(f"Added task info: {task_description[:50]}...")
        return entry

    def add_step_progress(
        self,
        step_id: str,
        step_number: int,
        status: str,
        details: dict[str, Any] = None,
    ) -> MemoryEntry:
        """
        添加步骤进度
        """
        entry = MemoryEntry(
            entry_id=f"step_{uuid.uuid4().hex[:8]}",
            entry_type=self.ENTRY_TYPE_STEP,
            content={
                "step_id": step_id,
                "step_number": step_number,
                "status": status,
                "details": details or {},
                "timestamp": time.time(),
            },
            created_at=time.time(),
            importance=5,
            tags=["step_progress", f"step_{step_id}"],
            step_reference=step_id,
        )
        self._add_entry(entry)
        return entry

    def add_tool_result(
        self,
        tool_id: str,
        result: dict[str, Any],
        step_id: Optional[str] = None,
        output_files: list[str] = None,
    ) -> MemoryEntry:
        """
        添加工具执行结果
        """
        entry = MemoryEntry(
            entry_id=f"tool_{uuid.uuid4().hex[:8]}",
            entry_type=self.ENTRY_TYPE_TOOL_RESULT,
            content={
                "tool_id": tool_id,
                "result": result,
                "output_files": output_files or [],
                "timestamp": time.time(),
            },
            created_at=time.time(),
            importance=8,
            tags=["tool_result", f"tool_{tool_id}"],
            step_reference=step_id,
        )
        self._add_entry(entry)
        logger.info(f"Added tool result: {tool_id}")
        return entry

    def add_error(
        self,
        error: str,
        error_code: Optional[str] = None,
        step_id: Optional[str] = None,
        context: dict[str, Any] = None,
    ) -> MemoryEntry:
        """
        添加错误信息
        """
        entry = MemoryEntry(
            entry_id=f"error_{uuid.uuid4().hex[:8]}",
            entry_type=self.ENTRY_TYPE_ERROR,
            content={
                "error": error,
                "error_code": error_code,
                "context": context or {},
                "timestamp": time.time(),
            },
            created_at=time.time(),
            importance=10,
            tags=["error"],
            step_reference=step_id,
        )
        self._add_entry(entry)
        logger.error(f"Added error: {error_code or 'UNKNOWN'} - {error[:100]}")
        return entry

    def add_observation(
        self,
        observation: str,
        source: str = "system",
        metadata: dict[str, Any] = None,
        importance: int = 3,
    ) -> MemoryEntry:
        """
        添加观察信息
        """
        entry = MemoryEntry(
            entry_id=f"obs_{uuid.uuid4().hex[:8]}",
            entry_type=self.ENTRY_TYPE_OBSERVATION,
            content={
                "observation": observation,
                "source": source,
                "metadata": metadata or {},
                "timestamp": time.time(),
            },
            created_at=time.time(),
            importance=importance,
            tags=["observation", f"source_{source}"],
        )
        self._add_entry(entry)
        return entry

    def add_user_input(
        self,
        input_text: str,
        metadata: dict[str, Any] = None,
    ) -> MemoryEntry:
        """
        添加用户输入
        """
        entry = MemoryEntry(
            entry_id=f"user_{uuid.uuid4().hex[:8]}",
            entry_type=self.ENTRY_TYPE_USER_INPUT,
            content={
                "input": input_text,
                "metadata": metadata or {},
                "timestamp": time.time(),
            },
            created_at=time.time(),
            importance=9,
            tags=["user_input"],
        )
        self._add_entry(entry)
        return entry

    def _add_entry(self, entry: MemoryEntry) -> None:
        """
        内部添加条目方法
        """
        self._entries.append(entry)

        for tag in entry.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = []
            self._tags_index[tag].append(entry.entry_id)

        if self.config.enable_pruning and len(self._entries) > self.config.max_entries:
            self._prune()

    def _prune(self) -> None:
        """
        修剪旧条目
        """
        sorted_entries = sorted(self._entries, key=lambda e: (e.importance, -e.created_at))
        keep_count = int(self.config.max_entries * 0.8)
        to_remove = sorted_entries[keep_count:]

        for entry in to_remove:
            self._entries.remove(entry)
            for tag in entry.tags:
                if tag in self._tags_index and entry.entry_id in self._tags_index[tag]:
                    self._tags_index[tag].remove(entry.entry_id)

        logger.info(f"Pruned {len(to_remove)} entries from working memory")

    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """
        获取最近的条目
        """
        return sorted(self._entries, key=lambda e: -e.created_at)[:limit]

    def get_by_type(self, entry_type: str) -> list[MemoryEntry]:
        """
        按类型获取条目
        """
        return [e for e in self._entries if e.entry_type == entry_type]

    def get_by_tag(self, tag: str) -> list[MemoryEntry]:
        """
        按标签获取条目
        """
        entry_ids = self._tags_index.get(tag, [])
        return [e for e in self._entries if e.entry_id in entry_ids]

    def get_by_step(self, step_id: str) -> list[MemoryEntry]:
        """
        按步骤获取相关条目
        """
        return [e for e in self._entries if e.step_reference == step_id]

    def search(
        self,
        query: str,
        entry_types: list[str] = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """
        搜索内存条目
        """
        query_lower = query.lower()
        results = []

        for entry in self._entries:
            if entry_types and entry.entry_type not in entry_types:
                continue

            entry_str = json.dumps(entry.content, ensure_ascii=False).lower()
            if query_lower in entry_str or any(query_lower in t.lower() for t in entry.tags):
                results.append(entry)

        return sorted(results, key=lambda e: (-e.importance, -e.created_at))[:limit]

    def build_context(
        self,
        max_tokens: int = 4000,
        include_types: list[str] = None,
    ) -> str:
        """
        构建上下文字符串（用于LLM输入）
        """
        entries = sorted(self._entries, key=lambda e: (-e.importance, -e.created_at))

        if include_types:
            entries = [e for e in entries if e.entry_type in include_types]

        context_parts = []
        total_length = 0

        for entry in entries:
            entry_str = self._format_entry_for_context(entry)
            if total_length + len(entry_str) > max_tokens:
                break
            context_parts.append(entry_str)
            total_length += len(entry_str)

        return "\n".join(context_parts)

    def _format_entry_for_context(self, entry: MemoryEntry) -> str:
        """
        格式化条目用于上下文
        """
        if entry.entry_type == self.ENTRY_TYPE_TASK:
            return f"[TASK] {entry.content.get('description', '')}"
        elif entry.entry_type == self.ENTRY_TYPE_STEP:
            return f"[STEP {entry.content.get('step_number')}] {entry.content.get('status', '')}"
        elif entry.entry_type == self.ENTRY_TYPE_TOOL_RESULT:
            return f"[TOOL {entry.content.get('tool_id')}] executed successfully"
        elif entry.entry_type == self.ENTRY_TYPE_ERROR:
            return f"[ERROR] {entry.content.get('error', '')}"
        elif entry.entry_type == self.ENTRY_TYPE_OBSERVATION:
            return f"[OBSERVATION] {entry.content.get('observation', '')}"
        else:
            return f"[{entry.entry_type.upper()}] {json.dumps(entry.content)}"

    def get_tool_history(self) -> list[dict]:
        """
        获取工具调用历史
        """
        tool_entries = self.get_by_type(self.ENTRY_TYPE_TOOL_RESULT)
        return [
            {
                "tool_id": e.content.get("tool_id"),
                "result": e.content.get("result"),
                "output_files": e.content.get("output_files", []),
                "timestamp": e.content.get("timestamp"),
            }
            for e in tool_entries
        ]

    def get_error_history(self) -> list[dict]:
        """
        获取错误历史
        """
        error_entries = self.get_by_type(self.ENTRY_TYPE_ERROR)
        return [
            {
                "error": e.content.get("error"),
                "error_code": e.content.get("error_code"),
                "step_id": e.step_reference,
                "timestamp": e.content.get("timestamp"),
            }
            for e in error_entries
        ]

    def get_summary(self) -> dict:
        """
        获取内存摘要
        """
        return {
            "task_id": self.task_id,
            "total_entries": len(self._entries),
            "entry_counts": {
                et: len(self.get_by_type(et))
                for et in set(e.entry_type for e in self._entries)
            },
            "error_count": len(self.get_by_type(self.ENTRY_TYPE_ERROR)),
            "tool_executions": len(self.get_by_type(self.ENTRY_TYPE_TOOL_RESULT)),
        }

    def clear(self) -> None:
        """
        清空内存
        """
        self._entries = []
        self._tags_index = {}
        logger.info("Working memory cleared")

    def to_dict(self) -> dict:
        """
        序列化为字典
        """
        return {
            "task_id": self.task_id,
            "entries": [e.to_dict() for e in self._entries],
            "summary": self.get_summary(),
        }

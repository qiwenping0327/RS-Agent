"""
故障容错层 - SQLite 断点存储

支持遥感任务的断点续跑：任务中断后可从上次进度恢复。
"""

import hashlib
import json
import sqlite3
import os
from datetime import datetime
from typing import Any


class BreakpointManager:
    """
    基于 SQLite 的断点存储管理器

    每个任务通过 (tool_name, params_hash) 唯一标识，
    存储中间状态以便断点续跑。

    数据库路径: {workspace}/.rs_breakpoints.db
    """

    def __init__(self, workspace: str = ""):
        if not workspace:
            workspace = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))
        self.workspace = workspace
        self._db_path = os.path.join(workspace, ".rs_breakpoints.db")
        self._conn: sqlite3.Connection | None = None

    def _ensure_conn(self) -> sqlite3.Connection:
        """延迟初始化数据库连接"""
        if self._conn is None:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path)
            self._init_table(self._conn)
        return self._conn

    @staticmethod
    def _init_table(conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS breakpoints (
                task_id TEXT PRIMARY KEY,
                tool_name TEXT NOT NULL,
                params_hash TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_breakpoints_tool
            ON breakpoints(tool_name, params_hash)
        """)
        conn.commit()

    @staticmethod
    def _make_params_hash(params: dict) -> str:
        """根据参数生成哈希值"""
        raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _make_task_id(tool_name: str, params: dict) -> str:
        """生成任务 ID"""
        params_hash = BreakpointManager._make_params_hash(params)
        return f"{tool_name}_{params_hash}"

    async def save(self, tool_name: str, params: dict, state: dict[str, Any]) -> None:
        """
        保存断点

        Args:
            tool_name: 工具名称
            params: 工具参数
            state: 中间状态数据
        """
        conn = self._ensure_conn()
        task_id = self._make_task_id(tool_name, params)
        params_hash = self._make_params_hash(params)
        state_json = json.dumps(state, ensure_ascii=False)
        now = datetime.utcnow().isoformat()

        conn.execute(
            """
            INSERT INTO breakpoints (task_id, tool_name, params_hash, state_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (task_id, tool_name, params_hash, state_json, now),
        )
        conn.commit()

    async def load(self, tool_name: str, params: dict) -> dict[str, Any] | None:
        """
        加载断点

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            断点状态数据，不存在返回 None
        """
        conn = self._ensure_conn()
        task_id = self._make_task_id(tool_name, params)
        cursor = conn.execute(
            "SELECT state_json FROM breakpoints WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

    async def clear(self, tool_name: str, params: dict) -> None:
        """
        清除断点

        Args:
            tool_name: 工具名称
            params: 工具参数
        """
        conn = self._ensure_conn()
        task_id = self._make_task_id(tool_name, params)
        conn.execute("DELETE FROM breakpoints WHERE task_id = ?", (task_id,))
        conn.commit()

    async def list_breakpoints(self, tool_name: str | None = None) -> list[dict]:
        """列出所有断点"""
        conn = self._ensure_conn()
        if tool_name:
            cursor = conn.execute(
                "SELECT task_id, tool_name, updated_at FROM breakpoints WHERE tool_name = ?",
                (tool_name,),
            )
        else:
            cursor = conn.execute(
                "SELECT task_id, tool_name, updated_at FROM breakpoints"
            )
        return [
            {"task_id": row[0], "tool_name": row[1], "updated_at": row[2]}
            for row in cursor.fetchall()
        ]

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

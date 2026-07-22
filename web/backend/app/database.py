from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schemas import DiscussionMode, RunStatus


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        with self.lock, self.conn:
            self.conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    manager_ids TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    last_summary TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                    question TEXT NOT NULL,
                    status TEXT NOT NULL,
                    final_report TEXT NOT NULL DEFAULT '',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    manager_id TEXT,
                    round_no INTEGER,
                    content TEXT NOT NULL,
                    citations TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runs_thread ON runs(thread_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, id);
                """
            )
        self.set_default("model", "deepseek-v4-flash")
        self.set_default("output_language", "zh-CN")
        self.set_default("summary_format", "structured")

    def set_default(self, key: str, value: str) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, utcnow()),
            )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                """INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (key, value, utcnow()),
            )

    def delete_setting(self, key: str) -> None:
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM settings WHERE key=?", (key,))

    def create_thread(
        self, mode: DiscussionMode, manager_ids: list[str], title: str | None = None
    ) -> dict[str, Any]:
        thread_id = str(uuid.uuid4())
        now = utcnow()
        title = title or "新的基金经理讨论"
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO threads VALUES (?, ?, ?, ?, 'active', '', ?, ?)",
                (thread_id, title, mode.value, json.dumps(manager_ids, ensure_ascii=False), now, now),
            )
        return self.get_thread(thread_id)

    def list_threads(self, search: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM threads"
        params: list[Any] = []
        if search:
            query += " WHERE title LIKE ? OR last_summary LIKE ?"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY updated_at DESC"
        with self.lock:
            rows = self.conn.execute(query, params).fetchall()
        return [self._thread_dict(row, include_detail=False) for row in rows]

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        with self.lock:
            row = self.conn.execute("SELECT * FROM threads WHERE id=?", (thread_id,)).fetchone()
            if not row:
                raise KeyError(thread_id)
            runs = self.conn.execute(
                "SELECT * FROM runs WHERE thread_id=? ORDER BY created_at", (thread_id,)
            ).fetchall()
            messages = self.conn.execute(
                "SELECT * FROM messages WHERE thread_id=? ORDER BY created_at", (thread_id,)
            ).fetchall()
        result = self._thread_dict(row, include_detail=True)
        result["runs"] = [dict(item) for item in runs]
        result["messages"] = [self._message_dict(item) for item in messages]
        return result

    def _thread_dict(self, row: sqlite3.Row, include_detail: bool) -> dict[str, Any]:
        result = dict(row)
        result["manager_ids"] = json.loads(result["manager_ids"])
        if not include_detail:
            result["runs"] = []
            result["messages"] = []
        return result

    @staticmethod
    def _message_dict(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["citations"] = json.loads(result.get("citations") or "[]")
        return result

    def delete_thread(self, thread_id: str) -> None:
        with self.lock, self.conn:
            cursor = self.conn.execute("DELETE FROM threads WHERE id=?", (thread_id,))
            if cursor.rowcount == 0:
                raise KeyError(thread_id)

    def create_run(self, thread_id: str, question: str) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        now = utcnow()
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO runs(id, thread_id, question, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, thread_id, question, RunStatus.PENDING.value, now),
            )
            self.conn.execute(
                "UPDATE threads SET updated_at=?, title=CASE WHEN title='新的基金经理讨论' THEN ? ELSE title END WHERE id=?",
                (now, question[:64], thread_id),
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self.lock:
            row = self.conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        return dict(row)

    def update_run(
        self,
        run_id: str,
        status: RunStatus,
        final_report: str = "",
        error: str | None = None,
    ) -> None:
        completed_at = utcnow() if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED} else None
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE runs SET status=?, final_report=?, error=?, completed_at=? WHERE id=?",
                (status.value, final_report, error, completed_at, run_id),
            )
            row = self.conn.execute("SELECT thread_id FROM runs WHERE id=?", (run_id,)).fetchone()
            if row:
                self.conn.execute(
                    "UPDATE threads SET updated_at=?, last_summary=CASE WHEN ? != '' THEN ? ELSE last_summary END WHERE id=?",
                    (utcnow(), final_report, final_report[:1000], row["thread_id"]),
                )

    def add_message(
        self,
        thread_id: str,
        run_id: str,
        role: str,
        content: str,
        manager_id: str | None = None,
        round_no: int | None = None,
        citations: list[dict[str, Any]] | None = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    message_id,
                    thread_id,
                    run_id,
                    role,
                    manager_id,
                    round_no,
                    content,
                    json.dumps(citations or [], ensure_ascii=False),
                    utcnow(),
                ),
            )
        return message_id

    def add_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> int:
        with self.lock, self.conn:
            cursor = self.conn.execute(
                "INSERT INTO events(run_id, event_type, data, created_at) VALUES (?, ?, ?, ?)",
                (run_id, event_type, json.dumps(data, ensure_ascii=False), utcnow()),
            )
        return int(cursor.lastrowid)

    def list_events(self, run_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id", (run_id, after_id)
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "data": json.loads(row["data"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def previous_context(self, thread_id: str, limit: int = 10) -> str:
        with self.lock:
            rows = self.conn.execute(
                "SELECT role, manager_id, content FROM messages WHERE thread_id=? ORDER BY created_at DESC LIMIT ?",
                (thread_id, limit),
            ).fetchall()
        lines = []
        for row in reversed(rows):
            speaker = row["manager_id"] or row["role"]
            lines.append(f"{speaker}: {row['content'][:1200]}")
        return "\n".join(lines)

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .config import AppConfig
from .registry import ManagerRegistry


SUPPORTED_SUFFIXES = {".md", ".txt", ".csv", ".json"}


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _search_tokens(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9_.+-]+", text.lower())
    chinese = "".join(re.findall(r"[\u3400-\u9fff]", text))
    words.extend(chinese[index : index + 2] for index in range(max(0, len(chinese) - 1)))
    if chinese:
        words.extend(chinese)
    return " ".join(dict.fromkeys(token for token in words if token.strip()))


def _as_text(path: Path) -> str:
    if path.suffix.lower() in {".md", ".txt"}:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return "\n".join(
            "；".join(f"{key}: {value}" for key, value in row.items() if value not in (None, ""))
            for row in rows
        )
    data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if isinstance(data, list):
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
    if isinstance(data, dict):
        return "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in data.items())
    return str(data)


def _markdown_sections(text: str) -> Iterable[tuple[str, str]]:
    heading = "正文"
    buffer: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            if "\n".join(buffer).strip():
                yield heading, "\n".join(buffer).strip()
            heading = match.group(2).strip()
            buffer = []
        else:
            buffer.append(line)
    if "\n".join(buffer).strip():
        yield heading, "\n".join(buffer).strip()


def _chunk_text(text: str, title: str, size: int = 800, overlap: int = 120) -> Iterable[tuple[str, str]]:
    sections = _markdown_sections(text) if re.search(r"^#{1,6}\s+", text, re.M) else [(title, text)]
    for section_title, body in sections:
        compact = re.sub(r"\n{3,}", "\n\n", body).strip()
        if not compact:
            continue
        start = 0
        while start < len(compact):
            end = min(len(compact), start + size)
            if end < len(compact):
                break_at = max(compact.rfind("\n", start, end), compact.rfind("。", start, end))
                if break_at > start + size // 2:
                    end = break_at + 1
            chunk = compact[start:end].strip()
            if chunk:
                yield section_title, chunk
            if end >= len(compact):
                break
            start = max(start + 1, end - overlap)


class CorpusIndex:
    """Incremental local BM25 + embedding index over the five manager knowledge bases."""

    def __init__(self, config: AppConfig, registry: ManagerRegistry):
        self.config = config
        self.registry = registry
        self.path = config.index_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._encoder: Any | None = None
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        with self.lock, self.conn:
            self.conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY, manager_id TEXT NOT NULL, sha256 TEXT NOT NULL,
                    document_type TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, file_path TEXT NOT NULL, manager_id TEXT NOT NULL,
                    document_type TEXT NOT NULL, title TEXT NOT NULL, date TEXT,
                    fund_code TEXT, report_period TEXT, content TEXT NOT NULL,
                    embedding BLOB, dimensions INTEGER, sha256 TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED, manager_id UNINDEXED, search_text,
                    tokenize='unicode61 remove_diacritics 2'
                );
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_chunks_manager ON chunks(manager_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_path);
                """
            )

    def _meta(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def _set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def status(self) -> dict[str, Any]:
        with self.lock:
            files = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            chunks = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            state = self._meta("state", "empty")
            return {
                "state": state,
                "files": files,
                "chunks": chunks,
                "embedding_model": self.config.embedding_model,
                "vector_enabled": self._meta("vector_enabled", "0") == "1",
                "last_built_at": self._meta("last_built_at"),
                "error": self._meta("error"),
            }

    def _files(self) -> Iterable[tuple[str, Path, str]]:
        for manager_id in self.registry.ids():
            for key, registry_key in (
                ("profile", "profile_file"),
                ("method", "method_file"),
                ("scorecard", "scorecard_file"),
            ):
                path = self.registry.resolve(manager_id, registry_key)
                if path.is_file():
                    yield manager_id, path, key
            for key, registry_key in (("corpus", "corpus_dir"), ("fund_data", "fund_data_dir")):
                folder = self.registry.resolve(manager_id, registry_key)
                if not folder.exists():
                    continue
                for path in folder.rglob("*"):
                    if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                        yield manager_id, path.resolve(), key

    def _encoder_instance(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(self.config.embedding_model)
        return self._encoder

    def rebuild(self) -> dict[str, Any]:
        with self.lock:
            with self.conn:
                self._set_meta("state", "building")
                self._set_meta("error", "")
            try:
                discovered: dict[str, tuple[str, Path, str, str]] = {}
                for manager_id, path, doc_type in self._files():
                    relative = path.relative_to(self.config.root_dir).as_posix()
                    discovered[relative] = (manager_id, path, doc_type, _sha256(path))

                known = {
                    row["path"]: row["sha256"]
                    for row in self.conn.execute("SELECT path, sha256 FROM files").fetchall()
                }
                changed = [value for key, value in discovered.items() if known.get(key) != value[3]]
                stale = set(known) - set(discovered)
                prepared: list[dict[str, Any]] = []
                for manager_id, path, doc_type, digest in changed:
                    text = _as_text(path)
                    relative = path.relative_to(self.config.root_dir).as_posix()
                    date_match = re.search(r"(20\d{2})[年_\-]?(0?[1-9]|1[0-2])?", path.name)
                    date = date_match.group(0) if date_match else None
                    fund_match = re.search(r"(?<!\d)(\d{6})(?!\d)", relative)
                    report_period = path.stem if any(mark in path.stem for mark in ("季报", "中报", "年报")) else None
                    for ordinal, (title, content) in enumerate(_chunk_text(text, path.stem)):
                        chunk_hash = hashlib.sha256(f"{relative}:{ordinal}:{content}".encode()).hexdigest()
                        prepared.append(
                            {
                                "id": chunk_hash[:32], "file_path": relative,
                                "manager_id": manager_id, "document_type": doc_type,
                                "title": title, "date": date,
                                "fund_code": fund_match.group(1) if fund_match else None,
                                "report_period": report_period, "content": content,
                                "sha256": chunk_hash,
                            }
                        )

                vector_enabled = True
                embeddings: list[np.ndarray | None] = [None] * len(prepared)
                if prepared:
                    try:
                        encoded = self._encoder_instance().encode(
                            [item["content"] for item in prepared],
                            batch_size=32,
                            normalize_embeddings=True,
                            show_progress_bar=False,
                        )
                        embeddings = [np.asarray(vector, dtype=np.float32) for vector in encoded]
                    except Exception:
                        vector_enabled = False

                with self.conn:
                    for file_path in stale | {item[1].relative_to(self.config.root_dir).as_posix() for item in changed}:
                        ids = [row[0] for row in self.conn.execute("SELECT id FROM chunks WHERE file_path=?", (file_path,))]
                        self.conn.executemany("DELETE FROM chunks_fts WHERE chunk_id=?", [(item,) for item in ids])
                        self.conn.execute("DELETE FROM chunks WHERE file_path=?", (file_path,))
                        self.conn.execute("DELETE FROM files WHERE path=?", (file_path,))
                    for manager_id, path, doc_type, digest in changed:
                        relative = path.relative_to(self.config.root_dir).as_posix()
                        self.conn.execute(
                            "INSERT INTO files VALUES (?, ?, ?, ?, ?)",
                            (relative, manager_id, digest, doc_type, _utcnow()),
                        )
                    for item, vector in zip(prepared, embeddings, strict=True):
                        blob = vector.tobytes() if vector is not None else None
                        dimensions = int(vector.shape[0]) if vector is not None else None
                        self.conn.execute(
                            """INSERT INTO chunks(id, file_path, manager_id, document_type, title, date,
                            fund_code, report_period, content, embedding, dimensions, sha256)
                            VALUES (:id, :file_path, :manager_id, :document_type, :title, :date,
                            :fund_code, :report_period, :content, :embedding, :dimensions, :sha256)""",
                            {**item, "embedding": blob, "dimensions": dimensions},
                        )
                        self.conn.execute(
                            "INSERT INTO chunks_fts(chunk_id, manager_id, search_text) VALUES (?, ?, ?)",
                            (item["id"], item["manager_id"], _search_tokens(item["content"])),
                        )
                    self._set_meta("vector_enabled", "1" if vector_enabled else "0")
                    self._set_meta("state", "ready" if vector_enabled else "degraded")
                    self._set_meta("last_built_at", _utcnow())
                    self._set_meta("error", "" if vector_enabled else "向量模型不可用，已降级为关键词检索")
            except Exception as exc:
                with self.conn:
                    self._set_meta("state", "failed")
                    self._set_meta("error", str(exc))
                raise
        return self.status()

    def search(self, manager_id: str, query: str, limit: int = 8) -> list[dict[str, Any]]:
        tokens = _search_tokens(query).split()
        bm25_ids: list[str] = []
        with self.lock:
            if tokens:
                fts_query = " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens[:24])
                try:
                    rows = self.conn.execute(
                        """SELECT chunk_id FROM chunks_fts WHERE manager_id=? AND chunks_fts MATCH ?
                        ORDER BY bm25(chunks_fts) LIMIT 24""",
                        (manager_id, fts_query),
                    ).fetchall()
                    bm25_ids = [row["chunk_id"] for row in rows]
                except sqlite3.OperationalError:
                    bm25_ids = []

            vector_ids: list[str] = []
            if self._meta("vector_enabled", "0") == "1":
                try:
                    query_vector = np.asarray(
                        self._encoder_instance().encode([query], normalize_embeddings=True)[0],
                        dtype=np.float32,
                    )
                    scores: list[tuple[str, float]] = []
                    for row in self.conn.execute(
                        "SELECT id, embedding, dimensions FROM chunks WHERE manager_id=? AND embedding IS NOT NULL",
                        (manager_id,),
                    ):
                        vector = np.frombuffer(row["embedding"], dtype=np.float32, count=row["dimensions"])
                        scores.append((row["id"], float(np.dot(query_vector, vector))))
                    vector_ids = [item[0] for item in sorted(scores, key=lambda item: item[1], reverse=True)[:24]]
                except Exception:
                    vector_ids = []

            ranks: dict[str, float] = {}
            for ranking in (bm25_ids, vector_ids):
                for rank, chunk_id in enumerate(ranking, start=1):
                    ranks[chunk_id] = ranks.get(chunk_id, 0.0) + 1.0 / (60 + rank)
            if not ranks:
                fallback = self.conn.execute(
                    "SELECT id FROM chunks WHERE manager_id=? ORDER BY rowid DESC LIMIT ?",
                    (manager_id, limit),
                ).fetchall()
                ranks = {row["id"]: 1.0 for row in fallback}
            ordered = sorted(ranks, key=ranks.get, reverse=True)[:limit]
            if not ordered:
                return []
            placeholders = ",".join("?" for _ in ordered)
            rows = self.conn.execute(
                f"SELECT * FROM chunks WHERE id IN ({placeholders})", ordered
            ).fetchall()
        by_id = {row["id"]: dict(row) for row in rows}
        results = []
        for chunk_id in ordered:
            item = by_id[chunk_id]
            item.pop("embedding", None)
            item["excerpt"] = item["content"][:260]
            item["score"] = ranks[chunk_id]
            results.append(item)
        return results

    def get_chunk(self, chunk_id: str) -> dict[str, Any]:
        with self.lock:
            row = self.conn.execute("SELECT * FROM chunks WHERE id=?", (chunk_id,)).fetchone()
        if not row:
            raise KeyError(chunk_id)
        result = dict(row)
        result.pop("embedding", None)
        return result

    def quote_is_exact(self, chunk_id: str | None, quote: str) -> bool:
        if not chunk_id or not quote.strip():
            return False
        try:
            content = self.get_chunk(chunk_id)["content"]
        except KeyError:
            return False
        return quote.strip() in content

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .config import HISTORY_DB_PATH
from .schemas import AnswerStatus, HistoryEntry, HistoryListItem, SourceNode

log = logging.getLogger("rag.history")
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS qa_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    model        TEXT NOT NULL,
    duration_ms  INTEGER NOT NULL,
    status       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qa_ts ON qa_history(timestamp DESC);
"""


def _connect() -> sqlite3.Connection:
    HISTORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(HISTORY_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()


def save_qa(
    question: str,
    answer: str,
    sources: list[SourceNode],
    model: str,
    duration_ms: int,
    status: AnswerStatus,
) -> int:
    ts = datetime.now(timezone.utc).isoformat()
    sources_json = json.dumps([s.model_dump() for s in sources], ensure_ascii=False)
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "INSERT INTO qa_history (timestamp, question, answer, sources_json,"
                " model, duration_ms, status) VALUES (?,?,?,?,?,?,?)",
                (ts, question, answer, sources_json, model, duration_ms, status),
            )
            conn.commit()
            return int(cur.lastrowid)
        except Exception as e:
            log.warning("save_qa failed: %s", e)
            return -1
        finally:
            conn.close()


def list_history(limit: int, offset: int, search: str | None) -> tuple[list[HistoryListItem], int]:
    with _lock:
        conn = _connect()
        try:
            where = ""
            params: list = []
            if search:
                where = "WHERE question LIKE ?"
                params.append(f"%{search}%")

            total = conn.execute(
                f"SELECT COUNT(*) FROM qa_history {where}", params
            ).fetchone()[0]

            rows = conn.execute(
                f"SELECT id, timestamp, question, status FROM qa_history {where}"
                f" ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

            items = [
                HistoryListItem(
                    id=r["id"],
                    timestamp=r["timestamp"],
                    question_preview=(r["question"][:120] + "…") if len(r["question"]) > 120 else r["question"],
                    status=r["status"],
                )
                for r in rows
            ]
            return items, int(total)
        finally:
            conn.close()


def get_qa(entry_id: int) -> HistoryEntry | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM qa_history WHERE id = ?", (entry_id,)
            ).fetchone()
            if row is None:
                return None
            sources_raw = json.loads(row["sources_json"])
            sources = [SourceNode(**s) for s in sources_raw]
            return HistoryEntry(
                id=row["id"],
                timestamp=row["timestamp"],
                question=row["question"],
                answer=row["answer"],
                sources=sources,
                model=row["model"],
                duration_ms=row["duration_ms"],
                status=row["status"],
            )
        finally:
            conn.close()


def delete_qa(entry_id: int) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM qa_history WHERE id = ?", (entry_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def clear_history() -> int:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM qa_history")
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

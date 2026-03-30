"""
SQLite-backed cache với TTL tự động cleanup.

TTL mặc định:
  price    → 900s   (15 phút)
  history  → 3600s  (1 giờ)
  financial→ 86400s (24 giờ)
  market   → 300s   (5 phút)
  news     → 600s   (10 phút)
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

# ─── TTL presets ─────────────────────────────────────────────────────────────

TTL: dict[str, int] = {
    "price": 900,
    "history": 3600,
    "financial": 86_400,
    "market": 300,
    "news": 600,
    "default": 600,
}

_DEFAULT_DB = Path(__file__).parent / "vn_stock.db"


class SQLiteCache:
    """Thread-safe SQLite key-value cache với TTL."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ─── Internal ────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key        TEXT PRIMARY KEY,
                    value      TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
            conn.commit()

    # ─── Public API ──────────────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """Trả về giá trị nếu chưa hết TTL, ngược lại trả về None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        if time.time() > row["expires_at"]:
            self.delete(key)
            return None
        return json.loads(row["value"])

    def set(self, key: str, value: Any, ttl_type: str = "default") -> None:
        """Lưu giá trị với TTL theo loại dữ liệu."""
        ttl_seconds = TTL.get(ttl_type, TTL["default"])
        now = time.time()
        expires_at = now + ttl_seconds
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, serialized, expires_at, now),
            )
            conn.commit()

    def delete(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()

    def cleanup(self) -> int:
        """Xóa các entry hết hạn. Trả về số entry đã xóa."""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM cache WHERE expires_at <= ?", (time.time(),)
            )
            conn.commit()
            return cur.rowcount

    def clear(self) -> None:
        """Xóa toàn bộ cache (dùng trong tests)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()

    def stats(self) -> dict:
        """Thống kê cache hiện tại."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            expired = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at <= ?", (time.time(),)
            ).fetchone()[0]
        return {"total": total, "expired": expired, "valid": total - expired}


# ─── Module-level singleton ──────────────────────────────────────────────────

_cache_instance: SQLiteCache | None = None


def get_cache(db_path: str | Path | None = None) -> SQLiteCache:
    """Trả về singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SQLiteCache(db_path)
    return _cache_instance

"""Tests cho SQLiteCache."""

from __future__ import annotations

import time

from cache.cache import SQLiteCache


class TestSQLiteCache:
    def test_set_and_get(self, tmp_cache_db: SQLiteCache) -> None:
        """Lưu và lấy giá trị cơ bản."""
        tmp_cache_db.set("test:key", {"value": 42}, ttl_type="default")
        result = tmp_cache_db.get("test:key")
        assert result == {"value": 42}

    def test_get_nonexistent(self, tmp_cache_db: SQLiteCache) -> None:
        """Trả về None khi key không tồn tại."""
        assert tmp_cache_db.get("nonexistent") is None

    def test_ttl_expiry(self, tmp_cache_db: SQLiteCache) -> None:
        """Key hết hạn phải trả về None."""
        # Set với TTL ngắn giả lập bằng cách ghi thẳng
        import sqlite3
        conn = sqlite3.connect(str(tmp_cache_db.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at, created_at) VALUES (?, ?, ?, ?)",
            ("expired:key", '{"x": 1}', time.time() - 1, time.time() - 100),
        )
        conn.commit()
        conn.close()

        result = tmp_cache_db.get("expired:key")
        assert result is None

    def test_overwrite_key(self, tmp_cache_db: SQLiteCache) -> None:
        """Ghi đè key cũ."""
        tmp_cache_db.set("k", "old")
        tmp_cache_db.set("k", "new")
        assert tmp_cache_db.get("k") == "new"

    def test_delete(self, tmp_cache_db: SQLiteCache) -> None:
        """Xóa key."""
        tmp_cache_db.set("del:key", 99)
        tmp_cache_db.delete("del:key")
        assert tmp_cache_db.get("del:key") is None

    def test_cleanup(self, tmp_cache_db: SQLiteCache) -> None:
        """cleanup() xóa các entry hết hạn."""
        import sqlite3
        conn = sqlite3.connect(str(tmp_cache_db.db_path))
        # Thêm 3 entry hết hạn + 1 còn hạn
        for i in range(3):
            conn.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)",
                (f"exp:{i}", '1', time.time() - 1, time.time() - 100),
            )
        conn.execute(
            "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)",
            ("valid:key", '"still_valid"', time.time() + 3600, time.time()),
        )
        conn.commit()
        conn.close()

        deleted = tmp_cache_db.cleanup()
        assert deleted == 3
        assert tmp_cache_db.get("valid:key") == "still_valid"

    def test_stats(self, tmp_cache_db: SQLiteCache) -> None:
        """stats() trả về đúng số liệu."""
        tmp_cache_db.set("a", 1, ttl_type="price")
        tmp_cache_db.set("b", 2, ttl_type="market")
        stats = tmp_cache_db.stats()
        assert stats["valid"] == 2
        assert stats["expired"] == 0

    def test_complex_value_serialization(self, tmp_cache_db: SQLiteCache) -> None:
        """Lưu/lấy dict phức tạp với tiếng Việt."""
        data = {
            "symbol": "VNM",
            "name": "Công ty Sữa Việt Nam",
            "price": 75_000,
            "items": [1, 2, 3],
            "nested": {"a": True, "b": None},
        }
        tmp_cache_db.set("complex", data)
        result = tmp_cache_db.get("complex")
        assert result["name"] == "Công ty Sữa Việt Nam"
        assert result["items"] == [1, 2, 3]
        assert result["nested"]["b"] is None

    def test_clear(self, tmp_cache_db: SQLiteCache) -> None:
        """clear() xóa tất cả."""
        tmp_cache_db.set("x", 1)
        tmp_cache_db.set("y", 2)
        tmp_cache_db.clear()
        assert tmp_cache_db.stats()["total"] == 0

    def test_ttl_types(self, tmp_cache_db: SQLiteCache) -> None:
        """Kiểm tra TTL mặc định của từng loại."""
        import sqlite3
        now = time.time()
        tmp_cache_db.set("p", 1, ttl_type="price")
        conn = sqlite3.connect(str(tmp_cache_db.db_path))
        row = conn.execute("SELECT expires_at FROM cache WHERE key='p'").fetchone()
        conn.close()
        assert row is not None
        remaining = row[0] - now
        assert 895 < remaining <= 905  # ~900s ± 5s

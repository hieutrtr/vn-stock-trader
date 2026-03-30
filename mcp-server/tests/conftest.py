"""
Shared pytest fixtures cho vn-stock-trader tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Thêm mcp-server vào sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_ohlcv_250() -> pd.DataFrame:
    """250 phiên OHLCV giả lập cho VNM."""
    import numpy as np

    np.random.seed(42)
    n = 250
    dates = pd.date_range("2025-01-01", periods=n, freq="B")

    # Tạo giá theo random walk
    close = 70000 + np.cumsum(np.random.randn(n) * 500)
    close = np.maximum(close, 50000)  # sàn 50k

    open_ = close + np.random.randn(n) * 200
    high = np.maximum(close, open_) + np.abs(np.random.randn(n) * 300)
    low = np.minimum(close, open_) - np.abs(np.random.randn(n) * 300)
    volume = np.random.randint(500_000, 3_000_000, n)

    df = pd.DataFrame({
        "open": open_.round(0),
        "high": high.round(0),
        "low": low.round(0),
        "close": close.round(0),
        "volume": volume,
    }, index=dates)
    df.index.name = "date"
    return df


@pytest.fixture
def sample_ohlcv_30() -> pd.DataFrame:
    """30 phiên ngắn — để test graceful degradation."""
    import numpy as np

    np.random.seed(123)
    n = 30
    dates = pd.date_range("2026-02-01", periods=n, freq="B")
    close = 28000 + np.cumsum(np.random.randn(n) * 400)
    close = np.maximum(close, 20000)
    volume = np.random.randint(1_000_000, 5_000_000, n)

    df = pd.DataFrame({
        "open": close + np.random.randn(n) * 100,
        "high": close + np.abs(np.random.randn(n) * 200),
        "low": close - np.abs(np.random.randn(n) * 200),
        "close": close.round(0),
        "volume": volume,
    }, index=dates)
    df.index.name = "date"
    return df


@pytest.fixture
def tmp_cache_db(tmp_path: Path):
    """SQLite cache trong thư mục temp."""
    from cache.cache import SQLiteCache
    db_path = tmp_path / "test_cache.db"
    return SQLiteCache(db_path=db_path)


@pytest.fixture
def tmp_portfolio_path(tmp_path: Path) -> Path:
    """Đường dẫn file portfolio tạm."""
    return tmp_path / "portfolio.json"

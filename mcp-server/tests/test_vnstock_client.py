"""
Tests cho vnstock_client.py.
Dùng mock — KHÔNG gọi API thật.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from cache.cache import SQLiteCache
from data_sources import vnstock_client


@pytest.fixture(autouse=True)
def reset_cache(tmp_path):
    """Mỗi test dùng cache riêng trong tmp_path để tránh side effect."""
    import cache.cache as cache_module
    db = SQLiteCache(tmp_path / "test.db")
    cache_module._cache_instance = db
    yield db
    cache_module._cache_instance = None


_PRICE_DF_DEFAULT = pd.DataFrame({
    "time": ["2026-03-30"],
    "open": [74000.0], "high": [75500.0],
    "low": [73500.0], "close": [75000.0], "volume": [1_250_000],
})

_dates_250 = pd.date_range("2025-01-01", periods=250, freq="B")
_HISTORY_DF_DEFAULT = pd.DataFrame({
    "time": _dates_250.strftime("%Y-%m-%d"),
    "open": [70000.0] * 250, "high": [71000.0] * 250,
    "low": [69000.0] * 250, "close": [70500.0] * 250,
    "volume": [1_000_000] * 250,
}, index=_dates_250)


def _make_mock_stock(quote_df: pd.DataFrame | None = None):
    """
    Helper tạo mock Vnstock object.
    quote_df: được trả về bởi stock.quote.history() (dùng cho cả price và history).
    """
    mock_stock = MagicMock()
    mock_quote = MagicMock()

    if quote_df is None:
        quote_df = _PRICE_DF_DEFAULT

    mock_quote.history.return_value = quote_df
    mock_stock.quote = mock_quote

    mock_finance = MagicMock()
    mock_stock.finance = mock_finance

    return mock_stock


class TestGetStockPrice:
    def test_returns_required_fields(self) -> None:
        """get_stock_price trả về đầy đủ fields."""
        mock_stock = _make_mock_stock(_PRICE_DF_DEFAULT)

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock.return_value = mock_stock
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            result = vnstock_client.get_stock_price("VNM")

        assert result.get("symbol") == "VNM"
        assert "price" in result
        assert "volume" in result
        assert "reference_price" in result
        assert "ceiling" in result
        assert "floor" in result
        assert "timestamp" in result

    def test_ceiling_floor_calculation(self) -> None:
        """Ceiling = ref * 1.07, floor = ref * 0.93 (HOSE bands)."""
        mock_stock = _make_mock_stock(
            pd.DataFrame({"time": ["2026-03-30"], "close": [100000.0], "open": [100000.0], "high": [100000.0], "low": [100000.0], "volume": [1000]})
        )

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock.return_value = mock_stock
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            result = vnstock_client.get_stock_price("TEST")

        assert result["ceiling"] == 107000
        assert result["floor"] == 93000

    def test_symbol_not_found_returns_error(self) -> None:
        """Symbol không tồn tại → trả về error dict."""
        mock_stock = _make_mock_stock(pd.DataFrame())

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock.return_value = mock_stock
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            result = vnstock_client.get_stock_price("XXXXXX")

        assert "error" in result

    def test_cache_hit_skips_api(self) -> None:
        """Lần 2 không tạo request mới — lấy từ cache."""
        cached_data = {
            "symbol": "VNM", "price": 75000, "change": 0, "pct_change": 0,
            "open": 74000, "high": 75000, "low": 74000, "volume": 1_000_000,
            "value": 0, "reference_price": 74000, "ceiling": 79180, "floor": 68820,
            "foreign_buy_vol": 0, "foreign_sell_vol": 0, "foreign_room_pct": None,
            "timestamp": "2026-03-30T10:00:00",
        }

        from cache.cache import get_cache
        get_cache().set("price:VNM", cached_data, ttl_type="price")

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            result = vnstock_client.get_stock_price("VNM")
            # Vnstock không được gọi
            mock_vs_cls.assert_not_called()

        assert result["price"] == 75000

    def test_exception_returns_error(self) -> None:
        """Exception trong API call → trả về {'error': ...}."""
        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_vs_cls.side_effect = RuntimeError("API down")
            result = vnstock_client.get_stock_price("VNM")

        assert "error" in result

    def test_symbol_normalized_to_uppercase(self) -> None:
        """Symbol lowercase được normalize thành uppercase."""
        mock_stock = _make_mock_stock(_PRICE_DF_DEFAULT)

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock.return_value = mock_stock
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            result = vnstock_client.get_stock_price("vnm")

        assert result.get("symbol") == "VNM"


class TestGetStockHistory:
    def test_returns_dataframe_with_required_columns(self) -> None:
        """get_stock_history trả về DataFrame với đúng columns."""
        mock_stock = _make_mock_stock(_HISTORY_DF_DEFAULT)

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock.return_value = mock_stock
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            df = vnstock_client.get_stock_history("VNM", "1y")

        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 200
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in df.columns

    def test_invalid_period_defaults_to_1y(self) -> None:
        """Period không hợp lệ fallback về 1y."""
        mock_stock = _make_mock_stock(_HISTORY_DF_DEFAULT)

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock.return_value = mock_stock
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            # "10y" không có trong _PERIOD_DAYS → dùng 1y
            df = vnstock_client.get_stock_history("VNM", "10y")

        assert isinstance(df, pd.DataFrame)

    def test_empty_response_returns_empty_df(self) -> None:
        """Khi API trả về rỗng → DataFrame rỗng."""
        mock_stock = _make_mock_stock(pd.DataFrame())

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock.return_value = mock_stock
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            df = vnstock_client.get_stock_history("INVALID", "1y")

        assert len(df) == 0


class TestGetMarketOverview:
    def test_returns_index_structure(self) -> None:
        """get_market_overview trả về VN-Index, HNX, UPCOM."""
        mock_overview_df = pd.DataFrame([
            {"indexId": "VNINDEX", "indexValue": 1782.5, "indexChange": -3.2, "indexChangePercent": -0.18,
             "advances": 245, "declines": 198, "noChanges": 57, "ceilings": 12, "floors": 8},
            {"indexId": "HNX", "indexValue": 220.0, "indexChange": 0.5, "indexChangePercent": 0.23},
            {"indexId": "UPCOM", "indexValue": 93.5, "indexChange": 0.1, "indexChangePercent": 0.11},
        ])

        with patch("data_sources.vnstock_client._import_vnstock") as mock_vs_cls:
            mock_instance = MagicMock()
            mock_instance.stock_screening.market_overview.return_value = mock_overview_df
            mock_vs_cls.return_value = MagicMock(return_value=mock_instance)

            result = vnstock_client.get_market_overview()

        assert "vn_index" in result
        assert "hnx_index" in result
        assert "upcom_index" in result
        assert result["vn_index"]["value"] == 1782.5
        assert result["advance"] == 245
        assert result["decline"] == 198

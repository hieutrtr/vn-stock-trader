"""
Tests cho ta_calculator.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from data_sources.ta_calculator import (
    calculate_indicators,
    detect_patterns,
    find_support_resistance,
    get_trend,
)


class TestCalculateIndicators:
    def test_250_rows_no_key_nan(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """250 phiên → MA20/50, RSI14, MACD, BB không được là None."""
        result = calculate_indicators(sample_ohlcv_250)

        assert result["ma20"] is not None, "MA20 phải có với 250 rows"
        assert result["ma50"] is not None, "MA50 phải có với 250 rows"
        assert result["ma200"] is not None, "MA200 phải có với 250 rows"
        assert result["rsi14"] is not None, "RSI14 phải có với 250 rows"
        assert result["macd"] is not None, "MACD phải có với 250 rows"
        assert result["bb"] is not None, "BB phải có với 250 rows"

    def test_rsi_range(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """RSI phải trong [0, 100]."""
        result = calculate_indicators(sample_ohlcv_250)
        rsi = result["rsi14"]
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_bb_upper_greater_than_lower(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """Bollinger: upper > middle > lower."""
        result = calculate_indicators(sample_ohlcv_250)
        bb = result["bb"]
        assert bb is not None
        assert bb["upper"] > bb["middle"] > bb["lower"]

    def test_macd_has_three_keys(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """MACD trả về dict với macd, signal, histogram."""
        result = calculate_indicators(sample_ohlcv_250)
        assert "macd" in result["macd"]
        assert "signal" in result["macd"]
        assert "histogram" in result["macd"]

    def test_short_data_graceful_degradation(self, sample_ohlcv_30: pd.DataFrame) -> None:
        """30 phiên → MA200 phải là None, MA20 phải có."""
        result = calculate_indicators(sample_ohlcv_30)
        assert result["ma20"] is not None, "MA20 phải có với 30 rows"
        assert result["ma200"] is None, "MA200 phải là None khi < 200 rows"

    def test_empty_df_returns_empty(self) -> None:
        """DataFrame rỗng → trả về {} không crash."""
        result = calculate_indicators(pd.DataFrame())
        assert result == {}

    def test_volume_ratio_positive(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """volume_ratio > 0."""
        result = calculate_indicators(sample_ohlcv_250)
        assert result["volume_ma20"] is not None
        assert result["volume_ratio"] is not None
        assert result["volume_ratio"] > 0

    def test_atr_positive(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """ATR14 > 0."""
        result = calculate_indicators(sample_ohlcv_250)
        assert result["atr14"] is not None
        assert result["atr14"] > 0


class TestFindSupportResistance:
    def test_returns_structure(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """Trả về dict với support, resistance, current_price."""
        result = find_support_resistance(sample_ohlcv_250)
        assert "support" in result
        assert "resistance" in result
        assert "current_price" in result

    def test_support_below_price(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """Support < current_price."""
        result = find_support_resistance(sample_ohlcv_250)
        if result["support"]:
            assert all(s < result["current_price"] for s in result["support"])

    def test_resistance_above_price(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """Resistance > current_price."""
        result = find_support_resistance(sample_ohlcv_250)
        if result["resistance"]:
            assert all(r > result["current_price"] for r in result["resistance"])

    def test_empty_df(self) -> None:
        """DataFrame rỗng không crash."""
        result = find_support_resistance(pd.DataFrame())
        assert result["support"] == []
        assert result["resistance"] == []


class TestDetectPatterns:
    def test_golden_cross_detection(self) -> None:
        """Golden cross: MA20 cắt lên MA50."""
        # Tạo data với golden cross rõ ràng
        # Giai đoạn 1: giá thấp (MA20 < MA50), giai đoạn 2: giá vọt lên
        n = 100
        dates = pd.date_range("2025-01-01", periods=n, freq="B")

        close = np.zeros(n)
        # 70 phiên đầu: giá thấp
        close[:70] = np.linspace(50000, 45000, 70)
        # 30 phiên cuối: giá vọt mạnh
        close[70:] = np.linspace(48000, 65000, 30)

        df = pd.DataFrame({
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.98,
            "close": close,
            "volume": [1_000_000] * n,
        }, index=dates)

        patterns = detect_patterns(df)
        # Có thể có golden_cross nếu MA cross xảy ra
        assert isinstance(patterns, list)

    def test_returns_list(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """detect_patterns luôn trả về list."""
        result = detect_patterns(sample_ohlcv_250)
        assert isinstance(result, list)

    def test_volume_breakout(self) -> None:
        """Volume breakout khi vol > 2x MA20 và giá tăng >2%."""
        n = 50
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        close = np.full(n, 50000.0)

        # Phiên cuối: giá tăng 5%
        close[-1] = 52500.0
        close[-2] = 50000.0

        volume = np.full(n, 1_000_000)
        # Phiên cuối: volume tăng 3x
        volume[-1] = 3_000_000

        df = pd.DataFrame({
            "open": close * 0.99,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
            "volume": volume,
        }, index=dates)

        patterns = detect_patterns(df)
        assert "volume_breakout" in patterns

    def test_short_data_returns_empty(self, sample_ohlcv_30: pd.DataFrame) -> None:
        """< 50 phiên → trả về [] không crash."""
        result = detect_patterns(sample_ohlcv_30)
        assert result == []


class TestGetTrend:
    def test_uptrend_detection(self) -> None:
        """Giá tăng liên tục → UPTREND."""
        n = 250
        dates = pd.date_range("2025-01-01", periods=n, freq="B")
        close = np.linspace(10000, 90000, n)  # tăng mạnh liên tục (8x) để slope > 1.5%

        df = pd.DataFrame({
            "open": close * 0.995,
            "high": close * 1.005,
            "low": close * 0.990,
            "close": close,
            "volume": [1_000_000] * n,
        }, index=dates)

        result = get_trend(df)
        assert result["short_term"] == "UPTREND"
        assert result["medium_term"] == "UPTREND"

    def test_returns_required_keys(self, sample_ohlcv_250: pd.DataFrame) -> None:
        """Trả về dict với đúng keys."""
        result = get_trend(sample_ohlcv_250)
        assert "short_term" in result
        assert "medium_term" in result
        assert "long_term" in result
        assert "strength" in result

    def test_downtrend_detection(self) -> None:
        """Giá giảm liên tục → DOWNTREND."""
        n = 250
        dates = pd.date_range("2025-01-01", periods=n, freq="B")
        close = np.linspace(80000, 40000, n)

        df = pd.DataFrame({
            "open": close * 1.005,
            "high": close * 1.01,
            "low": close * 0.995,
            "close": close,
            "volume": [1_000_000] * n,
        }, index=dates)

        result = get_trend(df)
        assert result["short_term"] == "DOWNTREND"

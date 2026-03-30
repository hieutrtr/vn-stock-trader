"""
ta_calculator.py — Technical Analysis helper dùng pandas-ta.

Tính toán các chỉ báo kỹ thuật từ OHLCV DataFrame.
Graceful handling: trả về None khi không đủ data.

Indicators: SMA20/50/200, EMA20, RSI14, MACD, Bollinger Bands, ATR14, Volume MA20.
Patterns: golden cross, death cross, oversold bounce, volume breakout.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
    _HAS_PANDAS_TA = True
except ImportError:
    _HAS_PANDAS_TA = False
    logging.warning("pandas-ta not installed. TA calculations will use fallback methods.")

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

MIN_PERIODS = {
    "ma20": 20, "ma50": 50, "ma200": 200,
    "ema20": 20, "rsi14": 14,
    "macd": 26, "bb": 20, "atr14": 14,
}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _safe_float(val: Any) -> float | None:
    """Chuyển sang float, trả về None nếu NaN/None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Validate và chuẩn hóa DataFrame OHLCV."""
    if df is None or len(df) == 0:
        raise ValueError("DataFrame rỗng")

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = ["close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu columns: {missing}")

    # Đảm bảo numeric
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=["close"])


# ─── SMA / EMA tính thủ công (fallback khi không có pandas-ta) ───────────────


def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def _ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False, min_periods=window).mean()


def _rsi_manual(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI tính thủ công nếu không có pandas-ta."""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ─── Public Functions ─────────────────────────────────────────────────────────


def calculate_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """
    Tính tất cả chỉ báo kỹ thuật cho DataFrame OHLCV.

    Args:
        df: DataFrame với columns [open, high, low, close, volume], DatetimeIndex.
            Tối thiểu cần 14 rows để tính RSI.

    Returns:
        {
            "ma20": 74500.0, "ma50": 72000.0, "ma200": 68000.0,
            "ema20": 74800.0,
            "rsi14": 58.3,
            "macd": {"macd": 500.0, "signal": 420.0, "histogram": 80.0},
            "bb": {"upper": 78000.0, "middle": 74500.0, "lower": 71000.0},
            "atr14": 1200.0,
            "volume_ma20": 1_100_000.0,
            "volume_ratio": 1.35,
        }
        None cho từng chỉ báo nếu không đủ data.
    """
    try:
        df = _validate_ohlcv(df)
    except ValueError as e:
        logger.warning("calculate_indicators: %s", e)
        return {}

    close = df["close"]
    n = len(df)

    result: dict[str, Any] = {
        "ma20": None, "ma50": None, "ma200": None, "ema20": None,
        "rsi14": None,
        "macd": None,
        "bb": None,
        "atr14": None,
        "volume_ma20": None,
        "volume_ratio": None,
    }

    # ── Moving Averages ────────────────────────────────────────────
    if n >= MIN_PERIODS["ma20"]:
        result["ma20"] = _safe_float(_sma(close, 20).iloc[-1])
    if n >= MIN_PERIODS["ma50"]:
        result["ma50"] = _safe_float(_sma(close, 50).iloc[-1])
    if n >= MIN_PERIODS["ma200"]:
        result["ma200"] = _safe_float(_sma(close, 200).iloc[-1])
    if n >= MIN_PERIODS["ema20"]:
        result["ema20"] = _safe_float(_ema(close, 20).iloc[-1])

    # ── RSI ──────────────────────────────────────────────────────
    if n >= MIN_PERIODS["rsi14"]:
        if _HAS_PANDAS_TA:
            rsi = ta.rsi(close, length=14)
        else:
            rsi = _rsi_manual(close, 14)
        if rsi is not None and len(rsi) > 0:
            result["rsi14"] = _safe_float(rsi.iloc[-1])

    # ── MACD ──────────────────────────────────────────────────────
    if n >= MIN_PERIODS["macd"]:
        if _HAS_PANDAS_TA:
            macd_df = ta.macd(close, fast=12, slow=26, signal=9)
            if macd_df is not None and len(macd_df) > 0:
                last = macd_df.iloc[-1]
                macd_cols = macd_df.columns.tolist()
                # pandas-ta names: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
                macd_val = _safe_float(last.get(macd_cols[0]) if macd_cols else None)
                hist_val = _safe_float(last.get(macd_cols[1]) if len(macd_cols) > 1 else None)
                sig_val = _safe_float(last.get(macd_cols[2]) if len(macd_cols) > 2 else None)
                result["macd"] = {"macd": macd_val, "signal": sig_val, "histogram": hist_val}
        else:
            ema12 = _ema(close, 12)
            ema26 = _ema(close, 26)
            macd_line = ema12 - ema26
            signal_line = _ema(macd_line, 9)
            histogram = macd_line - signal_line
            result["macd"] = {
                "macd": _safe_float(macd_line.iloc[-1]),
                "signal": _safe_float(signal_line.iloc[-1]),
                "histogram": _safe_float(histogram.iloc[-1]),
            }

    # ── Bollinger Bands ───────────────────────────────────────────
    if n >= MIN_PERIODS["bb"]:
        if _HAS_PANDAS_TA:
            bb = ta.bbands(close, length=20, std=2)
            if bb is not None and len(bb) > 0:
                last = bb.iloc[-1]
                cols = bb.columns.tolist()
                # pandas-ta: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
                lower = _safe_float(last.get(cols[0]) if cols else None)
                mid = _safe_float(last.get(cols[1]) if len(cols) > 1 else None)
                upper = _safe_float(last.get(cols[2]) if len(cols) > 2 else None)
                result["bb"] = {"upper": upper, "middle": mid, "lower": lower}
        else:
            ma20 = _sma(close, 20)
            std20 = close.rolling(window=20, min_periods=20).std()
            upper = ma20 + 2 * std20
            lower = ma20 - 2 * std20
            result["bb"] = {
                "upper": _safe_float(upper.iloc[-1]),
                "middle": _safe_float(ma20.iloc[-1]),
                "lower": _safe_float(lower.iloc[-1]),
            }

    # ── ATR ──────────────────────────────────────────────────────
    if n >= MIN_PERIODS["atr14"] and all(c in df.columns for c in ["high", "low", "close"]):
        if _HAS_PANDAS_TA:
            atr = ta.atr(df["high"], df["low"], df["close"], length=14)
            if atr is not None and len(atr) > 0:
                result["atr14"] = _safe_float(atr.iloc[-1])
        else:
            high = df["high"]
            low = df["low"]
            prev_close = close.shift(1)
            tr = pd.concat([
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ], axis=1).max(axis=1)
            atr = tr.rolling(window=14, min_periods=14).mean()
            result["atr14"] = _safe_float(atr.iloc[-1])

    # ── Volume ───────────────────────────────────────────────────
    if "volume" in df.columns and n >= 20:
        vol_ma20 = _sma(df["volume"], 20)
        result["volume_ma20"] = _safe_float(vol_ma20.iloc[-1])
        if result["volume_ma20"] and result["volume_ma20"] > 0:
            result["volume_ratio"] = _safe_float(df["volume"].iloc[-1] / result["volume_ma20"])

    return result


def find_support_resistance(df: pd.DataFrame, lookback: int = 120) -> dict[str, Any]:
    """
    Tìm vùng support/resistance từ N phiên gần nhất.
    Dùng local min/max + simple clustering.

    Returns:
        {
            "support": [72000, 70500],   # mức hỗ trợ (sắp xếp giảm dần)
            "resistance": [78000, 80000],  # mức kháng cự (sắp xếp tăng dần)
            "current_price": 74500,
        }
    """
    try:
        df = _validate_ohlcv(df)
    except ValueError:
        return {"support": [], "resistance": [], "current_price": None}

    close = df["close"].iloc[-lookback:]
    high = df["high"].iloc[-lookback:] if "high" in df.columns else close
    low = df["low"].iloc[-lookback:] if "low" in df.columns else close
    current_price = float(close.iloc[-1])

    # Tìm local extrema với window 5
    window = 5
    local_highs = []
    local_lows = []

    for i in range(window, len(close) - window):
        h_slice = high.iloc[i - window: i + window + 1]
        l_slice = low.iloc[i - window: i + window + 1]

        if high.iloc[i] == h_slice.max():
            local_highs.append(float(high.iloc[i]))
        if low.iloc[i] == l_slice.min():
            local_lows.append(float(low.iloc[i]))

    def cluster(levels: list[float], threshold_pct: float = 0.015) -> list[float]:
        """Gom các mức giá gần nhau thành 1 cluster."""
        if not levels:
            return []
        sorted_levels = sorted(set(levels))
        clusters: list[float] = [sorted_levels[0]]
        for lvl in sorted_levels[1:]:
            if abs(lvl - clusters[-1]) / clusters[-1] > threshold_pct:
                clusters.append(lvl)
            else:
                # Merge: lấy trung bình
                clusters[-1] = (clusters[-1] + lvl) / 2
        return clusters

    # Phân loại support/resistance dựa theo giá hiện tại
    all_highs = cluster(local_highs)
    all_lows = cluster(local_lows)

    resistance = sorted([r for r in all_highs if r > current_price * 1.005])[:3]
    support = sorted([s for s in all_lows if s < current_price * 0.995], reverse=True)[:3]

    return {
        "support": [round(s) for s in support],
        "resistance": [round(r) for r in resistance],
        "current_price": round(current_price),
    }


def detect_patterns(df: pd.DataFrame) -> list[str]:
    """
    Phát hiện các pattern kỹ thuật trong 5 phiên gần nhất.

    Patterns:
    - "golden_cross": MA20 cắt lên MA50 trong 3 phiên
    - "death_cross": MA20 cắt xuống MA50 trong 3 phiên
    - "oversold_bounce": RSI < 30 và giá tăng
    - "overbought_warning": RSI > 70
    - "volume_breakout": volume > 2x MA20 và giá tăng > 2%
    - "support_hold": giá bounce từ support

    Returns:
        List pattern strings được phát hiện.
    """
    patterns: list[str] = []
    try:
        df = _validate_ohlcv(df)
    except ValueError:
        return patterns

    if len(df) < 50:
        return patterns

    close = df["close"]
    n = len(df)

    # ── MA series ─────────────────────────────────────────────────
    ma20 = _sma(close, 20)
    ma50 = _sma(close, 50)

    # Golden / Death cross — kiểm tra 3 phiên gần nhất
    lookback = min(3, n - 51)
    if lookback > 0:
        for i in range(-lookback - 1, -1):
            prev_diff = ma20.iloc[i] - ma50.iloc[i]
            curr_diff = ma20.iloc[i + 1] - ma50.iloc[i + 1]
            if pd.notna(prev_diff) and pd.notna(curr_diff):
                if prev_diff < 0 < curr_diff:
                    patterns.append("golden_cross")
                    break
                if prev_diff > 0 > curr_diff:
                    patterns.append("death_cross")
                    break

    # ── RSI patterns ─────────────────────────────────────────────
    if n >= 14:
        if _HAS_PANDAS_TA:
            rsi = ta.rsi(close, length=14)
        else:
            rsi = _rsi_manual(close, 14)
        if rsi is not None and len(rsi) > 1:
            rsi_val = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-2]
            if pd.notna(rsi_val):
                if rsi_val > 70:
                    patterns.append("overbought_warning")
                if rsi_prev < 30 and rsi_val > 30 and close.iloc[-1] > close.iloc[-2]:
                    patterns.append("oversold_bounce")

    # ── Volume breakout ──────────────────────────────────────────
    if "volume" in df.columns and n >= 21:
        vol = df["volume"]
        vol_ma20 = _sma(vol, 20)
        last_vol = float(vol.iloc[-1])
        last_ma20 = float(vol_ma20.iloc[-1]) if pd.notna(vol_ma20.iloc[-1]) else 0
        price_change_pct = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2]) * 100

        if last_ma20 > 0 and last_vol > 2 * last_ma20 and price_change_pct > 2:
            patterns.append("volume_breakout")

    return patterns


def get_trend(df: pd.DataFrame) -> dict[str, str | None]:
    """
    Xác định xu hướng ngắn/trung/dài hạn.

    Returns:
        {
            "short_term": "UPTREND",    # dựa trên MA20 slope
            "medium_term": "SIDEWAYS",  # dựa trên MA50 slope
            "long_term": "UPTREND",     # dựa trên MA200 slope
            "strength": "STRONG",       # STRONG / MODERATE / WEAK
        }
    """
    result: dict[str, str | None] = {
        "short_term": None,
        "medium_term": None,
        "long_term": None,
        "strength": None,
    }

    try:
        df = _validate_ohlcv(df)
    except ValueError:
        return result

    close = df["close"]
    n = len(close)

    def slope_trend(ma_series: pd.Series, window: int = 5) -> str | None:
        """Xác định xu hướng dựa trên slope của MA trong window phiên."""
        if len(ma_series.dropna()) < window + 1:
            return None
        recent = ma_series.dropna().iloc[-window - 1:]
        slope = (float(recent.iloc[-1]) - float(recent.iloc[0])) / float(recent.iloc[0]) * 100
        if slope > 1.5:
            return "UPTREND"
        if slope < -1.5:
            return "DOWNTREND"
        return "SIDEWAYS"

    # Short term: MA20
    if n >= 20:
        result["short_term"] = slope_trend(_sma(close, 20))

    # Medium term: MA50
    if n >= 50:
        result["medium_term"] = slope_trend(_sma(close, 50), window=10)

    # Long term: MA200
    if n >= 200:
        result["long_term"] = slope_trend(_sma(close, 200), window=20)

    # Strength: dựa trên RSI và price vs MA
    if n >= 14:
        if _HAS_PANDAS_TA:
            rsi = ta.rsi(close, length=14)
        else:
            rsi = _rsi_manual(close, 14)
        rsi_val = _safe_float(rsi.iloc[-1]) if rsi is not None and len(rsi) > 0 else None

        if rsi_val is not None:
            if rsi_val > 60 or rsi_val < 40:
                result["strength"] = "STRONG"
            elif rsi_val > 55 or rsi_val < 45:
                result["strength"] = "MODERATE"
            else:
                result["strength"] = "WEAK"

    return result

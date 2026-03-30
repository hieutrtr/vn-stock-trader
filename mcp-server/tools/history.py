"""
tools/history.py — MCP tool lịch sử giá và chỉ báo kỹ thuật.

Tools:
  - get_stock_history : OHLCV + MA, RSI, MACD, BB, ATR, patterns, S/R levels
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_PERIOD_LABEL = {
    "1m": "1 tháng",
    "3m": "3 tháng",
    "6m": "6 tháng",
    "1y": "1 năm",
    "2y": "2 năm",
    "5y": "5 năm",
}


def register(mcp: FastMCP) -> None:
    """Đăng ký history tools vào FastMCP instance."""

    @mcp.tool()
    async def get_stock_history(
        symbol: str,
        period: str = "1y",
        include_indicators: bool = True,
    ) -> str:
        """
        Get historical OHLCV price data and pre-calculated technical indicators
        for a Vietnamese stock.

        Returns price history plus MA20/50/200, RSI14, MACD, Bollinger Bands,
        ATR14, support/resistance zones, detected chart patterns, and trend direction.

        Args:
            symbol: Stock ticker (e.g. "VNM", "HPG", "ACB")
            period: "1m", "3m", "6m", "1y" (default), "2y", "5y"
            include_indicators: Calculate and return TA indicators (default True)
        """
        from data_sources.ta_calculator import (
            calculate_indicators,
            detect_patterns,
            find_support_resistance,
            get_trend,
        )
        from data_sources.vnstock_client import get_stock_history as _get_history

        symbol = symbol.upper().strip()
        period = period.lower()
        if period not in _PERIOD_LABEL:
            return (
                f"❌ Period không hợp lệ: **{period}**. "
                f"Chọn một trong: {', '.join(_PERIOD_LABEL.keys())}"
            )

        df = _get_history(symbol, period)

        if df is None or len(df) == 0:
            return f"❌ Không có dữ liệu lịch sử cho **{symbol}** (period={period})"

        n = len(df)
        period_label = _PERIOD_LABEL[period]

        last = df.iloc[-1]
        first = df.iloc[0]
        price_now = float(last["close"])
        price_start = float(first["close"])
        period_change = price_now - price_start
        period_change_pct = (period_change / price_start * 100) if price_start > 0 else 0
        high_period = float(df["high"].max()) if "high" in df.columns else price_now
        low_period = float(df["low"].min()) if "low" in df.columns else price_now
        avg_volume = int(df["volume"].mean()) if "volume" in df.columns else 0

        lines = [
            f"## 📈 Lịch sử giá — {symbol} ({period_label}, {n} phiên)",
            "",
            "| Chỉ số | Giá trị |",
            "|--------|---------|",
            f"| Giá hiện tại | **{price_now:,.0f} VNĐ** |",
            f"| Giá đầu kỳ | {price_start:,.0f} VNĐ |",
            f"| Thay đổi kỳ | {period_change:+,.0f} VNĐ ({period_change_pct:+.2f}%) |",
            f"| Cao nhất kỳ | {high_period:,.0f} VNĐ |",
            f"| Thấp nhất kỳ | {low_period:,.0f} VNĐ |",
            f"| Volume TB | {avg_volume:,} CP |",
            "",
        ]

        if include_indicators:
            try:
                indicators = calculate_indicators(df)

                def _v(key: str, decimals: int = 0) -> str:
                    val = indicators.get(key)
                    if val is None:
                        return "N/A"
                    if decimals == 0:
                        return f"{val:,.0f}"
                    return f"{val:,.{decimals}f}"

                lines += [
                    "### 📊 Chỉ báo kỹ thuật",
                    "",
                    "**Moving Averages:**",
                    f"- MA20: **{_v('ma20')} VNĐ**",
                    f"- MA50: **{_v('ma50')} VNĐ**",
                    f"- MA200: **{_v('ma200')} VNĐ**",
                    f"- EMA20: {_v('ema20')} VNĐ",
                    "",
                    "**Momentum:**",
                ]

                rsi = indicators.get("rsi14")
                rsi_str = "N/A"
                if rsi is not None:
                    if rsi >= 70:
                        rsi_icon = "🔴 Overbought"
                    elif rsi <= 30:
                        rsi_icon = "🟢 Oversold"
                    else:
                        rsi_icon = "🟡 Neutral"
                    rsi_str = f"**{rsi:.1f}** ({rsi_icon})"
                lines.append(f"- RSI(14): {rsi_str}")
                lines.append("")

                # MACD
                macd = indicators.get("macd", {})
                if macd and any(v is not None for v in macd.values()):
                    macd_val = macd.get("macd")
                    sig_val = macd.get("signal")
                    hist_val = macd.get("histogram")
                    if macd_val is not None:
                        hist_icon = "🟢" if (hist_val or 0) >= 0 else "🔴"
                        lines += [
                            "**MACD:**",
                            f"- MACD: {macd_val:,.0f} | Signal: {sig_val:,.0f} | Hist: {hist_icon} {hist_val:,.0f}",
                            "",
                        ]

                # Bollinger Bands
                bb = indicators.get("bb", {})
                if bb and bb.get("upper") is not None:
                    bb_upper = bb["upper"]
                    bb_mid = bb["middle"]
                    bb_lower = bb["lower"]
                    bb_pct = None
                    if bb_upper and bb_lower and bb_upper != bb_lower:
                        bb_pct = (price_now - bb_lower) / (bb_upper - bb_lower) * 100
                    bb_pos = f" — vị trí {bb_pct:.1f}%" if bb_pct is not None else ""
                    lines += [
                        f"**Bollinger Bands{bb_pos}:**",
                        f"- Upper: {bb_upper:,.0f} | Middle: {bb_mid:,.0f} | Lower: {bb_lower:,.0f}",
                        "",
                    ]

                # ATR + Volume
                atr = indicators.get("atr14")
                vol_ma20 = indicators.get("volume_ma20")
                vol_ratio = indicators.get("volume_ratio")
                lines.append(
                    f"**Volatility:** ATR(14) = {f'{atr:,.0f}' if atr else 'N/A'} VNĐ"
                )
                vol_line = f"**Volume:** MA20 = {f'{vol_ma20:,.0f}' if vol_ma20 else 'N/A'} CP"
                if vol_ratio is not None:
                    vol_line += f" (ratio hôm nay: {vol_ratio:.2f}x)"
                lines.append(vol_line)
                lines.append("")

            except Exception as e:
                logger.warning("TA indicators failed for %s: %s", symbol, e)
                lines.append(f"⚠️ Không tính được chỉ báo TA: {e}")
                lines.append("")

            # Trend
            try:
                trend = get_trend(df)
                short = trend.get("short_term", "N/A")
                medium = trend.get("medium_term", "N/A")
                long_ = trend.get("long_term", "N/A")
                strength = trend.get("strength", "N/A")
                _ticon = {"UPTREND": "📈", "DOWNTREND": "📉", "SIDEWAYS": "➡️"}
                lines += [
                    "### 🧭 Xu hướng",
                    f"- Ngắn hạn (MA20): {_ticon.get(short, '❓')} **{short}**",
                    f"- Trung hạn (MA50): {_ticon.get(medium, '❓')} **{medium}**",
                    f"- Dài hạn (MA200): {_ticon.get(long_, '❓')} **{long_}**",
                    f"- Sức mạnh xu hướng: **{strength}**",
                    "",
                ]
            except Exception as e:
                logger.debug("Trend calculation failed: %s", e)

            # Patterns
            try:
                patterns = detect_patterns(df)
                if patterns:
                    _pat_labels = {
                        "golden_cross": "✨ Golden Cross (MA20 cắt lên MA50)",
                        "death_cross": "💀 Death Cross (MA20 cắt xuống MA50)",
                        "oversold_bounce": "🔄 Oversold Bounce (RSI<30 + giá tăng)",
                        "volume_breakout": "💥 Volume Breakout (KL >2x TB + giá +2%)",
                    }
                    lines.append("### 🎯 Tín hiệu phát hiện")
                    for p in patterns:
                        lines.append(f"- **{_pat_labels.get(p, p)}**")
                    lines.append("")
            except Exception as e:
                logger.debug("Pattern detection failed: %s", e)

            # Support/Resistance
            try:
                sr = find_support_resistance(df)
                supports = sr.get("supports", [])
                resistances = sr.get("resistances", [])
                if supports or resistances:
                    lines.append("### 🏗️ Vùng Hỗ trợ / Kháng cự")
                    if resistances:
                        r_str = " | ".join(f"{r:,.0f}" for r in resistances[:3])
                        lines.append(f"- **Kháng cự:** {r_str} VNĐ")
                    if supports:
                        s_str = " | ".join(f"{s:,.0f}" for s in supports[:3])
                        lines.append(f"- **Hỗ trợ:** {s_str} VNĐ")
                    lines.append("")
            except Exception as e:
                logger.debug("S/R calculation failed: %s", e)

        # 5 phiên gần nhất
        lines += [
            "### 📋 5 phiên gần nhất",
            "| Ngày | Mở | Cao | Thấp | Đóng | KL |",
            "|------|-----|-----|------|------|----|",
        ]
        for date_idx, row in df.tail(5).iterrows():
            date_str = str(date_idx)[:10]
            o = int(row["open"]) if "open" in row.index and row["open"] == row["open"] else 0
            h = int(row["high"]) if "high" in row.index and row["high"] == row["high"] else 0
            lo = int(row["low"]) if "low" in row.index and row["low"] == row["low"] else 0
            c = int(row["close"])
            v = int(row["volume"]) if "volume" in row.index else 0
            lines.append(f"| {date_str} | {o:,} | {h:,} | {lo:,} | **{c:,}** | {v:,} |")

        return "\n".join(lines)

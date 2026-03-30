"""
tools/screener.py — MCP tool lọc cổ phiếu theo tiêu chí.

Tools:
  - screen_stocks : Lọc theo PE, PB, ROE, RSI, volume, giá...
"""

from __future__ import annotations

import logging
import re

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ─── Criteria Parser ─────────────────────────────────────────────────────────

# Các tiêu chí hỗ trợ và field mapping
_CRITERIA_MAP = {
    # Định giá
    "pe": "pe",
    "p/e": "pe",
    "pb": "pb",
    "p/b": "pb",
    "ps": "ps",
    "p/s": "ps",
    # Sinh lời
    "roe": "roe",
    "roa": "roa",
    "eps": "eps",
    "margin": "net_margin",
    "net_margin": "net_margin",
    # Kỹ thuật
    "rsi": "rsi",
    "rsi14": "rsi",
    "volume": "volume",
    "vol": "volume",
    # Giá
    "price": "price",
    "gia": "price",
    # Market cap
    "marketcap": "market_cap",
    "market_cap": "market_cap",
    # Tăng trưởng
    "revenue_growth": "revenue_growth",
    "profit_growth": "profit_growth",
}

_OP_MAP = {
    "<=": "lte",
    ">=": "gte",
    "<": "lt",
    ">": "gt",
    "=": "eq",
    "==": "eq",
}

_SUPPORTED_CRITERIA = [
    "PE<15", "PE>5", "PB<2", "ROE>15", "RSI<30", "RSI>70",
    "volume>1000000", "price<50000", "EPS>1000",
]


def _parse_criteria(criteria_str: str) -> list[dict]:
    """
    Parse chuỗi tiêu chí thành list filter dict.

    VD: "PE<15, ROE>15, RSI<30" →
    [
        {"field": "pe", "op": "lt", "value": 15},
        {"field": "roe", "op": "gt", "value": 15},
        {"field": "rsi", "op": "lt", "value": 30},
    ]
    """
    filters = []
    # Split bởi dấu phẩy hoặc "và" / "and"
    parts = re.split(r"[,;]|\s+và\s+|\s+and\s+", criteria_str, flags=re.IGNORECASE)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Match: field op value (VD: PE<15, ROE>=20, RSI < 30)
        m = re.match(
            r"([a-z_/0-9]+)\s*([<>]=?|==?)\s*([\d.]+)",
            part.strip(),
            re.IGNORECASE,
        )
        if not m:
            logger.debug("Cannot parse criterion: %s", part)
            continue

        raw_field = m.group(1).lower()
        raw_op = m.group(2)
        raw_val = m.group(3)

        field = _CRITERIA_MAP.get(raw_field)
        if not field:
            logger.debug("Unknown field: %s", raw_field)
            continue

        op = _OP_MAP.get(raw_op)
        if not op:
            continue

        try:
            value = float(raw_val)
        except ValueError:
            continue

        filters.append({"field": field, "op": op, "value": value})

    return filters


def _apply_filter(stock_data: dict, f: dict) -> bool:
    """Áp dụng một filter lên dict dữ liệu cổ phiếu."""
    val = stock_data.get(f["field"])
    if val is None:
        return False

    try:
        val = float(val)
        threshold = f["value"]
        op = f["op"]

        if op == "lt":
            return val < threshold
        if op == "lte":
            return val <= threshold
        if op == "gt":
            return val > threshold
        if op == "gte":
            return val >= threshold
        if op == "eq":
            return abs(val - threshold) < 1e-9
    except (TypeError, ValueError):
        pass
    return False


def register(mcp: FastMCP) -> None:
    """Đăng ký screener tools vào FastMCP instance."""

    @mcp.tool()
    async def screen_stocks(criteria: str, exchange: str = "HOSE") -> str:
        """
        Screen Vietnamese stocks by financial and technical criteria.

        Supported criteria (combine with commas):
          Valuation: PE<15, PE>5, PB<2, PB>0.5
          Profitability: ROE>15, ROA>10, EPS>1000
          Technical: RSI<30 (oversold), RSI>70 (overbought), volume>1000000
          Price: price<50000, price>10000

        Examples:
          "PE<15, ROE>15"          → Cổ phiếu rẻ + sinh lời tốt (value stocks)
          "RSI<30"                  → Oversold, cơ hội mua
          "PE<15, ROE>20, PB<2"    → Value + chất lượng
          "volume>2000000, RSI>50"  → Cổ phiếu thanh khoản tốt, đang tăng

        Args:
            criteria: Filter criteria string (see examples above)
            exchange: "HOSE" (default), "HNX", "UPCOM", or "ALL"
        """
        from data_sources.ta_calculator import calculate_indicators
        from data_sources.vnstock_client import (
            get_financial_report as _get_financials,
        )
        from data_sources.vnstock_client import (
            get_stock_history as _get_history,
        )
        from data_sources.vnstock_client import (
            get_stock_price as _get_price,
        )

        # Parse criteria
        filters = _parse_criteria(criteria)
        if not filters:
            supported = "\n".join(f"  - `{c}`" for c in _SUPPORTED_CRITERIA)
            return (
                f"❌ Không thể parse tiêu chí: **{criteria}**\n\n"
                f"Ví dụ tiêu chí hỗ trợ:\n{supported}\n\n"
                f"Có thể kết hợp: `PE<15, ROE>15, RSI<30`"
            )

        lines = [
            "## 🔍 Stock Screener",
            f"**Tiêu chí:** `{criteria}`",
            f"**Sàn:** {exchange}",
            "",
        ]

        # Lấy danh sách cổ phiếu để screen
        # Dùng top movers + watchlist phổ biến làm universe
        # (Do giới hạn API, không screen toàn bộ thị trường)
        _DEFAULT_UNIVERSE = [
            "VNM", "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HPG",
            "FPT", "VHM", "VIC", "GAS", "SAB", "MSN", "PLX", "POW",
            "HDB", "LPB", "SHB", "SSI", "PNJ", "NKG", "HSG", "REE",
            "DCM", "DGC", "HAG", "KDH", "NLG", "PDR", "DXG",
            "MWG", "DGW", "PHL", "GVR", "BCM",
        ]

        # Filter theo exchange nếu cần (simplified mapping)
        if exchange == "HNX":
            universe = ["ACB", "MBB", "SHB", "NKG", "HSG", "PHL", "TNG", "HUT", "VCS"]
        elif exchange == "UPCOM":
            universe = ["ACV", "BSR", "VEA", "BVH", "MCH"]
        else:
            universe = _DEFAULT_UNIVERSE

        needs_technical = any(f["field"] in ("rsi", "volume") for f in filters)
        needs_price = any(f["field"] == "price" for f in filters)
        needs_financial = any(f["field"] in ("pe", "pb", "roe", "roa", "eps", "net_margin") for f in filters)

        results = []
        errors = []

        lines.append(f"🔄 Đang scan **{len(universe)}** mã...")
        lines.append("")

        for sym in universe:
            try:
                stock_data: dict = {"symbol": sym}

                # Lấy giá nếu cần
                if needs_price or needs_technical:
                    price_data = _get_price(sym)
                    if "error" not in price_data:
                        stock_data["price"] = price_data.get("price")
                        stock_data["volume"] = price_data.get("volume")

                # Lấy financials nếu cần
                if needs_financial:
                    fin_data = _get_financials(sym)
                    if "error" not in fin_data:
                        ratios = fin_data.get("ratios", {})
                        for k, v in ratios.items():
                            # Convert ROE/ROA từ decimal sang percent nếu cần
                            if k in ("roe", "roa", "net_margin") and v is not None and abs(v) < 2:
                                stock_data[k] = v * 100
                            else:
                                stock_data[k] = v

                # Tính RSI nếu cần
                if needs_technical and "rsi" not in stock_data:
                    try:
                        df = _get_history(sym, "3m")
                        if df is not None and len(df) >= 14:
                            ind = calculate_indicators(df)
                            stock_data["rsi"] = ind.get("rsi14")
                            if stock_data.get("volume") is None:
                                stock_data["volume"] = ind.get("volume_ma20")
                    except Exception:
                        pass

                # Áp dụng tất cả filters
                if all(_apply_filter(stock_data, f) for f in filters):
                    results.append(stock_data)

            except Exception as e:
                errors.append(f"{sym}: {e}")
                logger.debug("Screen %s failed: %s", sym, e)

        # Hiển thị kết quả
        if not results:
            lines += [
                f"**Kết quả:** Không có mã nào thỏa tiêu chí trong {len(universe)} mã đã scan.",
                "",
                "_Thử nới lỏng tiêu chí hoặc mở rộng sàn (exchange=ALL)_",
            ]
        else:
            lines += [
                f"**Kết quả:** {len(results)} mã thỏa tiêu chí",
                "",
                "| Mã | Giá | P/E | P/B | ROE | RSI | Volume |",
                "|----|-----|-----|-----|-----|-----|--------|",
            ]
            for s in sorted(results, key=lambda x: x.get("pe", 999) or 999):
                sym = s["symbol"]
                price = s.get("price")
                pe = s.get("pe")
                pb = s.get("pb")
                roe = s.get("roe")
                rsi = s.get("rsi")
                volume = s.get("volume")

                lines.append(
                    f"| **{sym}** | "
                    f"{f'{price:,.0f}' if price else 'N/A'} | "
                    f"{f'{pe:.1f}' if pe else 'N/A'} | "
                    f"{f'{pb:.1f}' if pb else 'N/A'} | "
                    f"{f'{roe:.1f}%' if roe else 'N/A'} | "
                    f"{f'{rsi:.1f}' if rsi else 'N/A'} | "
                    f"{f'{int(volume):,}' if volume else 'N/A'} |"
                )

        lines += [
            "",
            f"_Universe: {len(universe)} mã | Lỗi: {len(errors)} mã_",
            "_Dữ liệu delay ~15 phút. Kết quả chỉ từ universe mặc định, không phải toàn thị trường._",
        ]

        return "\n".join(lines)

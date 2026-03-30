"""
tools/market.py — MCP tools thị trường.

Tools:
  - get_stock_price      : Snapshot giá hiện tại của một mã
  - get_market_overview  : Tổng quan VN-Index, HNX, UPCOM, breadth
  - get_top_movers       : Top tăng/giảm/volume
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def _fmt_number(n: float | int | None, unit: str = "") -> str:
    """Format số với dấu phân cách ngàn."""
    if n is None:
        return "N/A"
    if isinstance(n, float):
        return f"{n:,.0f}{unit}"
    return f"{n:,}{unit}"


def _fmt_pct(n: float | None) -> str:
    """Format phần trăm với dấu +/-."""
    if n is None:
        return "N/A"
    sign = "+" if n > 0 else ""
    return f"{sign}{n:.2f}%"


def _fmt_change(change: float | None, pct: float | None) -> str:
    if change is None or pct is None:
        return "N/A"
    sign = "▲" if change >= 0 else "▼"
    return f"{sign} {abs(change):,.0f} ({_fmt_pct(pct)})"


def register(mcp: FastMCP) -> None:
    """Đăng ký market tools vào FastMCP instance."""

    @mcp.tool()
    async def get_stock_price(symbol: str) -> str:
        """
        Get current price and trading data for a Vietnamese stock.

        Returns price, change %, volume, reference price, ceiling/floor limits,
        and foreign ownership data. Data is delayed ~15 minutes.

        Args:
            symbol: Stock ticker (e.g. "VNM", "HPG", "ACB", "VCB", "FPT")
        """
        from data_sources.vnstock_client import get_stock_price as _get_price

        symbol = symbol.upper().strip()
        data = _get_price(symbol)

        if "error" in data:
            return f"❌ Không tìm thấy mã **{symbol}**: {data['error']}"

        price = data.get("price", 0)
        ref = data.get("reference_price", 0)
        change = data.get("change", 0)
        pct = data.get("pct_change", 0)

        # Chiều giá
        if change > 0:
            price_icon = "🟢"
            change_str = f"▲ +{change:,.0f} (+{pct:.2f}%)"
        elif change < 0:
            price_icon = "🔴"
            change_str = f"▼ {change:,.0f} ({pct:.2f}%)"
        else:
            price_icon = "🟡"
            change_str = "— 0 (0.00%)"

        # Biên độ còn lại đến trần/sàn
        ceiling = data.get("ceiling", 0)
        floor = data.get("floor", 0)
        room_to_ceiling = ((ceiling - price) / price * 100) if price > 0 else None
        room_to_floor = ((price - floor) / price * 100) if price > 0 else None

        lines = [
            f"## {price_icon} {symbol} — {price:,.0f} VNĐ",
            "",
            f"**Thay đổi:** {change_str}",
            f"**Tham chiếu:** {_fmt_number(ref)} | **Trần:** {_fmt_number(ceiling)} | **Sàn:** {_fmt_number(floor)}",
            f"**Còn đến trần:** {_fmt_pct(room_to_ceiling)} | **Còn đến sàn:** {_fmt_pct(room_to_floor)}",
            "",
            "| Chỉ số | Giá trị |",
            "|--------|---------|",
            f"| Mở cửa | {_fmt_number(data.get('open'))} VNĐ |",
            f"| Cao nhất | {_fmt_number(data.get('high'))} VNĐ |",
            f"| Thấp nhất | {_fmt_number(data.get('low'))} VNĐ |",
            f"| Khối lượng | {_fmt_number(data.get('volume'))} CP |",
            f"| Giá trị GD | {_fmt_number(data.get('value', 0) / 1e9, ' tỷ VNĐ') if data.get('value') else 'N/A'} |",
        ]

        # Foreign data nếu có
        fb = data.get("foreign_buy_vol")
        fs = data.get("foreign_sell_vol")
        fr = data.get("foreign_room_pct")
        if fb is not None or fs is not None:
            lines += [
                "",
                f"**Khối ngoại:** Mua {_fmt_number(fb)} CP | Bán {_fmt_number(fs)} CP",
            ]
            if fr is not None:
                lines.append(f"**Room ngoại còn lại:** {fr:.1f}%")

        lines += [
            "",
            f"_Cập nhật: {data.get('timestamp', 'N/A')} (delay ~15 phút)_",
        ]

        return "\n".join(lines)

    @mcp.tool()
    async def get_market_overview() -> str:
        """
        Get Vietnamese stock market overview: VN-Index, HNX-Index, UPCOM-Index,
        market breadth (advances/declines), total liquidity, and foreign trading flow.

        Use this tool to understand overall market sentiment before analyzing individual stocks.
        """
        from data_sources.vnstock_client import get_market_overview as _get_overview

        data = _get_overview()

        if "error" in data:
            return f"❌ Không lấy được dữ liệu thị trường: {data['error']}"

        def _idx_line(name: str, idx: dict) -> str:
            val = idx.get("value")
            chg = idx.get("change")
            pct = idx.get("pct")
            if val is None:
                return f"**{name}:** N/A"
            icon = "🟢" if (chg or 0) >= 0 else "🔴"
            return f"**{name}:** {icon} {val:,.2f} {_fmt_change(chg, pct)}"

        # Breadth
        adv = data.get("advance")
        dec = data.get("decline")
        unc = data.get("unchanged")
        cei = data.get("ceiling")
        flo = data.get("floor")
        breadth_str = ""
        if adv is not None:
            breadth_str = f"Tăng **{adv}** | Giảm **{dec}** | Không đổi **{unc}**"
            if cei is not None:
                breadth_str += f" | Trần **{cei}** | Sàn **{flo}**"

        # Foreign
        fb = data.get("foreign_buy_bn")
        fs = data.get("foreign_sell_bn")
        fn = data.get("foreign_net_bn")
        foreign_str = ""
        if fb is not None:
            net_icon = "🟢" if (fn or 0) >= 0 else "🔴"
            foreign_str = (
                f"Mua: **{fb:.1f} tỷ** | Bán: **{fs:.1f} tỷ** | "
                f"Ròng: {net_icon} **{fn:+.1f} tỷ**"
            )

        tv = data.get("total_value_bn_vnd")
        vol = data.get("total_volume")

        lines = [
            "## 📊 Tổng quan thị trường",
            "",
            _idx_line("VN-Index", data.get("vn_index", {})),
            _idx_line("HNX-Index", data.get("hnx_index", {})),
            _idx_line("UPCOM-Index", data.get("upcom_index", {})),
            "",
            "### Thanh khoản",
            f"- Khối lượng: **{_fmt_number(vol)} CP**" if vol else "",
            f"- Giá trị: **{tv:,.0f} tỷ VNĐ**" if tv else "",
            "",
            "### Độ rộng thị trường",
            breadth_str if breadth_str else "N/A",
            "",
        ]
        if foreign_str:
            lines += [
                "### Khối ngoại",
                foreign_str,
                "",
            ]
        lines.append(f"_Cập nhật: {data.get('timestamp', 'N/A')} (delay ~15 phút)_")

        return "\n".join(line for line in lines)

    @mcp.tool()
    async def get_top_movers(exchange: str = "ALL", n: int = 10) -> str:
        """
        Get top gaining, losing, and most-traded stocks in the Vietnamese market.

        Args:
            exchange: "HOSE", "HNX", "UPCOM", or "ALL" (default "ALL")
            n: Number of stocks per list, max 20 (default 10)
        """
        from data_sources.vnstock_client import get_top_movers as _get_movers

        n = min(max(1, n), 20)
        data = _get_movers(n=n)

        if "error" in data:
            return f"❌ Không lấy được dữ liệu top movers: {data['error']}"

        def _table(stocks: list[dict], title: str, icon: str) -> list[str]:
            if not stocks:
                return [f"### {icon} {title}", "_Không có dữ liệu_", ""]
            rows = [f"### {icon} {title}", "| # | Mã | Giá (VNĐ) | % |", "|---|-----|-----------|---|"]
            for i, s in enumerate(stocks, 1):
                sym = s.get("symbol") or "N/A"
                price = _fmt_number(s.get("price"))
                pct = _fmt_pct(s.get("pct_change"))
                rows.append(f"| {i} | **{sym}** | {price} | {pct} |")
            rows.append("")
            return rows

        def _vol_table(stocks: list[dict]) -> list[str]:
            if not stocks:
                return ["### 🔊 Volume cao nhất", "_Không có dữ liệu_", ""]
            rows = ["### 🔊 Volume cao nhất", "| # | Mã | Giá (VNĐ) | KL (CP) |", "|---|-----|-----------|---------|"]
            for i, s in enumerate(stocks, 1):
                sym = s.get("symbol") or "N/A"
                price = _fmt_number(s.get("price"))
                vol = _fmt_number(s.get("volume"))
                rows.append(f"| {i} | **{sym}** | {price} | {vol} |")
            rows.append("")
            return rows

        lines = [f"## 🏆 Top Movers — {exchange}", ""]
        lines += _table(data.get("gainers", []), "Tăng mạnh nhất", "🟢")
        lines += _table(data.get("losers", []), "Giảm mạnh nhất", "🔴")
        lines += _vol_table(data.get("volume_leaders", []))
        lines.append("_Dữ liệu delay ~15 phút_")

        return "\n".join(lines)

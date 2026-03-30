"""
tools/portfolio.py — MCP tools quản lý danh mục đầu tư.

Tools:
  - get_portfolio    : Đọc danh mục + giá hiện tại + P&L
  - update_portfolio : Mua/bán/xóa vị thế
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def _pnl_icon(pnl: float) -> str:
    if pnl > 0:
        return "🟢"
    if pnl < 0:
        return "🔴"
    return "🟡"


def register(mcp: FastMCP) -> None:
    """Đăng ký portfolio tools vào FastMCP instance."""

    @mcp.tool()
    async def get_portfolio() -> str:
        """
        Read current investment portfolio from data/portfolio.json,
        fetch live prices, and calculate unrealized P&L for each position.

        Returns portfolio summary with NAV, total P&L, position weights,
        and T+2 receivables (Vietnamese T+2 settlement).
        """
        from data_sources.portfolio import PortfolioManager
        from data_sources.vnstock_client import get_stock_price as _get_price

        manager = PortfolioManager()
        portfolio = manager.load()

        if not portfolio.positions:
            cash_str = f"{portfolio.cash:,.0f} VNĐ" if portfolio.cash else "0 VNĐ"
            return (
                f"## 💼 Danh mục đầu tư\n\n"
                f"**Danh mục trống.** Không có vị thế nào.\n\n"
                f"- Tiền mặt: **{cash_str}**\n"
                f"- T+1 nhận: {portfolio.t1_receivable:,.0f} VNĐ\n"
                f"- T+2 nhận: {portfolio.t2_receivable:,.0f} VNĐ\n\n"
                f"_Dùng `update_portfolio` để thêm vị thế._"
            )

        # Lấy giá hiện tại cho tất cả positions
        prices: dict[str, float] = {}
        price_errors: list[str] = []
        for pos in portfolio.positions:
            price_data = _get_price(pos.symbol)
            if "error" not in price_data and price_data.get("price"):
                prices[pos.symbol] = float(price_data["price"])
            else:
                prices[pos.symbol] = pos.avg_cost  # fallback về giá vốn
                price_errors.append(pos.symbol)

        # Tính P&L
        pnl_data = manager.calculate_pnl(prices)

        nav = pnl_data["nav"]
        total_mv = pnl_data["total_market_value"]
        total_pnl = pnl_data["total_unrealized_pnl"]
        total_pnl_pct = pnl_data["total_unrealized_pnl_pct"]
        cash = pnl_data["cash"]
        t1 = pnl_data["t1_receivable"]
        t2 = pnl_data["t2_receivable"]
        cash_w = pnl_data["cash_weight_pct"]

        pnl_icon = _pnl_icon(total_pnl)

        lines = [
            "## 💼 Danh mục đầu tư",
            "",
            "### Tổng quan NAV",
            "| | Giá trị |",
            "|--|---------|",
            f"| **NAV** | **{nav:,.0f} VNĐ** |",
            f"| Giá trị cổ phiếu | {total_mv:,.0f} VNĐ |",
            f"| Tiền mặt | {cash:,.0f} VNĐ ({cash_w:.1f}%) |",
        ]
        if t1 > 0:
            lines.append(f"| T+1 nhận về | {t1:,.0f} VNĐ |")
        if t2 > 0:
            lines.append(f"| T+2 nhận về | {t2:,.0f} VNĐ |")
        lines += [
            f"| {pnl_icon} Lãi/Lỗ chưa thực hiện | **{total_pnl:+,.0f} VNĐ ({total_pnl_pct:+.2f}%)** |",
            "",
            "### Vị thế",
            "",
            "| Mã | SL | Giá vốn | Giá TT | GT TT | LL | LL% | Tỷ trọng |",
            "|----|----|---------|---------|---------|----|-----|---------|",
        ]

        for pos in pnl_data["positions"]:
            sym = pos["symbol"]
            qty = pos["qty"]
            cost = pos["avg_cost"]
            curr = pos["current_price"]
            mv = pos["market_value"]
            pnl = pos["unrealized_pnl"]
            pnl_pct = pos["unrealized_pnl_pct"]
            weight = pos["weight_pct"]
            icon = _pnl_icon(pnl)

            # Giá vốn note nếu đang dùng fallback
            curr_str = f"{curr:,.0f}" + (" ⚠️" if sym in price_errors else "")

            lines.append(
                f"| **{sym}** | {qty:,} | {cost:,.0f} | {curr_str} | "
                f"{mv:,.0f} | {icon}{pnl:+,.0f} | {pnl_pct:+.2f}% | {weight:.1f}% |"
            )

        lines += [""]

        if price_errors:
            lines += [
                f"⚠️ Không lấy được giá TT cho: {', '.join(price_errors)} — dùng giá vốn.",
                "",
            ]

        lines += [
            f"_Cập nhật: {portfolio.updated_at or 'N/A'} | Dữ liệu giá delay ~15 phút_",
        ]

        return "\n".join(lines)

    @mcp.tool()
    async def update_portfolio(
        action: str,
        symbol: str,
        qty: int,
        price: float,
        notes: str = "",
    ) -> str:
        """
        Update investment portfolio: buy, sell, or remove a position.

        Changes are saved to data/portfolio.json immediately.
        Vietnamese T+2 settlement: selling today means cash arrives in 2 trading days.

        Args:
            action: "buy" — add/increase position | "sell" — reduce/close position | "remove" — delete entirely
            symbol: Stock ticker (e.g. "VNM", "HPG")
            qty: Number of shares (positive integer)
            price: Price per share in VNĐ
            notes: Optional note (e.g. "Mua tại vùng hỗ trợ MA200")
        """
        from data_sources.portfolio import PortfolioManager

        action = action.lower().strip()
        symbol = symbol.upper().strip()

        # Validate inputs
        if action not in ("buy", "sell", "remove"):
            return (
                f"❌ Action không hợp lệ: **{action}**. "
                f"Chọn: `buy` | `sell` | `remove`"
            )

        if not symbol or not symbol.isalpha():
            return f"❌ Mã cổ phiếu không hợp lệ: **{symbol}**"

        if action != "remove":
            if qty <= 0:
                return f"❌ Số lượng phải > 0, nhận được: {qty}"
            if price <= 0:
                return f"❌ Giá phải > 0, nhận được: {price:,.0f}"

        manager = PortfolioManager()
        portfolio = manager.load()

        if action == "buy":
            old_pos = next((p for p in portfolio.positions if p.symbol == symbol), None)
            old_qty = old_pos.qty if old_pos else 0
            old_cost = old_pos.avg_cost if old_pos else 0

            manager.add_position(symbol, qty, price, notes)
            manager.save()

            new_pos = next((p for p in manager.portfolio.positions if p.symbol == symbol), None)
            new_qty = new_pos.qty if new_pos else qty
            new_cost = new_pos.avg_cost if new_pos else price
            total_cost = qty * price

            lines = [
                f"✅ **Mua thành công** — {symbol}",
                "",
                "| | |",
                "|--|--|",
                f"| Số lượng mua | {qty:,} CP |",
                f"| Giá mua | {price:,.0f} VNĐ |",
                f"| Tổng chi | {total_cost:,.0f} VNĐ |",
            ]
            if old_qty > 0:
                lines += [
                    f"| SL trước | {old_qty:,} CP @ {old_cost:,.0f} VNĐ |",
                    f"| **SL mới** | **{new_qty:,} CP @ {new_cost:,.0f} VNĐ** |",
                ]
            else:
                lines.append(f"| **Vị thế mới** | **{new_qty:,} CP @ {new_cost:,.0f} VNĐ** |")

            if notes:
                lines.append(f"| Ghi chú | {notes} |")
            lines.append("")
            lines.append("_T+2: Cổ phiếu về tài khoản sau 2 phiên giao dịch_")

        elif action == "sell":
            result = manager.remove_position(symbol, qty, price)
            if "error" in result:
                return f"❌ {result['error']}"

            manager.save()
            realized_pnl = result["realized_pnl"]
            pnl_pct = result["realized_pnl_pct"]
            pnl_icon = "🟢" if realized_pnl >= 0 else "🔴"
            pnl_str = f"{realized_pnl:+,.0f} VNĐ ({pnl_pct:+.2f}%)"

            lines = [
                f"✅ **Bán thành công** — {symbol}",
                "",
                "| | |",
                "|--|--|",
                f"| Số lượng bán | {qty:,} CP |",
                f"| Giá bán | {price:,.0f} VNĐ |",
                f"| Giá vốn | {result['avg_cost']:,.0f} VNĐ |",
                f"| {pnl_icon} Lãi/Lỗ thực hiện | **{pnl_str}** |",
                f"| Tiền nhận (T+2) | {qty * price:,.0f} VNĐ |",
                "",
                "_T+2 settlement: tiền về tài khoản sau 2 phiên giao dịch_",
            ]

        else:  # remove
            existing = next((p for p in portfolio.positions if p.symbol == symbol), None)
            if not existing:
                return f"❌ Không tìm thấy vị thế **{symbol}** trong danh mục."

            portfolio.positions = [p for p in portfolio.positions if p.symbol != symbol]
            manager.save()
            lines = [
                f"✅ **Đã xóa** vị thế **{symbol}** ({existing.qty:,} CP @ {existing.avg_cost:,.0f} VNĐ)",
                "",
                "_Lưu ý: Thao tác này không ảnh hưởng đến tài khoản thực tế, chỉ xóa khỏi file theo dõi._",
            ]

        return "\n".join(lines)

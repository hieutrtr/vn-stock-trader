"""
tools/insider.py — MCP tool giao dịch nội bộ (insider trading).

Tools:
  - get_insider_trades : Giao dịch của cổ đông lớn / lãnh đạo

Nguồn: Vietstock (nếu có) hoặc vnstock. Trả về best-effort.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Đăng ký insider tools vào FastMCP instance."""

    @mcp.tool()
    async def get_insider_trades(symbol: str, limit: int = 20) -> str:
        """
        Get recent insider trading activity for a Vietnamese listed company.

        Shows transactions by major shareholders (≥5%) and company executives
        (Board members, CEO, CFO). Data sourced from SSC disclosures via Vietstock.

        Note: Data availability depends on Vietstock's disclosure database.
        Not all companies have detailed insider transaction history.

        Args:
            symbol: Stock ticker (e.g. "VNM", "HPG", "ACB")
            limit: Maximum number of transactions to return (default 20)
        """
        from data_sources.vietstock_client import get_insider_trades as _get_insider

        symbol = symbol.upper().strip()
        limit = max(1, min(50, limit))

        try:
            trades = await _get_insider(symbol, limit=limit)
        except AttributeError:
            # vietstock_client chưa có hàm này — fallback
            trades = []
        except Exception as e:
            logger.warning("get_insider_trades(%s) failed: %s", symbol, e)
            trades = []

        if not trades:
            return (
                f"## 🔍 Giao dịch nội bộ — {symbol}\n\n"
                f"⚠️ Không tìm thấy dữ liệu giao dịch nội bộ cho **{symbol}**.\n\n"
                f"Có thể do:\n"
                f"- Mã không có giao dịch nội bộ gần đây\n"
                f"- Vietstock chưa cập nhật dữ liệu\n"
                f"- Mã không niêm yết trên sàn\n\n"
                f"_Nguồn: Vietstock (dữ liệu công bố theo quy định UBCKNN)_"
            )

        lines = [
            f"## 🔍 Giao dịch nội bộ — {symbol}",
            f"_{len(trades)} giao dịch gần nhất_",
            "",
            "| Ngày | Người GD | Chức vụ | Hành động | SL | Giá | Sau GD |",
            "|------|----------|---------|-----------|-----|-----|--------|",
        ]

        for trade in trades[:limit]:
            date = trade.get("date", "N/A")
            person = trade.get("person", "N/A")
            title = trade.get("title", "")
            action = trade.get("action", "")
            qty = trade.get("qty")
            price = trade.get("price")
            after_qty = trade.get("after_qty")

            # Action icon
            action_icon = "🟢 Mua" if "mua" in action.lower() or "buy" in action.lower() else \
                          "🔴 Bán" if "bán" in action.lower() or "sell" in action.lower() else action

            qty_str = f"{int(qty):,}" if qty else "N/A"
            price_str = f"{int(price):,}" if price else "N/A"
            after_str = f"{int(after_qty):,}" if after_qty else "N/A"

            lines.append(
                f"| {date} | {person[:20]} | {title[:15]} | {action_icon} | "
                f"{qty_str} | {price_str} | {after_str} |"
            )

        # Tóm tắt net buy/sell
        buy_trades = [t for t in trades if "mua" in str(t.get("action", "")).lower() or "buy" in str(t.get("action", "")).lower()]
        sell_trades = [t for t in trades if "bán" in str(t.get("action", "")).lower() or "sell" in str(t.get("action", "")).lower()]

        if buy_trades or sell_trades:
            buy_qty = sum(t.get("qty", 0) or 0 for t in buy_trades)
            sell_qty = sum(t.get("qty", 0) or 0 for t in sell_trades)
            net_qty = buy_qty - sell_qty
            net_icon = "🟢" if net_qty >= 0 else "🔴"

            lines += [
                "",
                "### Tóm tắt",
                f"- Giao dịch mua: **{len(buy_trades)}** lần ({buy_qty:,} CP)",
                f"- Giao dịch bán: **{len(sell_trades)}** lần ({sell_qty:,} CP)",
                f"- Mua ròng: {net_icon} **{net_qty:+,} CP**",
            ]

        lines += [
            "",
            "_Nguồn: Vietstock — dữ liệu công bố theo quy định UBCKNN_",
        ]

        return "\n".join(lines)

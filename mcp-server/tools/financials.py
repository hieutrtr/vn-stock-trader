"""
tools/financials.py — MCP tools báo cáo tài chính và so sánh ngành.

Tools:
  - get_financial_report : BCTC (income/balance/cashflow) + chỉ số định giá
  - get_sector_peers     : Cổ phiếu cùng ngành ICB với metrics
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def _fmt_bn(val: float | None, decimals: int = 1) -> str:
    """Format số tỷ VNĐ."""
    if val is None:
        return "N/A"
    if abs(val) >= 1000:
        return f"{val/1000:,.{decimals}f} nghìn tỷ"
    return f"{val:,.{decimals}f} tỷ"


def _fmt_ratio(val: float | None, decimals: int = 2, suffix: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{val:.{decimals}f}{suffix}"


def register(mcp: FastMCP) -> None:
    """Đăng ký financial tools vào FastMCP instance."""

    @mcp.tool()
    async def get_financial_report(
        symbol: str,
        num_quarters: int = 4,
        report_type: str = "all",
    ) -> str:
        """
        Get financial statements and valuation metrics for a Vietnamese listed company.

        Returns income statement, balance sheet, cash flow statement (quarterly),
        and key ratios: PE, PB, ROE, ROA, EPS, net margin, debt/equity.

        Args:
            symbol: Stock ticker (e.g. "VNM", "HPG", "ACB")
            num_quarters: Number of recent quarters (default 4, max 8)
            report_type: "income" | "balance" | "cashflow" | "ratios" | "all" (default)
        """
        from data_sources.vnstock_client import get_financial_report as _get_financials

        symbol = symbol.upper().strip()
        num_quarters = max(1, min(8, num_quarters))
        valid_types = {"income", "balance", "cashflow", "ratios", "all"}
        if report_type not in valid_types:
            report_type = "all"

        data = _get_financials(symbol)

        if "error" in data:
            return f"❌ Không lấy được BCTC của **{symbol}**: {data['error']}"

        lines = [f"## 💰 Báo cáo tài chính — {symbol}", ""]

        # ── Chỉ số định giá ──────────────────────────────────────────────────
        if report_type in ("ratios", "all"):
            ratios = data.get("ratios", {})
            if ratios:
                lines += [
                    "### 📊 Chỉ số định giá",
                    "",
                    "| Chỉ số | Giá trị | Diễn giải |",
                    "|--------|---------|-----------|",
                ]
                pe = ratios.get("pe")
                pb = ratios.get("pb")
                roe = ratios.get("roe")
                roa = ratios.get("roa")
                eps = ratios.get("eps")
                bvps = ratios.get("bvps")
                nm = ratios.get("net_margin")
                de = ratios.get("debt_equity")

                def _pe_signal(v):
                    if v is None:
                        return "N/A"
                    if v < 10:
                        return "Rẻ"
                    if v < 20:
                        return "Hợp lý"
                    if v < 30:
                        return "Đắt"
                    return "Rất đắt"

                def _roe_signal(v):
                    if v is None:
                        return "N/A"
                    if v >= 20:
                        return "Xuất sắc"
                    if v >= 15:
                        return "Tốt"
                    if v >= 10:
                        return "Khá"
                    return "Thấp"

                rows = [
                    ("P/E", _fmt_ratio(pe, 2, "x"), _pe_signal(pe)),
                    ("P/B", _fmt_ratio(pb, 2, "x"), ""),
                    ("ROE", _fmt_ratio(roe * 100 if roe and roe < 2 else roe, 1, "%"), _roe_signal(roe * 100 if roe and roe < 2 else roe)),
                    ("ROA", _fmt_ratio(roa * 100 if roa and roa < 2 else roa, 1, "%"), ""),
                    ("EPS", f"{int(eps):,} VNĐ" if eps else "N/A", ""),
                    ("BVPS", f"{int(bvps):,} VNĐ" if bvps else "N/A", ""),
                    ("Biên LN ròng", _fmt_ratio(nm * 100 if nm and nm < 2 else nm, 1, "%"), ""),
                    ("Nợ/Vốn CSH", _fmt_ratio(de, 2, "x"), ""),
                ]
                for name, val, signal in rows:
                    lines.append(f"| {name} | {val} | {signal} |")
                lines.append("")

        # ── Kết quả kinh doanh ───────────────────────────────────────────────
        if report_type in ("income", "all"):
            income = data.get("income_statement", [])
            if income:
                quarters_to_show = income[:num_quarters]
                lines += [
                    "### 📈 Kết quả kinh doanh (tỷ VNĐ)",
                    "",
                ]
                headers = ["Chỉ tiêu"] + [q.get("quarter", f"Q{i+1}") for i, q in enumerate(quarters_to_show)]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

                metrics = [
                    ("Doanh thu", "revenue"),
                    ("Lãi gộp", "gross_profit"),
                    ("Lãi ròng", "net_profit"),
                ]
                for label, key in metrics:
                    row_vals = [label]
                    for q in quarters_to_show:
                        val = q.get(key)
                        row_vals.append(_fmt_bn(val / 1e9 if val and abs(val) > 1e6 else val))
                    lines.append("| " + " | ".join(row_vals) + " |")
                lines.append("")

        # ── Bảng cân đối kế toán ─────────────────────────────────────────────
        if report_type in ("balance", "all"):
            balance = data.get("balance_sheet", [])
            if balance:
                quarters_to_show = balance[:num_quarters]
                lines += [
                    "### 🏦 Bảng cân đối kế toán (tỷ VNĐ)",
                    "",
                ]
                headers = ["Chỉ tiêu"] + [q.get("quarter", f"Q{i+1}") for i, q in enumerate(quarters_to_show)]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

                metrics = [
                    ("Tổng tài sản", "total_assets"),
                    ("Tổng nợ", "total_liabilities"),
                    ("Vốn chủ sở hữu", "equity"),
                ]
                for label, key in metrics:
                    row_vals = [label]
                    for q in quarters_to_show:
                        val = q.get(key)
                        row_vals.append(_fmt_bn(val / 1e9 if val and abs(val) > 1e6 else val))
                    lines.append("| " + " | ".join(row_vals) + " |")
                lines.append("")

        # ── Lưu chuyển tiền tệ ───────────────────────────────────────────────
        if report_type in ("cashflow", "all"):
            cashflow = data.get("cash_flow", [])
            if cashflow:
                quarters_to_show = cashflow[:num_quarters]
                lines += [
                    "### 💵 Lưu chuyển tiền tệ (tỷ VNĐ)",
                    "",
                ]
                headers = ["Chỉ tiêu"] + [q.get("quarter", f"Q{i+1}") for i, q in enumerate(quarters_to_show)]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

                metrics = [
                    ("CF hoạt động KD", "operating_cf"),
                    ("CF đầu tư", "investing_cf"),
                    ("CF tài chính", "financing_cf"),
                ]
                for label, key in metrics:
                    row_vals = [label]
                    for q in quarters_to_show:
                        val = q.get(key)
                        row_vals.append(_fmt_bn(val / 1e9 if val and abs(val) > 1e6 else val))
                    lines.append("| " + " | ".join(row_vals) + " |")
                lines.append("")

        if len(lines) <= 3:
            return f"⚠️ Không có dữ liệu BCTC cho **{symbol}**. Có thể mã không tồn tại hoặc chưa công bố."

        lines.append("_Nguồn: TCBS/Vietstock. Số liệu theo quý gần nhất có sẵn._")
        return "\n".join(lines)

    @mcp.tool()
    async def get_sector_peers(symbol: str) -> str:
        """
        Get peer companies in the same ICB sector and compare key valuation metrics.

        Useful for peer comparison analysis — PE, PB, ROE relative to sector.

        Args:
            symbol: Stock ticker to find peers for (e.g. "VNM", "HPG", "ACB")
        """
        from data_sources.vnstock_client import (
            get_financial_report as _get_financials,
        )
        from data_sources.vnstock_client import (
            get_sector_peers as _get_peers,
        )
        from data_sources.vnstock_client import (
            get_stock_price as _get_price,
        )

        symbol = symbol.upper().strip()

        peers = _get_peers(symbol)
        if not peers:
            return (
                f"⚠️ Không tìm thấy cổ phiếu cùng ngành với **{symbol}**. "
                f"Có thể mã không hợp lệ hoặc không có trong cơ sở dữ liệu."
            )

        lines = [
            f"## 🏭 Cổ phiếu cùng ngành — {symbol}",
            "",
            f"Tìm thấy **{len(peers)}** mã cùng ngành: {', '.join(peers)}",
            "",
            "### So sánh định giá",
            "",
            "| Mã | Giá (VNĐ) | P/E | P/B | ROE | ROA |",
            "|----|-----------|-----|-----|-----|-----|",
        ]

        # Thêm symbol chính vào đầu danh sách
        all_syms = [symbol] + [p for p in peers[:9] if p != symbol]

        for sym in all_syms:
            try:
                price_data = _get_price(sym)
                fin_data = _get_financials(sym)
                price = price_data.get("price", 0) if "error" not in price_data else 0
                ratios = fin_data.get("ratios", {}) if "error" not in fin_data else {}
                pe = _fmt_ratio(ratios.get("pe"), 1)
                pb = _fmt_ratio(ratios.get("pb"), 1)
                roe_raw = ratios.get("roe")
                roa_raw = ratios.get("roa")
                roe = _fmt_ratio(roe_raw * 100 if roe_raw and roe_raw < 2 else roe_raw, 1, "%")
                roa = _fmt_ratio(roa_raw * 100 if roa_raw and roa_raw < 2 else roa_raw, 1, "%")
                marker = " ⬅" if sym == symbol else ""
                lines.append(
                    f"| **{sym}{marker}** | {price:,.0f} | {pe} | {pb} | {roe} | {roa} |"
                )
            except Exception as e:
                logger.debug("Peer %s failed: %s", sym, e)
                lines.append(f"| {sym} | N/A | N/A | N/A | N/A | N/A |")

        lines += [
            "",
            "_Dữ liệu delay ~15 phút. Tỷ lệ ROE/ROA theo quý gần nhất._",
        ]
        return "\n".join(lines)

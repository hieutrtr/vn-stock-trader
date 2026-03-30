"""
VN Stock MCP Server — Entry Point
===================================
FastMCP server cung cấp tools cho Vietnamese stock traders.

Usage:
    uv run python mcp-server/server.py          # stdio transport (for Claude Code)
    uv run mcp dev mcp-server/server.py         # dev inspector

Tools exposed:
    get_stock_price        — Giá hiện tại + OHLCV
    get_market_overview    — VN-Index, HNX, breadth, foreign flow
    get_top_movers         — Top tăng/giảm/volume
    get_stock_history      — Lịch sử giá + chỉ báo TA
    get_financial_report   — BCTC + chỉ số định giá
    get_sector_peers       — Cổ phiếu cùng ngành
    get_news               — Tin tức thị trường
    screen_stocks          — Lọc cổ phiếu theo tiêu chí
    get_portfolio          — Danh mục + P&L
    update_portfolio       — Mua/bán/cập nhật danh mục
    get_insider_trades     — Giao dịch nội bộ
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Đảm bảo mcp-server directory trong path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

# ─── Tạo FastMCP instance ─────────────────────────────────────────────────────

mcp = FastMCP(
    "vn-stock-mcp",
    instructions=(
        "MCP server cung cấp dữ liệu thị trường chứng khoán Việt Nam (HOSE, HNX, UPCOM). "
        "Tất cả giá là VNĐ. Dữ liệu delay ~15 phút. "
        "T+2 settlement — tiền bán hôm nay (T) về sau 2 phiên giao dịch."
    ),
)

# ─── Đăng ký tools từ các module ─────────────────────────────────────────────

from tools.financials import register as register_financials  # noqa: E402
from tools.history import register as register_history  # noqa: E402
from tools.insider import register as register_insider  # noqa: E402
from tools.market import register as register_market  # noqa: E402
from tools.news import register as register_news  # noqa: E402
from tools.portfolio import register as register_portfolio  # noqa: E402
from tools.screener import register as register_screener  # noqa: E402

register_market(mcp)
register_history(mcp)
register_financials(mcp)
register_news(mcp)
register_screener(mcp)
register_portfolio(mcp)
register_insider(mcp)

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("vn-stock-mcp")


def main() -> None:
    """Chạy MCP server với stdio transport."""
    logger.info("VN Stock MCP Server starting...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

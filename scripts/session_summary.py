"""
session_summary.py — Script tổng kết phiên giao dịch.

Chạy lúc 14:50 sau ATC (hoặc cuối phiên) — tóm tắt phiên giao dịch hôm nay.
Output: Markdown summary lưu vào data/summaries/YYYY-MM-DD.md

Usage:
    uv run python scripts/session_summary.py
    uv run python scripts/session_summary.py --force   # bỏ qua check ngày giao dịch
    uv run python scripts/session_summary.py --quick   # chỉ in ngắn gọn
    uv run python scripts/session_summary.py --output stdout
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Thêm mcp-server vào path
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"
sys.path.insert(0, str(MCP_SERVER_DIR))

CONFIG_PATH = PROJECT_ROOT / "data" / "automation_config.json"
PORTFOLIO_PATH = PROJECT_ROOT / "data" / "portfolio.json"
WATCHLIST_PATH = PROJECT_ROOT / "data" / "watchlist.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("session_summary")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_portfolio_data() -> dict[str, Any]:
    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"positions": [], "cash": 0}


def load_watchlist() -> dict[str, Any]:
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"symbols": []}


def is_trading_day(d: date | None = None) -> bool:
    d = d or date.today()
    if d.weekday() >= 5:
        return False
    fixed_holidays = {(1, 1), (4, 30), (5, 1), (9, 2)}
    return (d.month, d.day) not in fixed_holidays


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    prefix = "+" if val > 0 else ""
    return f"{prefix}{val:.2f}%"


def _fmt_price(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:,.0f}"


# ─── Sections ─────────────────────────────────────────────────────────────────


def _section_market_result(market: dict) -> list[str]:
    """Section: Kết quả thị trường trong ngày."""
    lines = ["## 📊 Kết quả phiên hôm nay", ""]

    if "error" in market:
        lines.append(f"_Lỗi lấy dữ liệu: {market['error']}_")
        return lines

    def _idx_row(name: str, idx: dict) -> str:
        val = idx.get("value")
        chg = idx.get("change")
        pct = idx.get("pct")
        if val is None:
            return f"| {name} | N/A | — | — |"
        icon = "🟢" if (pct or 0) >= 0 else "🔴"
        return f"| {name} | {val:,.2f} | {icon} {chg:+.2f} | {_fmt_pct(pct)} |"

    lines += [
        "| Chỉ số | Điểm | Thay đổi | % |",
        "|--------|------|----------|---|",
        _idx_row("VN-Index", market.get("vn_index", {})),
        _idx_row("HNX-Index", market.get("hnx_index", {})),
        _idx_row("UPCOM-Index", market.get("upcom_index", {})),
        "",
    ]

    adv = market.get("advance")
    dec = market.get("decline")
    unc = market.get("unchanged")
    cei = market.get("ceiling")
    flo = market.get("floor")
    tv = market.get("total_value_bn_vnd")

    if adv is not None:
        lines.append(
            f"**Độ rộng:** Tăng **{adv}** | Giảm **{dec}** | Không đổi **{unc}** "
            f"| Trần **{cei}** | Sàn **{flo}**"
        )
    if tv:
        lines.append(f"**Thanh khoản:** {tv:,.0f} tỷ VNĐ")

    fn = market.get("foreign_net_bn")
    fb = market.get("foreign_buy_bn")
    fs = market.get("foreign_sell_bn")
    if fn is not None:
        icon = "🟢" if fn >= 0 else "🔴"
        lines.append(
            f"**Khối ngoại:** Mua {fb:.1f} tỷ | Bán {fs:.1f} tỷ | "
            f"Ròng {icon} {fn:+.1f} tỷ"
        )

    return lines


def _section_top_movers(movers: dict) -> list[str]:
    """Section: Top tăng/giảm hôm nay."""
    lines = ["## 🏆 Top movers hôm nay", ""]

    if "error" in movers:
        lines.append(f"_Lỗi: {movers['error']}_")
        return lines

    gainers = movers.get("gainers", [])[:5]
    losers = movers.get("losers", [])[:5]
    vol_leaders = movers.get("volume_leaders", [])[:5]

    if gainers:
        lines.append("**🟢 Tăng mạnh nhất:**")
        for s in gainers:
            sym = s.get("symbol", "N/A")
            price = s.get("price", 0)
            pct = s.get("pct_change", 0)
            lines.append(f"- **{sym}** {_fmt_price(price)} VNĐ ({_fmt_pct(pct)})")
        lines.append("")

    if losers:
        lines.append("**🔴 Giảm mạnh nhất:**")
        for s in losers:
            sym = s.get("symbol", "N/A")
            price = s.get("price", 0)
            pct = s.get("pct_change", 0)
            lines.append(f"- **{sym}** {_fmt_price(price)} VNĐ ({_fmt_pct(pct)})")
        lines.append("")

    if vol_leaders:
        lines.append("**🔊 Volume cao nhất:**")
        for s in vol_leaders:
            sym = s.get("symbol", "N/A")
            price = s.get("price", 0)
            vol = s.get("volume", 0)
            lines.append(f"- **{sym}** {_fmt_price(price)} VNĐ | {vol:,} CP")

    return lines


def _section_portfolio_pnl(portfolio_data: dict, prices: dict[str, dict]) -> list[str]:
    """Section: P&L danh mục trong ngày."""
    lines = ["## 💼 P&L danh mục hôm nay", ""]
    positions = portfolio_data.get("positions", [])

    if not positions:
        lines.append("_Danh mục trống._")
        return lines

    total_cost = 0.0
    total_mv = 0.0
    pos_rows: list[tuple[str, float, float, float, float]] = []

    for pos in positions:
        sym = pos["symbol"]
        qty = pos["qty"]
        cost = pos["avg_cost"]
        price_data = prices.get(sym, {})
        curr = price_data.get("price", cost)
        mv = qty * curr
        pnl = mv - qty * cost
        pnl_pct = (pnl / (qty * cost) * 100) if cost > 0 else 0
        total_cost += qty * cost
        total_mv += mv
        pos_rows.append((sym, curr, pnl, pnl_pct, mv))

    total_pnl = total_mv - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    lines += [
        "| Mã | Giá TT | P&L | P&L% | GT TT |",
        "|----|--------|-----|------|-------|",
    ]
    for sym, curr, pnl, pnl_pct, mv in sorted(pos_rows, key=lambda x: x[2], reverse=True):
        icon = "🟢" if pnl >= 0 else "🔴"
        lines.append(
            f"| **{sym}** | {_fmt_price(curr)} | {icon}{pnl:+,.0f} | "
            f"{_fmt_pct(pnl_pct)} | {_fmt_price(mv)} |"
        )

    pnl_icon = "🟢" if total_pnl >= 0 else "🔴"
    lines += [
        "",
        f"**Tổng P&L chưa thực hiện:** {pnl_icon} {total_pnl:+,.0f} VNĐ ({_fmt_pct(total_pnl_pct)})",
        f"**NAV ước tính:** {total_mv + portfolio_data.get('cash', 0):,.0f} VNĐ",
    ]

    return lines


def _section_session_news(news: list[dict]) -> list[str]:
    """Section: Tin nổi bật trong phiên."""
    lines = ["## 📰 Tin nổi bật trong phiên", ""]

    if not news:
        lines.append("_Không có tin mới._")
        return lines

    for item in news[:8]:
        title = item.get("title", "").strip()
        url = item.get("url", "")
        pub = item.get("published_at", "")
        if pub:
            try:
                pub_str = datetime.fromisoformat(pub).strftime("%H:%M")
            except ValueError:
                pub_str = pub[:5]
        else:
            pub_str = ""

        lines.append(f"- {title}" + (f" _{pub_str}_" if pub_str else ""))

    return lines


def _section_anomalies(
    market: dict,
    movers: dict,
    portfolio_data: dict,
    prices: dict[str, dict],
    config: dict,
) -> list[str]:
    """Section: Điểm bất thường cần chú ý."""
    thresholds = config.get("alert_thresholds", {})
    price_threshold = thresholds.get("price_change_pct", 5.0)
    anomalies: list[str] = []

    # Check portfolio positions có biến động lớn
    for pos in portfolio_data.get("positions", []):
        sym = pos["symbol"]
        price_data = prices.get(sym, {})
        pct = price_data.get("pct_change")
        if pct is not None and abs(pct) >= price_threshold:
            icon = "🟢" if pct >= 0 else "🔴"
            anomalies.append(
                f"- {icon} **{sym}** biến động {_fmt_pct(pct)} trong ngày "
                f"(ngưỡng: >{price_threshold:.0f}%)"
            )

    # Check khối ngoại bán ròng mạnh
    fn = market.get("foreign_net_bn")
    if fn is not None and fn < -500:
        anomalies.append(
            f"- ⚠️ Khối ngoại bán ròng mạnh: {fn:+.1f} tỷ VNĐ"
        )

    # Check số mã chạm sàn nhiều
    flo_count = market.get("floor")
    if flo_count is not None and flo_count >= 20:
        anomalies.append(
            f"- ⚠️ {flo_count} mã chạm sàn — thị trường có áp lực bán mạnh"
        )

    if not anomalies:
        return []

    return ["## ⚠️ Điểm bất thường cần chú ý", ""] + anomalies


def _section_tomorrow_plan(market: dict, movers: dict) -> list[str]:
    """Section: Gợi ý kế hoạch ngày mai."""
    lines = ["## 📋 Kế hoạch ngày mai", ""]

    vn_pct = market.get("vn_index", {}).get("pct", 0) or 0
    fn = market.get("foreign_net_bn", 0) or 0
    adv = market.get("advance", 0) or 0
    dec = market.get("decline", 0) or 0

    # Sentiment đơn giản
    if vn_pct > 0.5 and fn > 0:
        sentiment = "🟢 Tích cực — khối ngoại mua ròng, VN-Index tăng tốt"
        action = "Duy trì danh mục, theo dõi breakout mới"
    elif vn_pct < -0.5 and fn < 0:
        sentiment = "🔴 Tiêu cực — khối ngoại bán ròng, VN-Index điều chỉnh"
        action = "Thận trọng, kiểm tra lại stop loss"
    elif dec > adv:
        sentiment = "🟡 Thận trọng — nhiều mã giảm hơn tăng"
        action = "Chờ đợi, không vội mua thêm"
    else:
        sentiment = "🟡 Trung lập"
        action = "Theo dõi tín hiệu kỹ thuật từng mã"

    lines += [
        f"**Sentiment hôm nay:** {sentiment}",
        f"**Gợi ý hành động:** {action}",
        "",
        "_Lưu ý: Đây là nhận định tự động dựa trên dữ liệu định lượng, "
        "không thay thế phân tích chuyên sâu._",
    ]

    return lines


# ─── Main ─────────────────────────────────────────────────────────────────────


async def session_summary(force: bool = False, quick: bool = False) -> str:
    """
    Tổng kết phiên giao dịch.

    Returns:
        Markdown string của summary.
    """
    today = date.today()
    now = datetime.now()

    if not force and not is_trading_day(today):
        return f"_Hôm nay ({today.strftime('%d/%m/%Y')}) không phải ngày giao dịch._"

    config = load_config()
    portfolio_data = load_portfolio_data()
    watchlist = load_watchlist()

    # Import data sources
    try:
        from data_sources.vnstock_client import (
            get_market_overview,
            get_stock_price,
            get_top_movers,
        )
    except ImportError as e:
        logger.error("Không import được data_sources: %s", e)
        return f"❌ Lỗi import: {e}"

    try:
        from data_sources.news_scraper import get_market_news
    except ImportError:
        get_market_news = None  # type: ignore[assignment]

    logger.info("Đang lấy dữ liệu tổng kết phiên...")

    # Thu thập data
    market: dict = {}
    movers: dict = {}
    prices: dict[str, dict] = {}
    news: list[dict] = []

    try:
        market = get_market_overview()
    except Exception as e:
        logger.warning("get_market_overview failed: %s", e)
        market = {"error": str(e)}

    try:
        movers = get_top_movers(n=5)
    except Exception as e:
        logger.warning("get_top_movers failed: %s", e)
        movers = {"error": str(e)}

    # Prices cho portfolio positions
    all_symbols = list(set(
        [p["symbol"] for p in portfolio_data.get("positions", [])]
        + watchlist.get("symbols", [])
    ))
    for sym in all_symbols:
        try:
            prices[sym] = get_stock_price(sym)
        except Exception as e:
            logger.warning("get_stock_price(%s) failed: %s", sym, e)
            prices[sym] = {"error": str(e)}

    if get_market_news is not None:
        try:
            news = await get_market_news(limit=10)
        except Exception as e:
            logger.warning("get_market_news failed: %s", e)

    # Build summary
    sections: list[list[str]] = [
        [
            f"# 📈 Session Summary — {today.strftime('%A, %d/%m/%Y')}",
            f"_Tổng kết phiên lúc {now.strftime('%H:%M')} — ATC kết thúc ~14:45_",
            "",
        ],
        _section_market_result(market),
        [""],
    ]

    if not quick:
        sections += [
            _section_top_movers(movers),
            [""],
        ]

    sections += [
        _section_portfolio_pnl(portfolio_data, prices),
        [""],
    ]

    if not quick:
        anomaly_section = _section_anomalies(market, movers, portfolio_data, prices, config)
        if anomaly_section:
            sections += [anomaly_section, [""]]

        sections += [
            _section_session_news(news),
            [""],
            _section_tomorrow_plan(market, movers),
            [""],
        ]

    sections.append([
        "---",
        f"_Cập nhật: {now.strftime('%H:%M:%S %d/%m/%Y')} | Dữ liệu delay ~15 phút_",
    ])

    all_lines: list[str] = []
    for section in sections:
        if section:
            all_lines.extend(section)

    return "\n".join(all_lines)


def save_summary(content: str, output_dir: Path) -> Path:
    """Lưu summary ra file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{date.today().isoformat()}.md"
    filename.write_text(content, encoding="utf-8")
    logger.info("Summary saved to %s", filename)
    return filename


async def main() -> None:
    parser = argparse.ArgumentParser(description="VN Stock Session Summary")
    parser.add_argument("--force", action="store_true", help="Bỏ qua check ngày giao dịch")
    parser.add_argument("--quick", action="store_true", help="Output ngắn gọn (chỉ market + P&L)")
    parser.add_argument(
        "--output",
        choices=["file", "stdout", "both"],
        default="both",
        help="In ra stdout, lưu file, hoặc cả hai (default: both)",
    )
    args = parser.parse_args()

    config = load_config()
    output_cfg = config.get("output", {})
    summaries_dir = PROJECT_ROOT / output_cfg.get("summaries_dir", "data/summaries")

    summary = await session_summary(force=args.force, quick=args.quick)

    if args.output in ("stdout", "both"):
        print(summary)

    if args.output in ("file", "both"):
        saved_path = save_summary(summary, summaries_dir)
        if args.output == "file":
            print(f"Summary saved to: {saved_path}")


if __name__ == "__main__":
    asyncio.run(main())

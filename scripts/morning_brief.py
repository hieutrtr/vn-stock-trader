"""
morning_brief.py — Script tổng hợp thông tin trước phiên giao dịch.

Chạy lúc 8:30 sáng mỗi ngày giao dịch (T2-T6, không phải lễ).
Output: Markdown brief lưu vào data/briefs/YYYY-MM-DD.md

Usage:
    uv run python scripts/morning_brief.py
    uv run python scripts/morning_brief.py --force   # bỏ qua check ngày lễ
    uv run python scripts/morning_brief.py --output stdout
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

# Thêm mcp-server vào path để import data_sources
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"
sys.path.insert(0, str(MCP_SERVER_DIR))

# ─── Config ──────────────────────────────────────────────────────────────────

CONFIG_PATH = PROJECT_ROOT / "data" / "automation_config.json"
WATCHLIST_PATH = PROJECT_ROOT / "data" / "watchlist.json"
PORTFOLIO_PATH = PROJECT_ROOT / "data" / "portfolio.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("morning_brief")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def load_config() -> dict[str, Any]:
    """Load automation config."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_watchlist() -> dict[str, Any]:
    """Load watchlist.json."""
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"symbols": [], "alerts": []}


def load_portfolio_summary() -> dict[str, Any]:
    """Load portfolio positions (không fetch giá live)."""
    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {
            "positions": data.get("positions", []),
            "cash": data.get("cash", 0),
            "symbols": [p["symbol"] for p in data.get("positions", [])],
        }
    return {"positions": [], "cash": 0, "symbols": []}


def is_trading_day(d: date | None = None) -> bool:
    """
    Kiểm tra ngày có phải ngày giao dịch không.
    Hiện tại check thứ 7, CN. Có thể mở rộng thêm lịch lễ sau.
    """
    d = d or date.today()
    if d.weekday() >= 5:  # 5 = Sat, 6 = Sun
        return False
    # Các ngày lễ VN cố định (có thể mở rộng)
    fixed_holidays = {
        (1, 1),    # Tết Dương lịch
        (4, 30),   # Ngày Giải phóng
        (5, 1),    # Ngày Quốc tế Lao động
        (9, 2),    # Ngày Quốc khánh
    }
    if (d.month, d.day) in fixed_holidays:
        return False
    return True


def _fmt_pct(val: float | None, sign: bool = True) -> str:
    if val is None:
        return "N/A"
    prefix = "+" if (sign and val > 0) else ""
    return f"{prefix}{val:.2f}%"


def _fmt_index(name: str, idx: dict) -> str:
    val = idx.get("value")
    pct = idx.get("pct")
    if val is None:
        return f"**{name}:** N/A"
    icon = "🟢" if (pct or 0) >= 0 else "🔴"
    return f"**{name}:** {icon} {val:,.2f} ({_fmt_pct(pct)})"


# ─── Các section của brief ───────────────────────────────────────────────────


def _section_market_overview(market: dict) -> list[str]:
    """Section: Tổng quan thị trường (từ phiên hôm qua)."""
    lines = ["## 📊 Thị trường phiên hôm qua", ""]

    if "error" in market:
        lines.append(f"_Không lấy được dữ liệu: {market['error']}_")
        return lines

    lines += [
        _fmt_index("VN-Index", market.get("vn_index", {})),
        _fmt_index("HNX-Index", market.get("hnx_index", {})),
        _fmt_index("UPCOM-Index", market.get("upcom_index", {})),
        "",
    ]

    adv = market.get("advance")
    dec = market.get("decline")
    cei = market.get("ceiling")
    flo = market.get("floor")
    if adv is not None:
        lines.append(
            f"**Độ rộng:** Tăng {adv} | Giảm {dec} | Trần {cei} | Sàn {flo}"
        )

    tv = market.get("total_value_bn_vnd")
    if tv:
        lines.append(f"**Thanh khoản:** {tv:,.0f} tỷ VNĐ")

    fn = market.get("foreign_net_bn")
    if fn is not None:
        icon = "🟢" if fn >= 0 else "🔴"
        lines.append(f"**Khối ngoại ròng:** {icon} {fn:+.1f} tỷ VNĐ")

    return lines


def _section_portfolio_status(portfolio: dict, prices: dict[str, dict]) -> list[str]:
    """Section: Trạng thái danh mục."""
    lines = ["## 💼 Danh mục — trạng thái", ""]
    positions = portfolio.get("positions", [])

    if not positions:
        lines.append("_Danh mục trống._")
        return lines

    total_cost = sum(p["qty"] * p["avg_cost"] for p in positions)
    total_mv = 0.0
    pos_lines = []

    for pos in positions:
        sym = pos["symbol"]
        qty = pos["qty"]
        cost = pos["avg_cost"]
        price_data = prices.get(sym, {})
        curr_price = price_data.get("price", cost)
        mv = qty * curr_price
        pnl = mv - qty * cost
        pnl_pct = (pnl / (qty * cost) * 100) if cost > 0 else 0
        total_mv += mv
        icon = "🟢" if pnl >= 0 else "🔴"
        pos_lines.append(
            f"- **{sym}** {qty:,} CP @ {cost:,.0f} → {curr_price:,.0f} VNĐ "
            f"{icon} {pnl_pct:+.2f}%"
        )

    total_pnl = total_mv - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    pnl_icon = "🟢" if total_pnl >= 0 else "🔴"

    lines += pos_lines
    lines += [
        "",
        f"**Tổng P&L:** {pnl_icon} {total_pnl:+,.0f} VNĐ ({total_pnl_pct:+.2f}%)",
        f"**Tiền mặt:** {portfolio.get('cash', 0):,.0f} VNĐ",
    ]
    return lines


def _section_watchlist(watchlist_symbols: list[str], prices: dict[str, dict]) -> list[str]:
    """Section: Watchlist hôm nay."""
    lines = ["## 👀 Watchlist hôm nay", ""]

    if not watchlist_symbols:
        lines.append("_Watchlist trống._")
        return lines

    for sym in watchlist_symbols:
        price_data = prices.get(sym, {})
        if "error" in price_data or not price_data:
            lines.append(f"- **{sym}** — N/A")
            continue
        curr = price_data.get("price", 0)
        pct = price_data.get("pct_change", 0)
        ceil = price_data.get("ceiling", 0)
        icon = "🟢" if pct >= 0 else "🔴"
        room_ceil = ((ceil - curr) / curr * 100) if curr > 0 else 0
        lines.append(
            f"- **{sym}** {icon} {curr:,.0f} VNĐ ({_fmt_pct(pct)}) "
            f"| Còn đến trần: {room_ceil:.1f}%"
        )

    return lines


def _section_news(news: list[dict]) -> list[str]:
    """Section: Tin tức quan trọng."""
    lines = ["## 📰 Tin tức qua đêm", ""]

    if not news:
        lines.append("_Không có tin tức mới._")
        return lines

    for item in news[:10]:
        title = item.get("title", "").strip()
        url = item.get("url", "")
        pub = item.get("published_at", "")
        source = item.get("source", "")
        if pub:
            try:
                pub_dt = datetime.fromisoformat(pub)
                pub_str = pub_dt.strftime("%H:%M %d/%m")
            except ValueError:
                pub_str = pub[:16]
        else:
            pub_str = ""

        lines.append(f"- {title} _{pub_str} / {source}_")

    return lines


def _section_watchlist_alerts(watchlist: dict, prices: dict[str, dict], config: dict) -> list[str]:
    """Section: Alerts từ watchlist conditions."""
    alerts = watchlist.get("alerts", [])
    if not alerts:
        return []

    triggered = []

    for alert in alerts:
        sym = alert.get("symbol", "")
        condition = alert.get("condition", "")
        value = alert.get("value", 0)
        note = alert.get("note", "")
        price_data = prices.get(sym, {})
        curr = price_data.get("price", 0)

        hit = False
        if condition == "price_below" and curr > 0 and curr <= value:
            hit = True
            msg = f"**{sym}** đang ở {curr:,.0f} ≤ {value:,.0f} (price_below) — {note}"
        elif condition == "price_above" and curr > 0 and curr >= value:
            hit = True
            msg = f"**{sym}** đang ở {curr:,.0f} ≥ {value:,.0f} (price_above) — {note}"
        else:
            msg = ""

        if hit:
            triggered.append(f"🔔 {msg}")

    if triggered:
        return ["## ⚠️ Alerts kích hoạt", ""] + triggered
    return []


# ─── Main ─────────────────────────────────────────────────────────────────────


async def morning_brief(force: bool = False) -> str:
    """
    Tổng hợp morning brief.

    Returns:
        Markdown string của brief.
    """
    today = date.today()
    now = datetime.now()

    if not force and not is_trading_day(today):
        day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        day_name = day_names[today.weekday()]
        return f"_Hôm nay ({day_name} {today.strftime('%d/%m/%Y')}) không phải ngày giao dịch. Bỏ qua._"

    config = load_config()
    watchlist = load_watchlist()
    portfolio = load_portfolio_summary()

    # Import data sources
    try:
        from data_sources.vnstock_client import get_market_overview, get_stock_price
    except ImportError as e:
        logger.error("Không import được data_sources: %s", e)
        return f"❌ Lỗi import data_sources: {e}"

    try:
        from data_sources.news_scraper import get_market_news
    except ImportError as e:
        logger.warning("Không import được news_scraper: %s", e)
        get_market_news = None  # type: ignore[assignment]

    logger.info("Đang lấy dữ liệu thị trường...")

    # Thu thập data song song (best effort)
    market: dict = {}
    prices: dict[str, dict] = {}
    news: list[dict] = []

    # Market overview
    try:
        market = get_market_overview()
    except Exception as e:
        logger.warning("get_market_overview failed: %s", e)
        market = {"error": str(e)}

    # Prices cho watchlist + portfolio
    all_symbols = list(set(watchlist.get("symbols", []) + portfolio.get("symbols", [])))
    for sym in all_symbols:
        try:
            prices[sym] = get_stock_price(sym)
        except Exception as e:
            logger.warning("get_stock_price(%s) failed: %s", sym, e)
            prices[sym] = {"error": str(e)}

    # News
    if get_market_news is not None:
        try:
            news = await get_market_news(limit=15)
        except Exception as e:
            logger.warning("get_market_news failed: %s", e)
            news = []

    # Tạo brief
    sections: list[list[str]] = [
        [
            f"# 🌅 Morning Brief — {today.strftime('%A, %d/%m/%Y')}",
            f"_Tổng hợp lúc {now.strftime('%H:%M')} — Dữ liệu delay ~15 phút_",
            "",
        ],
        _section_market_overview(market),
        [""],
        _section_portfolio_status(portfolio, prices),
        [""],
        _section_watchlist(watchlist.get("symbols", []), prices),
        [""],
        _section_watchlist_alerts(watchlist, prices, config),
        [""],
        _section_news(news),
        [""],
        [
            "---",
            f"_Nguồn: vnstock / CafeF / Vietstock. Cập nhật: {now.strftime('%H:%M:%S %d/%m/%Y')}_",
            "_Lưu ý: Đây là dữ liệu delay ~15 phút, không phải realtime. Không dùng cho giao dịch tức thì._",
        ],
    ]

    all_lines: list[str] = []
    for section in sections:
        if section:
            all_lines.extend(section)

    return "\n".join(all_lines)


def save_brief(content: str, output_dir: Path) -> Path:
    """Lưu brief ra file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{date.today().isoformat()}.md"
    filename.write_text(content, encoding="utf-8")
    logger.info("Brief saved to %s", filename)
    return filename


async def main() -> None:
    parser = argparse.ArgumentParser(description="VN Stock Morning Brief")
    parser.add_argument("--force", action="store_true", help="Bỏ qua kiểm tra ngày giao dịch")
    parser.add_argument(
        "--output",
        choices=["file", "stdout", "both"],
        default="both",
        help="In ra stdout, lưu file, hoặc cả hai (default: both)",
    )
    args = parser.parse_args()

    config = load_config()
    output_cfg = config.get("output", {})
    briefs_dir = PROJECT_ROOT / output_cfg.get("briefs_dir", "data/briefs")

    brief = await morning_brief(force=args.force)

    if args.output in ("stdout", "both"):
        print(brief)

    if args.output in ("file", "both"):
        saved_path = save_brief(brief, briefs_dir)
        if args.output == "file":
            print(f"Brief saved to: {saved_path}")


if __name__ == "__main__":
    asyncio.run(main())

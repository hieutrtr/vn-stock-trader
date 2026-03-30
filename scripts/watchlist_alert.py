"""
watchlist_alert.py — Kiểm tra điều kiện alert cho watchlist.

Đọc data/watchlist.json → kiểm tra điều kiện → in alert khi triggered.
Có thể chạy độc lập hoặc tích hợp vào portfolio_monitor.

Alert conditions hỗ trợ:
  - price_below  : Giá ≤ value
  - price_above  : Giá ≥ value
  - pct_change_above : % thay đổi trong ngày ≥ value (VD: 5 = +5%)
  - pct_change_below : % thay đổi trong ngày ≤ value (VD: -5 = -5%)
  - near_ceiling : Còn ≤ value% đến trần (VD: 1 = còn 1%)
  - near_floor   : Còn ≤ value% đến sàn

Usage:
    uv run python scripts/watchlist_alert.py
    uv run python scripts/watchlist_alert.py --watchlist data/watchlist.json
    uv run python scripts/watchlist_alert.py --dry-run   # chỉ in, không ghi log
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Thêm mcp-server vào path
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"
sys.path.insert(0, str(MCP_SERVER_DIR))

WATCHLIST_PATH = PROJECT_ROOT / "data" / "watchlist.json"
CONFIG_PATH = PROJECT_ROOT / "data" / "automation_config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("watchlist_alert")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def load_watchlist(path: Path) -> dict[str, Any]:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"symbols": [], "alerts": []}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    prefix = "+" if val > 0 else ""
    return f"{prefix}{val:.2f}%"


# ─── Alert evaluation ─────────────────────────────────────────────────────────


def evaluate_alert(alert: dict, price_data: dict) -> tuple[bool, str]:
    """
    Kiểm tra một alert condition.

    Returns:
        (triggered: bool, message: str)
    """
    if "error" in price_data or not price_data:
        return False, ""

    sym = alert.get("symbol", "")
    condition = alert.get("condition", "")
    value = float(alert.get("value", 0))
    note = alert.get("note", "")

    curr = price_data.get("price", 0) or 0
    pct = price_data.get("pct_change", 0) or 0
    ceil = price_data.get("ceiling", 0) or 0
    flr = price_data.get("floor", 0) or 0

    triggered = False
    msg = ""

    if condition == "price_below":
        if curr > 0 and curr <= value:
            triggered = True
            msg = (
                f"**{sym}** price_below: {curr:,.0f} ≤ {value:,.0f} VNĐ"
                + (f" | {note}" if note else "")
            )

    elif condition == "price_above":
        if curr > 0 and curr >= value:
            triggered = True
            msg = (
                f"**{sym}** price_above: {curr:,.0f} ≥ {value:,.0f} VNĐ"
                + (f" | {note}" if note else "")
            )

    elif condition == "pct_change_above":
        if pct >= value:
            triggered = True
            msg = (
                f"**{sym}** pct_change_above: {_fmt_pct(pct)} ≥ {value:+.1f}%"
                + (f" | {note}" if note else "")
            )

    elif condition == "pct_change_below":
        if pct <= value:
            triggered = True
            msg = (
                f"**{sym}** pct_change_below: {_fmt_pct(pct)} ≤ {value:+.1f}%"
                + (f" | {note}" if note else "")
            )

    elif condition == "near_ceiling":
        if curr > 0 and ceil > 0:
            room = (ceil - curr) / curr * 100
            if 0 <= room <= value:
                triggered = True
                msg = (
                    f"**{sym}** near_ceiling: còn {room:.2f}% đến trần {ceil:,.0f} VNĐ"
                    + (f" | {note}" if note else "")
                )

    elif condition == "near_floor":
        if curr > 0 and flr > 0:
            room = (curr - flr) / curr * 100
            if 0 <= room <= value:
                triggered = True
                msg = (
                    f"**{sym}** near_floor: còn {room:.2f}% đến sàn {flr:,.0f} VNĐ"
                    + (f" | {note}" if note else "")
                )

    else:
        logger.warning("Condition không hỗ trợ: %s (symbol: %s)", condition, sym)

    return triggered, msg


def check_watchlist(
    watchlist: dict[str, Any],
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """
    Kiểm tra tất cả alerts trong watchlist.

    Returns:
        List các alert đã trigger với thông tin chi tiết.
    """
    alerts = watchlist.get("alerts", [])
    symbols_all = watchlist.get("symbols", [])

    # Thu thập unique symbols (từ alerts + watchlist symbols)
    alert_symbols = {a.get("symbol", "") for a in alerts}
    all_symbols = list(alert_symbols | set(symbols_all))

    if not all_symbols:
        logger.info("Không có symbol nào trong watchlist")
        return []

    # Import
    try:
        from data_sources.vnstock_client import get_stock_price
    except ImportError as e:
        logger.error("Không import được data_sources: %s", e)
        return []

    # Lấy giá
    prices: dict[str, Any] = {}
    for sym in all_symbols:
        if not sym:
            continue
        try:
            prices[sym] = get_stock_price(sym)
            logger.debug("Price %s: %s", sym, prices[sym].get("price"))
        except Exception as e:
            logger.warning("get_stock_price(%s) failed: %s", sym, e)
            prices[sym] = {"error": str(e)}

    # Đánh giá từng alert
    triggered_alerts: list[dict[str, Any]] = []
    now_str = datetime.now().strftime("%H:%M:%S")

    for alert in alerts:
        sym = alert.get("symbol", "")
        price_data = prices.get(sym, {})
        triggered, msg = evaluate_alert(alert, price_data)

        if triggered:
            alert_result = {
                "symbol": sym,
                "condition": alert.get("condition"),
                "value": alert.get("value"),
                "note": alert.get("note", ""),
                "message": msg,
                "price": price_data.get("price"),
                "pct_change": price_data.get("pct_change"),
                "timestamp": now_str,
            }
            triggered_alerts.append(alert_result)

            if not dry_run:
                print(f"[{now_str}] 🔔 WATCHLIST ALERT: {msg}", flush=True)
            else:
                print(f"[DRY-RUN] 🔔 {msg}", flush=True)

    # Print summary cho symbols không có alert
    if not dry_run:
        unalerted = [
            sym for sym in symbols_all
            if sym and not any(a.get("symbol") == sym for a in alerts)
        ]
        if unalerted:
            logger.info("Watchlist symbols không có alert conditions: %s", ", ".join(unalerted))
            for sym in unalerted:
                pd_data = prices.get(sym, {})
                if "error" not in pd_data and pd_data:
                    curr = pd_data.get("price", 0)
                    pct = pd_data.get("pct_change", 0)
                    icon = "🟢" if (pct or 0) >= 0 else "🔴"
                    print(f"  [{now_str}] {icon} {sym}: {curr:,.0f} VNĐ ({_fmt_pct(pct)})")

    if not triggered_alerts:
        logger.info("Không có alert nào được kích hoạt")

    return triggered_alerts


def print_watchlist_status(watchlist: dict[str, Any]) -> None:
    """In trạng thái giá toàn bộ watchlist."""
    symbols = watchlist.get("symbols", [])
    if not symbols:
        print("Watchlist trống.")
        return

    try:
        from data_sources.vnstock_client import get_stock_price
    except ImportError as e:
        print(f"Lỗi import: {e}")
        return

    print(f"\n{'='*60}")
    print(f"WATCHLIST STATUS — {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    print(f"{'='*60}")
    print(f"{'Mã':<8} {'Giá':>12} {'% Ngày':>8} {'Trần':>10} {'Sàn':>10}")
    print(f"{'-'*60}")

    for sym in symbols:
        try:
            pd_data = get_stock_price(sym)
            if "error" in pd_data:
                print(f"{sym:<8} {'[Lỗi]':>12}")
                continue
            curr = pd_data.get("price", 0) or 0
            pct = pd_data.get("pct_change", 0) or 0
            ceil = pd_data.get("ceiling", 0) or 0
            flr = pd_data.get("floor", 0) or 0
            icon = "🟢" if pct >= 0 else "🔴"
            print(
                f"{sym:<8} {curr:>12,.0f} {icon}{pct:>+7.2f}% "
                f"{ceil:>10,.0f} {flr:>10,.0f}"
            )
        except Exception as e:
            print(f"{sym:<8} [Lỗi: {e}]")

    print(f"{'='*60}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="VN Stock Watchlist Alert")
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=WATCHLIST_PATH,
        help="Đường dẫn đến watchlist.json",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Chỉ print kết quả, không ghi log",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="In trạng thái giá toàn bộ watchlist (không check alerts)",
    )
    args = parser.parse_args()

    watchlist = load_watchlist(args.watchlist)

    if args.status:
        print_watchlist_status(watchlist)
        return

    logger.info("Kiểm tra watchlist: %s", args.watchlist)
    triggered = check_watchlist(watchlist, dry_run=args.dry_run)

    if triggered:
        print(f"\n✅ {len(triggered)} alert(s) được kích hoạt.", flush=True)
    else:
        print("✅ Không có alert nào được kích hoạt.", flush=True)


if __name__ == "__main__":
    main()

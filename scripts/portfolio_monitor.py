"""
portfolio_monitor.py — Theo dõi danh mục trong phiên giao dịch.

Chạy liên tục mỗi N phút (mặc định 5 phút) trong giờ giao dịch.
Alert khi:
  - Cổ phiếu thay đổi > 5% so với tham chiếu
  - Volume spike > 3x trung bình 20 phiên
  - Sắp chạm trần (còn < 1%) hoặc chạm sàn
  - VN-Index thay đổi > 1%

Usage:
    uv run python scripts/portfolio_monitor.py
    uv run python scripts/portfolio_monitor.py --interval 300   # 5 phút
    uv run python scripts/portfolio_monitor.py --portfolio data/portfolio.json
    uv run python scripts/portfolio_monitor.py --once   # chỉ chạy 1 lần rồi thoát
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from datetime import time as dtime
from pathlib import Path
from typing import Any

# Thêm mcp-server vào path
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"
sys.path.insert(0, str(MCP_SERVER_DIR))

CONFIG_PATH = PROJECT_ROOT / "data" / "automation_config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("portfolio_monitor")

# ─── Trạng thái theo dõi ─────────────────────────────────────────────────────

_alerted_today: set[str] = set()   # Tránh alert trùng lặp trong ngày
_running = True


def _handle_sigint(sig: int, frame: object) -> None:
    global _running
    logger.info("Nhận SIGINT — dừng monitor...")
    _running = False


signal.signal(signal.SIGINT, _handle_sigint)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_portfolio(path: Path) -> dict[str, Any]:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"positions": [], "cash": 0}


def is_trading_session(now: datetime | None = None) -> bool:
    """Kiểm tra có trong giờ giao dịch không (9:00-11:30 và 13:00-14:45)."""
    config = load_config()
    trading = config.get("trading_hours", {})
    now = now or datetime.now()
    t = now.time()

    # Parse từ config hoặc dùng default
    try:
        mo = dtime.fromisoformat(trading.get("morning_open", "09:00"))
        mc = dtime.fromisoformat(trading.get("morning_close", "11:30"))
        ao = dtime.fromisoformat(trading.get("afternoon_open", "13:00"))
        ac = dtime.fromisoformat(trading.get("afternoon_close", "14:45"))
    except ValueError:
        mo = dtime(9, 0)
        mc = dtime(11, 30)
        ao = dtime(13, 0)
        ac = dtime(14, 45)

    # Bỏ qua cuối tuần
    if now.weekday() >= 5:
        return False

    return (mo <= t <= mc) or (ao <= t <= ac)


def _alert(msg: str, key: str | None = None) -> None:
    """In alert ra stdout với timestamp. Tránh trùng nếu key đã alert hôm nay."""
    if key and key in _alerted_today:
        return
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔔 ALERT: {msg}", flush=True)
    if key:
        _alerted_today.add(key)


def _get_volume_average(symbol: str, days: int = 20) -> float | None:
    """Lấy khối lượng trung bình 20 phiên gần nhất."""
    try:
        from data_sources.vnstock_client import get_stock_history
        df = get_stock_history(symbol, period="3m")
        if df.empty or "volume" not in df.columns:
            return None
        avg = df["volume"].tail(days).mean()
        return float(avg) if avg > 0 else None
    except Exception:
        return None


# ─── Check functions ──────────────────────────────────────────────────────────


def check_price_changes(
    positions: list[dict],
    prices: dict[str, Any],
    threshold_pct: float,
) -> list[str]:
    """Kiểm tra thay đổi giá vượt ngưỡng."""
    alerts: list[str] = []
    for pos in positions:
        sym = pos["symbol"]
        price_data = prices.get(sym, {})
        if "error" in price_data or not price_data:
            continue
        pct = price_data.get("pct_change", 0) or 0
        curr = price_data.get("price", 0) or 0
        if abs(pct) >= threshold_pct:
            icon = "🟢" if pct >= 0 else "🔴"
            key = f"price_change:{sym}:{int(pct)}"
            msg = f"{sym} thay đổi {icon} {pct:+.2f}% | Giá: {curr:,.0f} VNĐ"
            alerts.append((msg, key))
    return alerts


def check_near_ceiling_floor(
    positions: list[dict],
    prices: dict[str, Any],
    near_threshold_pct: float = 1.0,
) -> list[str]:
    """Kiểm tra cổ phiếu sắp chạm trần hoặc chạm sàn."""
    alerts: list[str] = []
    for pos in positions:
        sym = pos["symbol"]
        price_data = prices.get(sym, {})
        if "error" in price_data or not price_data:
            continue
        curr = price_data.get("price", 0) or 0
        ceil = price_data.get("ceiling", 0) or 0
        flr = price_data.get("floor", 0) or 0

        if curr <= 0:
            continue

        if ceil > 0:
            room_ceil = (ceil - curr) / curr * 100
            if 0 <= room_ceil <= near_threshold_pct:
                key = f"near_ceil:{sym}"
                msg = f"{sym} sắp chạm TRẦN — còn {room_ceil:.1f}% (trần: {ceil:,.0f})"
                alerts.append((msg, key))

        if flr > 0:
            room_flr = (curr - flr) / curr * 100
            if 0 <= room_flr <= near_threshold_pct:
                key = f"near_floor:{sym}"
                msg = f"{sym} sắp chạm SÀN — còn {room_flr:.1f}% (sàn: {flr:,.0f})"
                alerts.append((msg, key))

    return alerts


def check_volume_spike(
    positions: list[dict],
    prices: dict[str, Any],
    spike_ratio: float = 3.0,
) -> list[tuple[str, str]]:
    """Kiểm tra volume bất thường (> spike_ratio × TB20)."""
    alerts: list[tuple[str, str]] = []
    for pos in positions:
        sym = pos["symbol"]
        price_data = prices.get(sym, {})
        if "error" in price_data or not price_data:
            continue
        curr_vol = price_data.get("volume", 0) or 0
        if curr_vol <= 0:
            continue

        avg_vol = _get_volume_average(sym)
        if avg_vol and avg_vol > 0:
            ratio = curr_vol / avg_vol
            if ratio >= spike_ratio:
                key = f"vol_spike:{sym}"
                msg = (
                    f"{sym} volume spike {ratio:.1f}× TB20 "
                    f"({curr_vol:,.0f} CP vs TB {avg_vol:,.0f} CP)"
                )
                alerts.append((msg, key))

    return alerts


def check_market_index(market: dict, threshold_pct: float = 1.0) -> list[tuple[str, str]]:
    """Kiểm tra VN-Index thay đổi lớn."""
    alerts: list[tuple[str, str]] = []
    pct = market.get("vn_index", {}).get("pct", 0) or 0
    val = market.get("vn_index", {}).get("value", 0) or 0
    if abs(pct) >= threshold_pct:
        icon = "🟢" if pct >= 0 else "🔴"
        key = f"vnindex:{int(pct * 10)}"
        msg = f"VN-Index thay đổi mạnh {icon} {pct:+.2f}% | {val:,.2f} điểm"
        alerts.append((msg, key))
    return alerts


# ─── Monitor loop ─────────────────────────────────────────────────────────────


def run_check(portfolio_data: dict, config: dict) -> None:
    """Chạy một lần kiểm tra."""
    thresholds = config.get("alert_thresholds", {})
    price_threshold = thresholds.get("price_change_pct", 5.0)
    vol_spike_ratio = thresholds.get("volume_spike_ratio", 3.0)
    near_ceil_pct = thresholds.get("near_ceiling_pct", 1.0)

    positions = portfolio_data.get("positions", [])
    if not positions:
        logger.info("Danh mục trống — không có gì để theo dõi")
        return

    symbols = [p["symbol"] for p in positions]
    logger.info("Kiểm tra %d mã: %s", len(symbols), ", ".join(symbols))

    # Import
    try:
        from data_sources.vnstock_client import get_market_overview, get_stock_price
    except ImportError as e:
        logger.error("Không import được data_sources: %s", e)
        return

    # Lấy giá
    prices: dict[str, Any] = {}
    for sym in symbols:
        try:
            prices[sym] = get_stock_price(sym)
        except Exception as e:
            logger.warning("get_stock_price(%s) failed: %s", sym, e)
            prices[sym] = {"error": str(e)}

    # Lấy market overview
    market: dict = {}
    try:
        market = get_market_overview()
    except Exception as e:
        logger.warning("get_market_overview failed: %s", e)
        market = {"error": str(e)}

    # --- Run checks ---
    all_alerts: list[tuple[str, str]] = []

    all_alerts.extend(check_price_changes(positions, prices, price_threshold))
    all_alerts.extend(check_near_ceiling_floor(positions, prices, near_ceil_pct))
    all_alerts.extend(check_volume_spike(positions, prices, vol_spike_ratio))

    if "error" not in market:
        all_alerts.extend(check_market_index(market, threshold_pct=1.0))

    # Fire alerts
    if all_alerts:
        for msg, key in all_alerts:
            _alert(msg, key)
    else:
        logger.info("Không có bất thường — danh mục ổn định")


def monitor_loop(portfolio_path: Path, interval_seconds: int, force_session: bool) -> None:
    """Vòng lặp chính của monitor."""
    config = load_config()
    logger.info(
        "Portfolio monitor bắt đầu | portfolio: %s | interval: %ds",
        portfolio_path, interval_seconds,
    )
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Portfolio monitor started. Press Ctrl+C to stop.")

    global _running
    while _running:
        now = datetime.now()

        if not force_session and not is_trading_session(now):
            # Kiểm tra đã qua 14:45 chưa — nếu qua thì dừng
            if now.time() > dtime(14, 45):
                print(f"[{now.strftime('%H:%M:%S')}] Phiên giao dịch kết thúc. Dừng monitor.")
                break
            next_open = "09:00" if now.time() < dtime(9, 0) else "13:00"
            logger.info("Ngoài giờ giao dịch. Tiếp tục khi %s.", next_open)
            time.sleep(60)  # sleep 1 phút rồi check lại
            continue

        portfolio_data = load_portfolio(portfolio_path)
        run_check(portfolio_data, config)

        logger.info("Xong. Đợi %d giây...", interval_seconds)
        # Sleep từng giây để có thể ngắt nhanh
        for _ in range(interval_seconds):
            if not _running:
                break
            time.sleep(1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitor dừng.")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="VN Stock Portfolio Monitor")
    parser.add_argument(
        "--interval", type=int, default=300,
        help="Khoảng thời gian giữa các lần check (giây, default: 300 = 5 phút)",
    )
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=PROJECT_ROOT / "data" / "portfolio.json",
        help="Đường dẫn đến portfolio.json",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Chỉ chạy 1 lần rồi thoát (không loop)",
    )
    parser.add_argument(
        "--force-session", action="store_true",
        help="Bỏ qua kiểm tra giờ giao dịch",
    )
    args = parser.parse_args()

    if args.once:
        config = load_config()
        portfolio_data = load_portfolio(args.portfolio)
        run_check(portfolio_data, config)
    else:
        monitor_loop(args.portfolio, args.interval, args.force_session)


if __name__ == "__main__":
    main()

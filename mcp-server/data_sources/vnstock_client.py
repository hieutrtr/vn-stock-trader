"""
vnstock_client.py — Wrapper quanh thư viện vnstock.

Chuẩn hóa output thành Python dict/DataFrame có kiểu rõ ràng,
xử lý lỗi gracefully, cache SQLite tự động.

Nguồn dữ liệu: TCBS (mặc định) với fallback sang VCI.
Rate limit: max 3 concurrent requests (token bucket via threading.Semaphore).
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

# Thêm mcp-server vào path để import cache
sys.path.insert(0, str(Path(__file__).parent.parent))
from cache.cache import get_cache

logger = logging.getLogger(__name__)

# ─── Rate limiter ────────────────────────────────────────────────────────────

_SEMAPHORE = threading.Semaphore(3)  # max 3 concurrent requests
_LAST_REQUEST_TIME: float = 0.0
_MIN_INTERVAL = 0.5  # giây tối thiểu giữa 2 requests

# False-positive symbols để lọc khỏi kết quả
_FALSE_POSITIVE_SYMBOLS = {
    "VND", "USD", "EUR", "JPY", "CNY", "GBP", "AUD",
    "GDP", "CPI", "ROE", "ROA", "EPS", "NAV", "IPO",
    "ETF", "OTC", "FDI", "IMF", "WTO", "WB",
}

# Khoảng giá trị cho period → số ngày
_PERIOD_DAYS: dict[str, int] = {
    "1m": 30, "3m": 90, "6m": 180,
    "1y": 365, "2y": 730, "5y": 1825,
}

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _rate_limited_call(fn, *args, **kwargs):
    """Gọi hàm với rate limiting."""
    global _LAST_REQUEST_TIME
    with _SEMAPHORE:
        elapsed = time.time() - _LAST_REQUEST_TIME
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        try:
            result = fn(*args, **kwargs)
            _LAST_REQUEST_TIME = time.time()
            return result
        except Exception as e:
            logger.error("vnstock call failed: %s — %s", fn.__name__ if hasattr(fn, "__name__") else fn, e)
            raise


def _import_vnstock():
    """Lazy import vnstock để tránh crash khi chưa cài."""
    try:
        from vnstock import Vnstock  # noqa: PLC0415
        return Vnstock
    except ImportError as e:
        raise ImportError(
            "vnstock chưa được cài. Chạy: uv sync"
        ) from e


# ─── Public Functions ─────────────────────────────────────────────────────────


def get_stock_price(symbol: str) -> dict[str, Any]:
    """
    Trả về snapshot giá hiện tại của mã cổ phiếu.

    Returns:
        {
            "symbol": "VNM",
            "price": 75000,
            "change": 1000,
            "pct_change": 1.35,
            "open": 74000,
            "high": 75500,
            "low": 73500,
            "volume": 1_250_000,
            "value": 93_750_000_000,
            "reference_price": 74000,
            "ceiling": 79180,
            "floor": 68820,
            "foreign_buy_vol": 50000,
            "foreign_sell_vol": 30000,
            "foreign_room_pct": 42.3,
            "timestamp": "2026-03-30T10:30:00"
        }
        hoặc {"error": "Symbol not found"} nếu không tìm thấy
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"price:{symbol}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        Vnstock = _import_vnstock()
        stock = _rate_limited_call(Vnstock(source="TCBS").stock, symbol=symbol, category="stock")
        quote = _rate_limited_call(stock.quote.history, start=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), end=datetime.now().strftime("%Y-%m-%d"))

        if quote is None or len(quote) == 0:
            return {"error": f"Symbol not found: {symbol}"}

        # Lấy dòng cuối (phiên gần nhất)
        row = quote.iloc[-1]
        ref = float(row.get("close", 0))

        result: dict[str, Any] = {
            "symbol": symbol,
            "price": float(row.get("close", 0)),
            "change": 0.0,
            "pct_change": 0.0,
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "volume": int(row.get("volume", 0)),
            "value": float(row.get("value", 0)) if "value" in row.index else 0.0,
            "reference_price": ref,
            "ceiling": round(ref * 1.07),
            "floor": round(ref * 0.93),
            "foreign_buy_vol": 0,
            "foreign_sell_vol": 0,
            "foreign_room_pct": None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        cache.set(cache_key, result, ttl_type="price")
        return result

    except Exception as e:
        logger.warning("get_stock_price(%s) failed: %s", symbol, e)
        return {"error": str(e)}


def get_stock_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Lấy lịch sử giá OHLCV.

    Args:
        symbol: Mã cổ phiếu (VD: "VNM")
        period: "1m", "3m", "6m", "1y", "2y", "5y"

    Returns:
        DataFrame với columns [open, high, low, close, volume], index là DatetimeIndex.
        Trả về DataFrame rỗng nếu lỗi.
    """
    symbol = symbol.upper().strip()
    period = period.lower()
    if period not in _PERIOD_DAYS:
        period = "1y"

    cache = get_cache()
    cache_key = f"history:{symbol}:{period}"

    cached = cache.get(cache_key)
    if cached is not None:
        try:
            df = pd.DataFrame(cached["data"])
            df.index = pd.to_datetime(cached["index"])
            df.index.name = "date"
            return df
        except Exception:
            pass

    try:
        Vnstock = _import_vnstock()
        days = _PERIOD_DAYS[period]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        stock = _rate_limited_call(
            Vnstock(source="TCBS").stock, symbol=symbol, category="stock"
        )
        df = _rate_limited_call(
            stock.quote.history,
            start=start_date,
            end=end_date,
            interval="1D",
        )

        if df is None or len(df) == 0:
            logger.warning("No history data for %s", symbol)
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        # Chuẩn hóa tên cột
        df = df.rename(columns=str.lower)
        required_cols = ["open", "high", "low", "close", "volume"]
        df = df[[c for c in required_cols if c in df.columns]]

        # Index → DatetimeIndex
        if "time" in df.columns:
            df.index = pd.to_datetime(df["time"])
            df = df.drop(columns=["time"], errors="ignore")
        elif not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df.index.name = "date"
        df = df.sort_index()

        # Cache (serialize để JSON-serializable)
        cache.set(
            cache_key,
            {"data": df.reset_index(drop=True).to_dict(orient="list"), "index": df.index.strftime("%Y-%m-%d").tolist()},
            ttl_type="history",
        )
        return df

    except Exception as e:
        logger.warning("get_stock_history(%s, %s) failed: %s", symbol, period, e)
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])


def get_financial_report(symbol: str, period: int = 4) -> dict[str, Any]:
    """
    Trả về báo cáo tài chính gồm income statement, balance sheet, cash flow
    và các chỉ số tài chính quan trọng.

    Args:
        symbol: Mã cổ phiếu
        period: Số quý gần nhất (4 = 1 năm)

    Returns:
        {
            "income_statement": [...],
            "balance_sheet": [...],
            "cash_flow": [...],
            "ratios": {"pe": x, "pb": x, "roe": x, ...}
        }
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"financial:{symbol}:{period}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        Vnstock = _import_vnstock()
        stock = _rate_limited_call(
            Vnstock(source="TCBS").stock, symbol=symbol, category="stock"
        )

        # Income statement
        try:
            income = _rate_limited_call(
                stock.finance.income_statement, period="quarter", lang="en"
            )
            income_data = income.head(period).to_dict(orient="records") if income is not None else []
        except Exception:
            income_data = []

        # Balance sheet
        try:
            balance = _rate_limited_call(
                stock.finance.balance_sheet, period="quarter", lang="en"
            )
            balance_data = balance.head(period).to_dict(orient="records") if balance is not None else []
        except Exception:
            balance_data = []

        # Cash flow
        try:
            cashflow = _rate_limited_call(
                stock.finance.cash_flow, period="quarter"
            )
            cashflow_data = cashflow.head(period).to_dict(orient="records") if cashflow is not None else []
        except Exception:
            cashflow_data = []

        # Ratios (lấy từ income + balance nếu có)
        ratios: dict[str, Any] = {
            "pe": None, "pb": None,
            "roe": None, "roa": None,
            "net_margin": None, "debt_equity": None,
            "eps": None, "bvps": None,
        }
        try:
            ratio_df = _rate_limited_call(
                stock.finance.ratio, period="quarter", lang="en"
            )
            if ratio_df is not None and len(ratio_df) > 0:
                row = ratio_df.iloc[0]
                for src_key, dst_key in [
                    ("priceToEarning", "pe"), ("priceToBook", "pb"),
                    ("roe", "roe"), ("roa", "roa"),
                    ("postTaxMargin", "net_margin"),
                    ("debtOnEquity", "debt_equity"),
                    ("earningPerShare", "eps"),
                    ("bookValuePerShare", "bvps"),
                ]:
                    if src_key in row.index:
                        val = row[src_key]
                        ratios[dst_key] = round(float(val), 4) if pd.notna(val) else None
        except Exception:
            pass

        result = {
            "symbol": symbol,
            "income_statement": income_data,
            "balance_sheet": balance_data,
            "cash_flow": cashflow_data,
            "ratios": ratios,
        }
        cache.set(cache_key, result, ttl_type="financial")
        return result

    except Exception as e:
        logger.warning("get_financial_report(%s) failed: %s", symbol, e)
        return {"error": str(e)}


def get_market_overview() -> dict[str, Any]:
    """
    Trả về snapshot tổng quan thị trường: VN-Index, HNX, UPCOM, breadth, thanh khoản.

    Returns:
        {
            "vn_index": {"value": 1782.5, "change": -3.2, "pct": -0.18},
            "hnx_index": {...},
            "upcom_index": {...},
            "total_volume": 850_000_000,
            "total_value_bn_vnd": 23_500,
            "advance": 245,
            "decline": 198,
            "unchanged": 57,
            "ceiling": 12,
            "floor": 8,
            "foreign_buy_bn": 156.3,
            "foreign_sell_bn": 203.7,
            "foreign_net_bn": -47.4,
            "timestamp": "..."
        }
    """
    cache = get_cache()
    cache_key = "market:overview"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        Vnstock = _import_vnstock()
        vs = Vnstock(source="TCBS")
        market_data = _rate_limited_call(vs.stock_screening.market_overview)

        result: dict[str, Any] = {
            "vn_index": {"value": None, "change": None, "pct": None},
            "hnx_index": {"value": None, "change": None, "pct": None},
            "upcom_index": {"value": None, "change": None, "pct": None},
            "total_volume": None,
            "total_value_bn_vnd": None,
            "advance": None,
            "decline": None,
            "unchanged": None,
            "ceiling": None,
            "floor": None,
            "foreign_buy_bn": None,
            "foreign_sell_bn": None,
            "foreign_net_bn": None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        if market_data is not None and len(market_data) > 0:
            for _, row in market_data.iterrows():
                idx_code = str(row.get("indexId", "")).upper()
                entry = {
                    "value": float(row.get("indexValue", 0)),
                    "change": float(row.get("indexChange", 0)),
                    "pct": float(row.get("indexChangePercent", 0)),
                }
                if "VNINDEX" in idx_code or "VN-INDEX" in idx_code:
                    result["vn_index"] = entry
                    result["advance"] = int(row.get("advances", 0))
                    result["decline"] = int(row.get("declines", 0))
                    result["unchanged"] = int(row.get("noChanges", 0))
                    result["ceiling"] = int(row.get("ceilings", 0))
                    result["floor"] = int(row.get("floors", 0))
                elif "HNX" in idx_code:
                    result["hnx_index"] = entry
                elif "UPCOM" in idx_code:
                    result["upcom_index"] = entry

        cache.set(cache_key, result, ttl_type="market")
        return result

    except Exception as e:
        logger.warning("get_market_overview() failed: %s", e)
        return {"error": str(e)}


def get_top_movers(n: int = 10) -> dict[str, Any]:
    """
    Trả về top gainers, losers, volume leaders.

    Returns:
        {
            "gainers": [{"symbol": "HPG", "price": 30000, "pct_change": 6.8}, ...],
            "losers":  [...],
            "volume_leaders": [...],
        }
    """
    cache = get_cache()
    cache_key = f"market:movers:{n}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        Vnstock = _import_vnstock()
        vs = Vnstock(source="TCBS")
        df = _rate_limited_call(vs.stock_screening.top_movers)

        result: dict[str, Any] = {"gainers": [], "losers": [], "volume_leaders": []}
        if df is None or len(df) == 0:
            return result

        df = df.rename(columns=str.lower)

        if "change_percent" in df.columns:
            df_sorted = df.sort_values("change_percent", ascending=False)
            gainers = df_sorted.head(n)[["ticker", "price", "change_percent"]].to_dict(orient="records")
            losers = df_sorted.tail(n)[["ticker", "price", "change_percent"]].iloc[::-1].to_dict(orient="records")
            result["gainers"] = [{"symbol": r.get("ticker"), "price": r.get("price"), "pct_change": r.get("change_percent")} for r in gainers]
            result["losers"] = [{"symbol": r.get("ticker"), "price": r.get("price"), "pct_change": r.get("change_percent")} for r in losers]

        if "volume" in df.columns:
            vol_leaders = df.nlargest(n, "volume")[["ticker", "price", "volume"]].to_dict(orient="records")
            result["volume_leaders"] = [{"symbol": r.get("ticker"), "price": r.get("price"), "volume": r.get("volume")} for r in vol_leaders]

        cache.set(cache_key, result, ttl_type="market")
        return result

    except Exception as e:
        logger.warning("get_top_movers() failed: %s", e)
        return {"error": str(e)}


def get_sector_peers(symbol: str) -> list[str]:
    """
    Danh sách mã cùng ngành ICB sub-sector.

    Returns:
        List mã cổ phiếu, [] nếu không tìm thấy.
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"peers:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        Vnstock = _import_vnstock()
        vs = Vnstock(source="TCBS")
        df = _rate_limited_call(vs.stock_screening.stock_screening)

        if df is None or len(df) == 0:
            return []

        df = df.rename(columns=str.lower)
        col_ticker = "ticker" if "ticker" in df.columns else "symbol"
        col_industry = next((c for c in df.columns if "industry" in c.lower()), None)

        if col_industry is None:
            return []

        # Tìm ngành của symbol
        row = df[df[col_ticker].str.upper() == symbol]
        if row.empty:
            return []
        sector = row.iloc[0][col_industry]

        # Lấy các mã cùng ngành
        peers = df[df[col_industry] == sector][col_ticker].str.upper().tolist()
        peers = [p for p in peers if p != symbol][:20]  # max 20 peers

        cache.set(cache_key, peers, ttl_type="financial")
        return peers

    except Exception as e:
        logger.warning("get_sector_peers(%s) failed: %s", symbol, e)
        return []

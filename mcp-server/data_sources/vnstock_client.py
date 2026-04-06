"""
vnstock_client.py — Wrapper quanh thư viện vnstock.

Chuẩn hóa output thành Python dict/DataFrame có kiểu rõ ràng,
xử lý lỗi gracefully, cache SQLite tự động.

Nguồn dữ liệu: VCI (mặc định) với fallback sang MSN.
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
        # vnstock 3.5.0: stock() nhận symbol trực tiếp, không có category param
        stock = _rate_limited_call(Vnstock(source="VCI").stock, symbol=symbol)
        # Dùng price_board để lấy real-time data (ceiling/floor/ref_price/foreign)
        pb_raw = _rate_limited_call(stock.trading.price_board, [symbol])

        if pb_raw is None or len(pb_raw) == 0:
            return {"error": f"Symbol not found: {symbol}"}

        # Flatten MultiIndex columns (nếu là MultiIndex)
        if isinstance(pb_raw.columns, pd.MultiIndex):
            pb_raw.columns = ["_".join(col).strip() for col in pb_raw.columns.values]
        row = pb_raw.iloc[0]

        ref_price = float(row.get("listing_ref_price", 0) or 0)
        match_price = float(row.get("match_match_price", 0) or 0)
        # Fallback nếu match_price = 0 (ngoài giờ), dùng ref_price
        if match_price == 0:
            match_price = ref_price

        change = match_price - ref_price
        pct_change = (change / ref_price * 100) if ref_price > 0 else 0.0

        foreign_buy = int(row.get("match_foreign_buy_volume", 0) or 0)
        foreign_sell = int(row.get("match_foreign_sell_volume", 0) or 0)
        current_room = float(row.get("match_current_room", 0) or 0)
        total_room = float(row.get("match_total_room", 0) or 0)
        foreign_room_pct = round(current_room / total_room * 100, 2) if total_room > 0 else None

        result: dict[str, Any] = {
            "symbol": symbol,
            "price": match_price,
            "change": round(change, 2),
            "pct_change": round(pct_change, 2),
            "open": float(row.get("match_open_price", 0) or 0),
            "high": float(row.get("match_highest", 0) or 0),
            "low": float(row.get("match_lowest", 0) or 0),
            "volume": int(row.get("match_accumulated_volume", 0) or 0),
            "value": float(row.get("match_accumulated_value", 0) or 0) * 1_000_000,  # million VND → VND
            "reference_price": ref_price,
            "ceiling": float(row.get("listing_ceiling", 0) or round(ref_price * 1.07)),
            "floor": float(row.get("listing_floor", 0) or round(ref_price * 0.93)),
            "foreign_buy_vol": foreign_buy,
            "foreign_sell_vol": foreign_sell,
            "foreign_room_pct": foreign_room_pct,
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
            Vnstock(source="VCI").stock, symbol=symbol
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
            Vnstock(source="VCI").stock, symbol=symbol
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
                # vnstock 3.5.0 trả về MultiIndex columns — flatten trước
                if isinstance(ratio_df.columns, pd.MultiIndex):
                    ratio_df.columns = [
                        "_".join(str(c) for c in col).strip()
                        for col in ratio_df.columns.values
                    ]
                row = ratio_df.iloc[0]
                # Map tên cột mới → key nội bộ
                # Cột dạng "Chỉ tiêu định giá_P/E" sau khi flatten
                _ratio_map = {
                    "Chỉ tiêu định giá_P/E": "pe",
                    "Chỉ tiêu định giá_P/B": "pb",
                    "Chỉ tiêu khả năng sinh lợi_ROE (%)": "roe",
                    "Chỉ tiêu khả năng sinh lợi_ROA (%)": "roa",
                    "Chỉ tiêu khả năng sinh lợi_Net Profit Margin (%)": "net_margin",
                    "Chỉ tiêu cơ cấu nguồn vốn_Debt/Equity": "debt_equity",
                    "Chỉ tiêu định giá_EPS (VND)": "eps",
                    "Chỉ tiêu định giá_BVPS (VND)": "bvps",
                }
                for src_key, dst_key in _ratio_map.items():
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

        def _get_index_data(index_symbol: str) -> dict[str, Any]:
            """Lấy giá trị index hôm nay và hôm qua để tính change/pct."""
            try:
                stock = Vnstock(source="VCI").stock(symbol=index_symbol)
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                end_date = datetime.now().strftime("%Y-%m-%d")
                df = _rate_limited_call(stock.quote.history, start=start_date, end=end_date)
                if df is None or len(df) < 2:
                    return {"value": None, "change": None, "pct": None}
                today = df.iloc[-1]
                yesterday = df.iloc[-2]
                value = float(today["close"])
                prev = float(yesterday["close"])
                change = round(value - prev, 2)
                pct = round(change / prev * 100, 2) if prev > 0 else 0.0
                return {"value": round(value, 2), "change": change, "pct": pct}
            except Exception as e:
                logger.debug("_get_index_data(%s) failed: %s", index_symbol, e)
                return {"value": None, "change": None, "pct": None}

        vn_index = _get_index_data("VNINDEX")
        hnx_index = _get_index_data("HNXINDEX")
        upcom_index = _get_index_data("UPCOMINDEX")

        # Breadth từ price_board của một sample stocks HOSE
        _LIQUID_STOCKS = [
            "VNM", "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HPG",
            "FPT", "VHM", "VIC", "GAS", "SAB", "MSN", "PLX", "POW", "HDB",
            "LPB", "SHB", "SSI", "PNJ", "REE", "DCM", "DGC", "MWG", "BCM",
            "GVR", "STB", "EIB", "NVL", "KDH", "DXG", "PDR", "NLG",
        ]
        advance = decline = unchanged = ceiling_cnt = floor_cnt = 0
        total_vol = 0
        total_val = 0.0
        foreign_buy = 0.0
        foreign_sell = 0.0

        try:
            pb_stock = Vnstock(source="VCI").stock(symbol="VNM")
            pb_raw = _rate_limited_call(pb_stock.trading.price_board, _LIQUID_STOCKS)
            if pb_raw is not None and len(pb_raw) > 0:
                if isinstance(pb_raw.columns, pd.MultiIndex):
                    pb_raw.columns = ["_".join(col).strip() for col in pb_raw.columns.values]
                for _, r in pb_raw.iterrows():
                    ref = float(r.get("listing_ref_price", 0) or 0)
                    mp = float(r.get("match_match_price", 0) or 0)
                    ceil_p = float(r.get("listing_ceiling", 0) or 0)
                    floor_p = float(r.get("listing_floor", 0) or 0)
                    if ref > 0 and mp > 0:
                        if mp > ref:
                            advance += 1
                        elif mp < ref:
                            decline += 1
                        else:
                            unchanged += 1
                        if mp >= ceil_p > 0:
                            ceiling_cnt += 1
                        if mp <= floor_p > 0:
                            floor_cnt += 1
                    total_vol += int(r.get("match_accumulated_volume", 0) or 0)
                    total_val += float(r.get("match_accumulated_value", 0) or 0) * 1_000_000  # million VND → VND
                    foreign_buy += float(r.get("match_foreign_buy_value", 0) or 0)   # in VND
                    foreign_sell += float(r.get("match_foreign_sell_value", 0) or 0)  # in VND
        except Exception as e:
            logger.debug("Breadth calculation failed: %s", e)

        result: dict[str, Any] = {
            "vn_index": vn_index,
            "hnx_index": hnx_index,
            "upcom_index": upcom_index,
            "total_volume": total_vol if total_vol > 0 else None,
            "total_value_bn_vnd": round(total_val / 1e9, 1) if total_val > 0 else None,
            "advance": advance if advance + decline + unchanged > 0 else None,
            "decline": decline if advance + decline + unchanged > 0 else None,
            "unchanged": unchanged if advance + decline + unchanged > 0 else None,
            "ceiling": ceiling_cnt if advance + decline + unchanged > 0 else None,
            "floor": floor_cnt if advance + decline + unchanged > 0 else None,
            "foreign_buy_bn": round(foreign_buy / 1e9, 1) if foreign_buy > 0 else None,
            "foreign_sell_bn": round(foreign_sell / 1e9, 1) if foreign_sell > 0 else None,
            "foreign_net_bn": round((foreign_buy - foreign_sell) / 1e9, 1) if (foreign_buy + foreign_sell) > 0 else None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

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

        # Dùng price_board với universe liquid stocks thay cho stock_screening.top_movers
        _UNIVERSE = [
            "VNM", "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HPG", "FPT",
            "VHM", "VIC", "GAS", "SAB", "MSN", "PLX", "POW", "HDB", "LPB", "SHB",
            "SSI", "PNJ", "REE", "DCM", "DGC", "MWG", "BCM", "GVR", "STB", "EIB",
            "NVL", "KDH", "DXG", "PDR", "NLG", "HSG", "NKG", "DPM", "HAG", "PVD",
            "BSI", "VHC", "ANV", "IDC", "KBC", "SCS", "PC1", "TDH", "VND", "HCM",
        ]

        stock = Vnstock(source="VCI").stock(symbol="VNM")
        pb_raw = _rate_limited_call(stock.trading.price_board, _UNIVERSE)

        result: dict[str, Any] = {"gainers": [], "losers": [], "volume_leaders": []}
        if pb_raw is None or len(pb_raw) == 0:
            return result

        # Flatten MultiIndex (nếu là MultiIndex)
        if isinstance(pb_raw.columns, pd.MultiIndex):
            pb_raw.columns = ["_".join(col).strip() for col in pb_raw.columns.values]
        pb_raw = pb_raw.rename(columns={
            "listing_symbol": "symbol",
            "match_match_price": "price",
            "listing_ref_price": "ref_price",
            "match_accumulated_volume": "volume",
        })

        # Lọc rows có dữ liệu hợp lệ
        valid = pb_raw[
            pb_raw["symbol"].notna() &
            (pb_raw["price"].fillna(0) > 0) &
            (pb_raw["ref_price"].fillna(0) > 0)
        ].copy()

        if len(valid) == 0:
            return result

        valid["pct_change"] = ((valid["price"] - valid["ref_price"]) / valid["ref_price"] * 100).round(2)

        df_sorted = valid.sort_values("pct_change", ascending=False)
        gainers = df_sorted.head(n)[["symbol", "price", "pct_change"]].to_dict(orient="records")
        losers = df_sorted.tail(n)[["symbol", "price", "pct_change"]].iloc[::-1].to_dict(orient="records")
        vol_leaders = valid.nlargest(n, "volume")[["symbol", "price", "volume"]].to_dict(orient="records")

        result["gainers"] = [{"symbol": r["symbol"], "price": float(r["price"]), "pct_change": float(r["pct_change"])} for r in gainers]
        result["losers"] = [{"symbol": r["symbol"], "price": float(r["price"]), "pct_change": float(r["pct_change"])} for r in losers]
        result["volume_leaders"] = [{"symbol": r["symbol"], "price": float(r["price"]), "volume": int(r["volume"])} for r in vol_leaders]

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
        from vnstock import Listing  # noqa: PLC0415

        # vnstock 3.5.0: dùng Listing.symbols_by_industries() thay cho stock_screening
        df = _rate_limited_call(Listing().symbols_by_industries)

        if df is None or len(df) == 0:
            return []

        # df có columns: symbol, industry_code, industry_name
        col_ticker = "symbol"
        col_industry = "industry_name"

        if col_ticker not in df.columns or col_industry not in df.columns:
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

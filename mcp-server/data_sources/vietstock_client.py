"""
vietstock_client.py — Crawler lấy dữ liệu từ Vietstock.vn

Dữ liệu lấy:
  - Financial ratios (PE, PB, ROE, EPS...)
  - Income statement, Balance sheet
  - Company info (ngành ICB, vốn hóa)
  - Tin tức theo mã

Rate limiting: delay ngẫu nhiên 1–2.5s giữa các request.
Anti-blocking: rotate User-Agent, set Referer.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from cache.cache import get_cache

logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

BASE_URL = "https://finance.vietstock.vn"
NEWS_URL = "https://vietstock.vn"

REQUEST_DELAY_RANGE = (1.0, 2.5)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://vietstock.vn/",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _fetch_html(url: str, timeout: int = 15) -> str | None:
    """Fetch HTML với rate limiting và error handling."""
    # Random delay
    delay = random.uniform(*REQUEST_DELAY_RANGE)
    await asyncio.sleep(delay)

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP %s fetching %s: %s", e.response.status_code, url, e)
        return None
    except httpx.RequestError as e:
        logger.warning("Request error fetching %s: %s", url, e)
        return None
    except Exception as e:
        logger.warning("Unexpected error fetching %s: %s", url, e)
        return None


def _safe_float(val: Any) -> float | None:
    """Chuyển đổi value thành float, trả về None nếu lỗi."""
    if val is None:
        return None
    try:
        cleaned = re.sub(r"[^\d\.\-]", "", str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _parse_vn_date(text: str) -> str | None:
    """Parse ngày Việt Nam: 'DD/MM/YYYY' hoặc 'DD/MM/YYYY HH:MM' → ISO format."""
    if not text:
        return None
    text = text.strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return text  # trả về nguyên bản nếu không parse được


# ─── Public Functions ─────────────────────────────────────────────────────────


async def get_financial_ratios(symbol: str) -> dict[str, Any]:
    """
    Lấy PE, PB, ROE, ROA, EPS, BVPS theo quý từ Vietstock.

    Returns:
        {
            "symbol": "VNM",
            "pe": 15.2, "pb": 3.4, "roe": 28.5, "roa": 12.1,
            "eps": 4500, "bvps": 22000, "net_margin": 18.3,
            "debt_equity": 0.45, "source": "vietstock",
            "updated_at": "2026-03-30T..."
        }
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"vs:ratios:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/{symbol}/tai-chinh.htm"
    html = await _fetch_html(url)

    result: dict[str, Any] = {
        "symbol": symbol,
        "pe": None, "pb": None, "roe": None, "roa": None,
        "eps": None, "bvps": None, "net_margin": None,
        "debt_equity": None, "source": "vietstock",
        "updated_at": datetime.now().isoformat(),
    }

    if html is None:
        result["error"] = "Failed to fetch Vietstock"
        return result

    try:
        soup = BeautifulSoup(html, "lxml")

        # Tìm bảng tài chính — Vietstock có bảng với class "table" trong section tài chính
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = cells[0].get_text(strip=True).upper()
                val_text = cells[1].get_text(strip=True)

                if "P/E" in label:
                    result["pe"] = _safe_float(val_text)
                elif "P/B" in label:
                    result["pb"] = _safe_float(val_text)
                elif "ROE" in label:
                    result["roe"] = _safe_float(val_text)
                elif "ROA" in label:
                    result["roa"] = _safe_float(val_text)
                elif "EPS" in label:
                    result["eps"] = _safe_float(val_text)
                elif "BVPS" in label or "GIÁ TRỊ SỔ SÁCH" in label:
                    result["bvps"] = _safe_float(val_text)
                elif "LỢI NHUẬN RÒNG/DOANH THU" in label or "NET MARGIN" in label:
                    result["net_margin"] = _safe_float(val_text)
                elif "NỢ/VỐN" in label or "DEBT/EQUITY" in label:
                    result["debt_equity"] = _safe_float(val_text)

    except Exception as e:
        logger.warning("parse financial ratios %s: %s", symbol, e)
        result["error"] = str(e)

    cache.set(cache_key, result, ttl_type="financial")
    return result


async def get_income_statement(symbol: str, num_quarters: int = 8) -> list[dict[str, Any]]:
    """
    Lấy income statement theo quý: Doanh thu, Lãi gộp, Lãi ròng.

    Returns:
        [{"period": "Q4/2025", "revenue": 12_500_000, "gross_profit": 4_200_000,
          "net_profit": 2_100_000, "yoy_growth": 8.5}, ...]
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"vs:income:{symbol}:{num_quarters}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/{symbol}/bao-cao-tai-chinh.htm"
    html = await _fetch_html(url)

    if html is None:
        return []

    results: list[dict[str, Any]] = []
    try:
        soup = BeautifulSoup(html, "lxml")
        # Tìm section KQKD (Kết quả kinh doanh)
        tables = soup.find_all("table")
        for table in tables:
            header_row = table.find("tr")
            if not header_row:
                continue
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            # Kiểm tra bảng KQKD
            if not any("DOANH THU" in h.upper() or "REVENUE" in h.upper() for h in headers):
                continue

            rows = table.find_all("tr")[1:]  # skip header
            for row in rows[:num_quarters]:
                cells = row.find_all("td")
                if not cells:
                    continue
                entry: dict[str, Any] = {
                    "period": cells[0].get_text(strip=True) if cells else None,
                    "revenue": _safe_float(cells[1].get_text(strip=True)) if len(cells) > 1 else None,
                    "gross_profit": _safe_float(cells[2].get_text(strip=True)) if len(cells) > 2 else None,
                    "net_profit": _safe_float(cells[3].get_text(strip=True)) if len(cells) > 3 else None,
                    "yoy_growth": None,
                    "source": "vietstock",
                }
                results.append(entry)
            break

    except Exception as e:
        logger.warning("parse income statement %s: %s", symbol, e)

    cache.set(cache_key, results, ttl_type="financial")
    return results


async def get_balance_sheet(symbol: str, num_quarters: int = 4) -> list[dict[str, Any]]:
    """
    Lấy balance sheet: Tổng tài sản, Nợ, Vốn chủ sở hữu.

    Returns:
        [{"period": "Q4/2025", "total_assets": x, "total_liabilities": x,
          "equity": x, "cash": x}, ...]
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"vs:balance:{symbol}:{num_quarters}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/{symbol}/bao-cao-tai-chinh.htm"
    html = await _fetch_html(url)

    if html is None:
        return []

    results: list[dict[str, Any]] = []
    try:
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")
        for table in tables:
            header_row = table.find("tr")
            if not header_row:
                continue
            headers_text = header_row.get_text(strip=True).upper()
            if not any(kw in headers_text for kw in ["TỔNG TÀI SẢN", "TOTAL ASSET", "NỢ PHẢI TRẢ"]):
                continue

            rows = table.find_all("tr")[1:]
            for row in rows[:num_quarters]:
                cells = row.find_all("td")
                if not cells:
                    continue
                entry: dict[str, Any] = {
                    "period": cells[0].get_text(strip=True) if cells else None,
                    "total_assets": _safe_float(cells[1].get_text(strip=True)) if len(cells) > 1 else None,
                    "total_liabilities": _safe_float(cells[2].get_text(strip=True)) if len(cells) > 2 else None,
                    "equity": _safe_float(cells[3].get_text(strip=True)) if len(cells) > 3 else None,
                    "cash": None,
                    "source": "vietstock",
                }
                results.append(entry)
            break

    except Exception as e:
        logger.warning("parse balance sheet %s: %s", symbol, e)

    cache.set(cache_key, results, ttl_type="financial")
    return results


async def get_company_info(symbol: str) -> dict[str, Any]:
    """
    Lấy thông tin cơ bản công ty: tên, ngành ICB, sàn, vốn điều lệ, website.

    Returns:
        {
            "symbol": "VNM",
            "name": "Công ty CP Sữa Việt Nam",
            "exchange": "HOSE",
            "industry": "Food & Beverage",
            "icb_code": "3577",
            "charter_capital_bn": 17416.9,
            "website": "https://www.vinamilk.com.vn",
            "founded": "1976",
            "source": "vietstock"
        }
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"vs:info:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/{symbol}/co-ban.htm"
    html = await _fetch_html(url)

    result: dict[str, Any] = {
        "symbol": symbol,
        "name": None, "exchange": None, "industry": None,
        "icb_code": None, "charter_capital_bn": None,
        "website": None, "founded": None,
        "source": "vietstock",
    }

    if html is None:
        result["error"] = "Failed to fetch company info"
        return result

    try:
        soup = BeautifulSoup(html, "lxml")
        # Tìm bảng thông tin cơ bản
        info_items = soup.find_all(["tr", "div", "li"], limit=100)
        for item in info_items:
            text = item.get_text(separator=" ", strip=True)
            if "Tên công ty" in text or "Company Name" in text:
                cells = item.find_all(["td", "dd", "span"])
                if len(cells) >= 2:
                    result["name"] = cells[-1].get_text(strip=True)
            elif "Sàn giao dịch" in text or "Exchange" in text:
                cells = item.find_all(["td", "dd"])
                if len(cells) >= 2:
                    result["exchange"] = cells[-1].get_text(strip=True)
            elif "Ngành" in text and result["industry"] is None:
                cells = item.find_all(["td", "dd"])
                if len(cells) >= 2:
                    result["industry"] = cells[-1].get_text(strip=True)
            elif "Website" in text:
                link = item.find("a")
                if link:
                    result["website"] = link.get("href") or link.get_text(strip=True)
            elif "Năm thành lập" in text or "Founded" in text:
                cells = item.find_all(["td", "dd"])
                if len(cells) >= 2:
                    result["founded"] = cells[-1].get_text(strip=True)

        # Lấy tên từ title nếu chưa có
        if not result["name"]:
            title = soup.find("h1") or soup.find("h2")
            if title:
                result["name"] = title.get_text(strip=True)

    except Exception as e:
        logger.warning("parse company info %s: %s", symbol, e)
        result["error"] = str(e)

    cache.set(cache_key, result, ttl_type="financial")
    return result


async def get_stock_news(symbol: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Lấy tin tức theo mã từ Vietstock.

    Returns:
        [{"title": "...", "url": "...", "date": "...", "source": "vietstock"}, ...]
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"vs:news:{symbol}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{NEWS_URL}/{symbol.lower()}/tin-tuc.htm"
    html = await _fetch_html(url)

    results: list[dict[str, Any]] = []
    if html is None:
        return results

    try:
        soup = BeautifulSoup(html, "lxml")
        # Tìm các article/news items
        news_items = soup.find_all(["article", "div"], class_=re.compile(r"news|article|item", re.I), limit=50)
        if not news_items:
            # Fallback: tìm các link tin tức
            news_items = soup.find_all("li", limit=50)

        for item in news_items[:limit]:
            link = item.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            href = link["href"]
            if not href.startswith("http"):
                href = f"https://vietstock.vn{href}"

            # Tìm ngày
            date_el = item.find(["time", "span", "div"], class_=re.compile(r"date|time", re.I))
            date_text = date_el.get_text(strip=True) if date_el else None

            results.append({
                "title": title,
                "url": href,
                "date": _parse_vn_date(date_text),
                "source": "vietstock",
            })

    except Exception as e:
        logger.warning("parse stock news %s: %s", symbol, e)

    if results:
        cache.set(cache_key, results, ttl_type="news")
    return results


async def get_insider_trades(symbol: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Lấy giao dịch nội bộ (cổ đông lớn / lãnh đạo) từ Vietstock.

    Nguồn: Vietstock disclosure page — công bố theo quy định UBCKNN.

    Returns:
        [
            {
                "date": "2026-03-15",
                "person": "Nguyễn Văn A",
                "title": "Chủ tịch HĐQT",
                "action": "Mua",
                "qty": 100000,
                "price": 75000,
                "after_qty": 2500000,
            },
            ...
        ]
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"vs:insider:{symbol}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Thử endpoint Vietstock cho giao dịch nội bộ
    url = f"{BASE_URL}/data/getinsidertransaction?code={symbol}&type=0&page=1&pageSize={limit}"

    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            await asyncio.sleep(random.uniform(*REQUEST_DELAY_RANGE))
            resp = await client.get(url)
            if resp.status_code == 200:
                try:
                    json_data = resp.json()
                    items = json_data if isinstance(json_data, list) else json_data.get("data", [])
                    for item in items[:limit]:
                        results.append({
                            "date": str(item.get("TransactionDate", item.get("date", "")))[:10],
                            "person": str(item.get("OwnerName", item.get("person", ""))),
                            "title": str(item.get("OwnerTitle", item.get("title", ""))),
                            "action": str(item.get("TransactionType", item.get("action", ""))),
                            "qty": item.get("Quantity", item.get("qty")),
                            "price": item.get("Price", item.get("price")),
                            "after_qty": item.get("VolumeAfter", item.get("after_qty")),
                        })
                except Exception:
                    # Fallback: parse HTML nếu API không trả JSON
                    pass

        # Fallback: scrape trang HTML giao dịch nội bộ
        if not results:
            page_url = f"{BASE_URL}/{symbol.lower()}/giao-dich-noi-bo.htm"
            html = await _fetch_html(page_url)
            if html:
                soup = BeautifulSoup(html, "lxml")
                table = soup.find("table", class_=re.compile(r"insider|transaction|giao-dich", re.I))
                if table:
                    rows = table.find_all("tr")[1:]  # skip header
                    for row in rows[:limit]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 4:
                            results.append({
                                "date": cells[0].get_text(strip=True),
                                "person": cells[1].get_text(strip=True),
                                "title": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                                "action": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                                "qty": None,
                                "price": None,
                                "after_qty": None,
                            })

    except Exception as e:
        logger.warning("get_insider_trades(%s) failed: %s", symbol, e)

    if results:
        cache.set(cache_key, results, ttl_type="financial")
    return results

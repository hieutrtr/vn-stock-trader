"""
news_scraper.py — Scraper tin tức thị trường chứng khoán Việt Nam.

Nguồn: CafeF, Vietstock, VNExpress
Không phụ thuộc vào mã cụ thể — lấy tin thị trường chung.
Cache TTL: 10 phút (news).
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

REQUEST_DELAY_RANGE = (0.8, 2.0)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Referer": "https://cafef.vn/",
}

NEWS_SOURCES = {
    "cafef_market": {
        "url": "https://cafef.vn/thi-truong-chung-khoan.chn",
        "category": "market",
        "source": "cafef",
    },
    "cafef_company": {
        "url": "https://cafef.vn/doanh-nghiep.chn",
        "category": "company",
        "source": "cafef",
    },
    "vietstock_market": {
        "url": "https://vietstock.vn/thi-truong/tin-thi-truong.htm",
        "category": "market",
        "source": "vietstock",
    },
    "vnexpress_biz": {
        "url": "https://vnexpress.net/kinh-doanh/chung-khoan",
        "category": "market",
        "source": "vnexpress",
    },
}

# Từ điển false positive — không phải mã cổ phiếu
_FALSE_POSITIVES = {
    # Tiền tệ
    "VND", "USD", "EUR", "JPY", "CNY", "GBP", "AUD", "CHF", "SGD", "HKD",
    # Chỉ số kinh tế
    "GDP", "CPI", "PPI", "PMI", "GNP", "FDI", "ODA", "FII",
    # Chỉ số tài chính
    "ROE", "ROA", "EPS", "NAV", "NPL", "NIM", "CAR",
    # Viết tắt phổ biến
    "IPO", "ETF", "OTC", "MBO", "MBS", "NFI",
    "IMF", "WTO", "ADB", "WB", "ASEAN",
    "HOSE", "HNX", "UPC", "SSC", "MOF",
    "TGX", "HCM", "HN", "TP", "BC",
    # Tỷ lệ / đơn vị
    "PE", "PB", "PS", "EV", "EBIT", "EBITDA",
    "NII", "COF", "LTV", "LDR", "NPM",
    # Thương hiệu / tên chung
    "CEO", "CFO", "COO", "CTO",
    "IFC", "ICC", "ISO",
    # Tiếng Việt viết tắt
    "TTCK", "DNNN", "KTXH", "NHNN", "UBCK", "TPCP",
}

# Pattern mã chứng khoán VN: 2-5 ký tự IN HOA
_SYMBOL_PATTERN = re.compile(r"\b([A-Z]{2,5})\b")

# Danh sách mã VN-index 30 để whitelist (sẽ được cập nhật)
_KNOWN_SYMBOLS = {
    "VNM", "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HPG",
    "FPT", "VHM", "VIC", "GAS", "SAB", "MSN", "PLX", "POW", "BCM",
    "HDB", "LPB", "SHB", "SSI", "VND", "HCM", "BSR", "PNJ", "NKG",
    "HSG", "VNS", "KDH", "REE", "PHR", "GVR", "DCM", "DGC", "HAG",
    "IDC", "KBC", "NLG", "PDR", "DXG", "DPM",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _fetch_html(url: str, timeout: int = 15) -> str | None:
    """Async fetch với delay và error handling."""
    delay = random.uniform(*REQUEST_DELAY_RANGE)
    await asyncio.sleep(delay)

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.warning("Fetch failed %s: %s", url, e)
        return None


def _parse_date(text: str | None) -> str | None:
    """Parse ngày Việt Nam/ISO."""
    if not text:
        return None
    text = text.strip()
    for fmt in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return text


def _parse_cafef_news(html: str, source_key: str) -> list[dict[str, Any]]:
    """Parse tin từ CafeF."""
    config = NEWS_SOURCES[source_key]
    soup = BeautifulSoup(html, "lxml")
    results = []

    # CafeF dùng class "item" hoặc "news-item" cho mỗi tin
    items = soup.find_all(["article", "div", "li"], class_=re.compile(r"item|news|article", re.I), limit=60)

    for item in items:
        link = item.find("a", href=re.compile(r"cafef\.vn.*\.chn"))
        if not link:
            link = item.find("a", href=True)
        if not link:
            continue

        title = link.get("title") or link.get_text(strip=True)
        if not title or len(title) < 15:
            continue

        href = link["href"]
        if not href.startswith("http"):
            href = "https://cafef.vn" + href

        # Tìm summary
        summary_el = item.find(["p", "div"], class_=re.compile(r"sapo|summary|desc|content", re.I))
        summary = summary_el.get_text(strip=True) if summary_el else ""

        # Tìm ngày
        date_el = item.find(["time", "span"], class_=re.compile(r"date|time|post", re.I))
        date_text = None
        if date_el:
            date_text = date_el.get("datetime") or date_el.get_text(strip=True)

        results.append({
            "title": title,
            "url": href,
            "summary": summary[:300] if summary else "",
            "published_at": _parse_date(date_text),
            "source": config["source"],
            "symbols_mentioned": extract_symbols_from_text(f"{title} {summary}"),
            "category": config["category"],
        })

    return results


def _parse_vietstock_news(html: str) -> list[dict[str, Any]]:
    """Parse tin từ Vietstock."""
    config = NEWS_SOURCES["vietstock_market"]
    soup = BeautifulSoup(html, "lxml")
    results = []

    items = soup.find_all(["article", "div", "li"], class_=re.compile(r"news|article|item|post", re.I), limit=60)
    for item in items:
        link = item.find("a", href=re.compile(r"vietstock\.vn", re.I))
        if not link:
            link = item.find("a", href=True)
        if not link:
            continue

        title = link.get("title") or link.get_text(strip=True)
        if not title or len(title) < 15:
            continue

        href = link["href"]
        if not href.startswith("http"):
            href = "https://vietstock.vn" + href

        date_el = item.find(["time", "span"], class_=re.compile(r"date|time", re.I))
        date_text = date_el.get("datetime") or date_el.get_text(strip=True) if date_el else None

        summary_el = item.find(["p", "div"], class_=re.compile(r"desc|summary|sapo", re.I))
        summary = summary_el.get_text(strip=True)[:300] if summary_el else ""

        results.append({
            "title": title,
            "url": href,
            "summary": summary,
            "published_at": _parse_date(date_text),
            "source": config["source"],
            "symbols_mentioned": extract_symbols_from_text(f"{title} {summary}"),
            "category": config["category"],
        })

    return results


def _parse_vnexpress_news(html: str) -> list[dict[str, Any]]:
    """Parse tin từ VNExpress."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    items = soup.find_all(["article", "div"], class_=re.compile(r"item-news|article-item|box-item", re.I), limit=40)
    for item in items:
        link = item.find("a", href=re.compile(r"vnexpress\.net", re.I))
        if not link:
            link = item.find("h3", class_=re.compile(r"title", re.I))
            if link:
                link = link.find("a")
        if not link:
            continue

        title = link.get("title") or link.get_text(strip=True)
        if not title or len(title) < 15:
            continue

        href = link.get("href", "")
        if not href.startswith("http"):
            href = "https://vnexpress.net" + href

        date_el = item.find(["span", "time"], class_=re.compile(r"time|date", re.I))
        date_text = date_el.get("datetime") or date_el.get_text(strip=True) if date_el else None

        desc_el = item.find("p", class_=re.compile(r"description|desc", re.I))
        summary = desc_el.get_text(strip=True)[:300] if desc_el else ""

        results.append({
            "title": title,
            "url": href,
            "summary": summary,
            "published_at": _parse_date(date_text),
            "source": "vnexpress",
            "symbols_mentioned": extract_symbols_from_text(f"{title} {summary}"),
            "category": "market",
        })

    return results


# ─── Public Functions ─────────────────────────────────────────────────────────


def extract_symbols_from_text(text: str) -> list[str]:
    """
    Tìm mã chứng khoán trong text.

    Logic:
    1. Tìm tất cả chuỗi 2-5 ký tự in hoa.
    2. Loại bỏ false positives (_FALSE_POSITIVES).
    3. Ưu tiên _KNOWN_SYMBOLS.

    Returns:
        List mã không trùng lặp, tối đa 10 mã.
    """
    if not text:
        return []

    matches = _SYMBOL_PATTERN.findall(text)
    seen: set[str] = set()
    symbols: list[str] = []

    for m in matches:
        if m in seen:
            continue
        if m in _FALSE_POSITIVES:
            continue
        # Bỏ qua 2 ký tự nếu không trong known list (tránh false positive)
        if len(m) == 2 and m not in _KNOWN_SYMBOLS:
            continue
        seen.add(m)
        symbols.append(m)
        if len(symbols) >= 10:
            break

    return symbols


async def get_market_news(limit: int = 30) -> list[dict[str, Any]]:
    """
    Lấy tin tức thị trường từ tất cả nguồn.

    Returns:
        [{"title": "...", "url": "...", "summary": "...",
          "published_at": "...", "source": "cafef",
          "symbols_mentioned": ["VNM"], "category": "market"}, ...]
    """
    cache = get_cache()
    cache_key = f"news:market:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Fetch tất cả nguồn song song
    tasks = [
        ("cafef_market", _fetch_html(NEWS_SOURCES["cafef_market"]["url"])),
        ("cafef_company", _fetch_html(NEWS_SOURCES["cafef_company"]["url"])),
        ("vietstock_market", _fetch_html(NEWS_SOURCES["vietstock_market"]["url"])),
        ("vnexpress_biz", _fetch_html(NEWS_SOURCES["vnexpress_biz"]["url"])),
    ]

    htmls = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

    all_news: list[dict[str, Any]] = []

    # Parse từng nguồn
    source_keys = [t[0] for t in tasks]
    for key, html in zip(source_keys, htmls):
        if isinstance(html, Exception) or html is None:
            continue
        try:
            if key.startswith("cafef"):
                news = _parse_cafef_news(html, key)
            elif key == "vietstock_market":
                news = _parse_vietstock_news(html)
            elif key == "vnexpress_biz":
                news = _parse_vnexpress_news(html)
            else:
                news = []
            all_news.extend(news)
        except Exception as e:
            logger.warning("Parse news %s failed: %s", key, e)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_news: list[dict[str, Any]] = []
    for item in all_news:
        url = item.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)

    # Sắp xếp theo ngày (mới nhất trước)
    def sort_key(item: dict) -> str:
        return item.get("published_at") or ""

    unique_news.sort(key=sort_key, reverse=True)
    result = unique_news[:limit]

    if result:
        cache.set(cache_key, result, ttl_type="news")
    return result


async def get_news_by_symbol(symbol: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Lấy tin có đề cập đến mã cổ phiếu cụ thể.

    Returns:
        List tin tức lọc theo symbol, tối đa `limit` bài.
    """
    symbol = symbol.upper().strip()
    cache = get_cache()
    cache_key = f"news:symbol:{symbol}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Lấy toàn bộ tin rồi lọc
    all_news = await get_market_news(limit=100)
    filtered = [
        item for item in all_news
        if symbol in item.get("symbols_mentioned", [])
        or symbol in item.get("title", "").upper()
    ]

    result = filtered[:limit]
    if result:
        cache.set(cache_key, result, ttl_type="news")
    return result

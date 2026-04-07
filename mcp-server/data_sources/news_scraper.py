"""
news_scraper.py — Scraper tin tức thị trường chứng khoán Việt Nam.

Nguồn: CafeF, Vietstock, VNExpress, NDH, HOSE, HNX, SSC, FireAnt
Không phụ thuộc vào mã cụ thể — lấy tin thị trường chung.
Cache TTL: 10 phút (news).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import json

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
    "ndh_market": {
        "url": "https://tinnhanhchungkhoan.vn/chung-khoan/",
        "category": "market",
        "source": "tinnhanhchungkhoan",
    },
    "hose_market": {
        "url": "https://www.hsx.vn/Modules/Cms/Web/NewsByCat/dca0933e-a578-4eaf-8b29-beb4575052c9",
        "category": "market",
        "source": "hose",
    },
    "hnx_market": {
        "url": "https://www.hnx.vn/tin-tuc-su-kien-ttcbhnx.html",
        "category": "market",
        "source": "hnx",
    },
    "ssc_market": {
        "url": "https://baodautu.vn/dau-tu-tai-chinh-d6/",
        "category": "market",
        "source": "baodautu",
    },
    "fireant_market": {
        "url": "https://fireant.vn/",
        "category": "market",
        "source": "fireant",
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


async def _fetch_html(
    url: str,
    timeout: int = 15,
    extra_headers: dict | None = None,
    verify_ssl: bool = True,
) -> str | None:
    """Async fetch với delay và error handling."""
    delay = random.uniform(*REQUEST_DELAY_RANGE)
    await asyncio.sleep(delay)

    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)

    try:
        async with httpx.AsyncClient(
            headers=headers, timeout=timeout, follow_redirects=True, verify=verify_ssl
        ) as client:
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
            "title_hash": _title_hash(title),
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
            "title_hash": _title_hash(title),
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
            "title_hash": _title_hash(title),
            "url": href,
            "summary": summary,
            "published_at": _parse_date(date_text),
            "source": "vnexpress",
            "symbols_mentioned": extract_symbols_from_text(f"{title} {summary}"),
            "category": "market",
        })

    return results


def _parse_ndh_news(html: str) -> list[dict[str, Any]]:
    """Parse tin từ Tin Nhanh Chứng Khoán (tinnhanhchungkhoan.vn).

    NDH (ndh.vn) đã ngừng hoạt động (domain không phân giải được).
    Thay thế bằng tinnhanhchungkhoan.vn — báo chứng khoán chuyên biệt.

    URL pattern bài viết: https://www.tinnhanhchungkhoan.vn/<slug>-post<id>.html
    """
    config = NEWS_SOURCES["ndh_market"]
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Tìm tất cả link bài viết — URL có dạng .../...-post<id>...
    article_link_pattern = re.compile(r"tinnhanhchungkhoan\.vn/.+-post\d+", re.I)
    seen_hrefs: set[str] = set()

    for link in soup.find_all("a", href=article_link_pattern):
        href = link.get("href", "")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        title = link.get("title") or link.get_text(strip=True)
        if not title or len(title) < 15:
            continue

        if not href.startswith("http"):
            href = "https://www.tinnhanhchungkhoan.vn" + href

        # Tìm ngày trong các phần tử cha gần nhất
        date_text = None
        container = link.parent
        for _ in range(4):
            if container is None:
                break
            date_el = container.find(
                ["time", "span"], class_=re.compile(r"date|time|ngay", re.I)
            )
            if date_el:
                date_text = date_el.get("datetime") or date_el.get_text(strip=True)
                break
            container = container.parent

        results.append({
            "title": title,
            "title_hash": _title_hash(title),
            "url": href,
            "summary": "",
            "published_at": _parse_date(date_text),
            "source": config["source"],
            "symbols_mentioned": extract_symbols_from_text(title),
            "category": config["category"],
        })
        if len(results) >= 30:
            break

    return results


def _parse_hose_news(html: str) -> list[dict[str, Any]]:
    """Parse tin từ HOSE (Sở Giao dịch Chứng khoán TP.HCM)."""
    config = NEWS_SOURCES["hose_market"]
    soup = BeautifulSoup(html, "lxml")
    results = []

    # HOSE CMS thường render dạng bảng hoặc danh sách với các thẻ a + tiêu đề
    # Tìm các thẻ a có href trỏ về hsx.vn hoặc link bài viết
    link_patterns = [
        re.compile(r"hsx\.vn", re.I),
        re.compile(r"/Modules/Cms/", re.I),
        re.compile(r"newsdetail|tin-tuc|detail", re.I),
    ]

    # Thử tìm các item dạng row/cell trước
    rows = soup.find_all(["tr", "div", "li"], class_=re.compile(r"row|item|news|article", re.I), limit=60)
    if not rows:
        rows = soup.find_all(["tr", "div", "li"], limit=200)

    seen_hrefs: set[str] = set()
    for row in rows:
        link = None
        for pattern in link_patterns:
            link = row.find("a", href=pattern)
            if link:
                break
        if not link:
            link = row.find("a", href=True)
        if not link:
            continue

        href = link.get("href", "")
        if not href or href in seen_hrefs:
            continue
        if not href.startswith("http"):
            href = "https://www.hsx.vn" + href
        seen_hrefs.add(href)

        title = link.get("title") or link.get_text(strip=True)
        if not title or len(title) < 10:
            # Tìm tiêu đề trong các thẻ con của row
            heading = row.find(["h2", "h3", "h4", "strong", "b"])
            title = heading.get_text(strip=True) if heading else ""
        if not title or len(title) < 10:
            continue

        date_el = row.find(["time", "span", "td"], class_=re.compile(r"date|time", re.I))
        date_text = None
        if date_el:
            date_text = date_el.get("datetime") or date_el.get_text(strip=True)

        results.append({
            "title": title,
            "title_hash": _title_hash(title),
            "url": href,
            "summary": "",
            "published_at": _parse_date(date_text),
            "source": config["source"],
            "symbols_mentioned": extract_symbols_from_text(title),
            "category": config["category"],
        })
        if len(results) >= 30:
            break

    return results


def _parse_hnx_news(html: str) -> list[dict[str, Any]]:
    """Parse tin từ HNX (Sở Giao dịch Chứng khoán Hà Nội).

    HNX dùng URL pattern: /chi-tiet-su-kien-<id>-<num>-hnx.html
    """
    config = NEWS_SOURCES["hnx_market"]
    soup = BeautifulSoup(html, "lxml")
    results = []

    # HNX news links match pattern: /chi-tiet-su-kien-\d+-\d+-hnx.html
    news_link_pattern = re.compile(r"/chi-tiet-su-kien-\d+-\d+-hnx\.html", re.I)

    seen_hrefs: set[str] = set()
    links = soup.find_all("a", href=news_link_pattern)

    for link in links:
        href = link.get("href", "")
        if not href or href in seen_hrefs:
            continue
        if not href.startswith("http"):
            href = "https://www.hnx.vn" + href
        seen_hrefs.add(href)

        title = link.get("title") or link.get_text(strip=True)
        if not title or len(title) < 10:
            # Check parent element for title
            parent = link.parent
            if parent:
                heading = parent.find(["h2", "h3", "h4", "strong"])
                title = heading.get_text(strip=True) if heading else ""
        if not title or len(title) < 10:
            continue

        # Find date in nearby elements
        container = link.parent or link
        date_el = container.find(["time", "span"], class_=re.compile(r"date|time|ngay", re.I))
        date_text = None
        if date_el:
            date_text = date_el.get("datetime") or date_el.get_text(strip=True)

        summary_el = container.find(["p", "div"], class_=re.compile(r"desc|summary|sapo|excerpt|intro", re.I))
        summary = summary_el.get_text(strip=True)[:300] if summary_el else ""

        results.append({
            "title": title,
            "title_hash": _title_hash(title),
            "url": href,
            "summary": summary,
            "published_at": _parse_date(date_text),
            "source": config["source"],
            "symbols_mentioned": extract_symbols_from_text(f"{title} {summary}"),
            "category": config["category"],
        })
        if len(results) >= 30:
            break

    return results


def _parse_ssc_news(html: str) -> list[dict[str, Any]]:
    """Parse tin từ Báo Đầu tư (baodautu.vn) — mục Đầu tư tài chính.

    SSC (ssc.gov.vn) không còn scrape được: trang dùng Oracle ADF render
    bằng JavaScript và có vòng lặp redirect HTTPS→HTTP:80→HTTPS bất tận.
    Thay thế bằng baodautu.vn (Báo Đầu tư) — cơ quan báo chí chính thức của
    Bộ Kế hoạch và Đầu tư, chuyên về tài chính và chứng khoán.

    URL pattern bài viết: https://baodautu.vn/<slug>-d<6+ chữ số>.html
    """
    config = NEWS_SOURCES["ssc_market"]
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Bài viết baodautu có ID dạng -d<6+ chữ số> trước .html
    article_link_pattern = re.compile(r"baodautu\.vn/.+-d\d{5,}\.html", re.I)
    seen_hrefs: set[str] = set()

    for link in soup.find_all("a", href=article_link_pattern):
        href = link.get("href", "")
        if not href:
            continue

        title = link.get("title") or link.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        # Dedup after title check (each article appears twice — once with empty title)
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        if not href.startswith("http"):
            href = "https://baodautu.vn" + href

        # Tìm ngày trong các phần tử cha
        date_text = None
        container = link.parent
        for _ in range(4):
            if container is None:
                break
            date_el = container.find(
                ["time", "span", "p"],
                class_=re.compile(r"date|time|ngay|publish", re.I),
            )
            if date_el:
                date_text = date_el.get("datetime") or date_el.get_text(strip=True)
                break
            container = container.parent

        results.append({
            "title": title,
            "title_hash": _title_hash(title),
            "url": href,
            "summary": "",
            "published_at": _parse_date(date_text),
            "source": config["source"],
            "symbols_mentioned": extract_symbols_from_text(title),
            "category": config["category"],
        })
        if len(results) >= 30:
            break

    return results


def _parse_fireant_news(html: str) -> list[dict[str, Any]]:
    """Parse tin từ FireAnt via __NEXT_DATA__ JSON embedded in page.

    FireAnt là Next.js SPA — tin tức nằm trong thẻ <script id="__NEXT_DATA__">
    tại path: props.pageProps.initialState.posts.posts.NEWS_STREAM.posts
    """
    config = NEWS_SOURCES["fireant_market"]
    soup = BeautifulSoup(html, "lxml")
    results = []

    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return results

    try:
        data = json.loads(script.string)
    except (json.JSONDecodeError, TypeError):
        return results

    try:
        posts = (
            data["props"]["pageProps"]["initialState"]["posts"]["posts"]
            .get("NEWS_STREAM", {})
            .get("posts", [])
        )
    except (KeyError, TypeError):
        return results

    for post in posts:
        title = post.get("title", "")
        if not title or len(title) < 10:
            continue

        post_id = post.get("postID", "")
        # FireAnt article URL pattern: /bai-viet/<uuid>/<postID>
        # We can construct a usable URL from postID
        url = f"https://fireant.vn/bai-viet/{post_id}" if post_id else ""

        description = post.get("description", "") or ""
        date_str = post.get("date", "")

        # Parse date — FireAnt uses ISO format with timezone: 2026-04-07T10:00:00+07:00
        published_at = None
        if date_str:
            # Strip timezone offset for simpler parsing
            clean_date = re.sub(r"[+-]\d{2}:\d{2}$", "", date_str)
            published_at = _parse_date(clean_date)

        # Extract tagged symbols from FireAnt's structured data
        tagged_symbols = [
            s.get("symbol", "") for s in post.get("taggedSymbols", []) if s.get("symbol")
        ]
        # Also extract from title + description text
        text_symbols = extract_symbols_from_text(f"{title} {description}")
        # Merge, preserving order, no duplicates
        all_symbols = list(dict.fromkeys(tagged_symbols + text_symbols))[:10]

        results.append({
            "title": title,
            "title_hash": _title_hash(title),
            "url": url,
            "summary": description[:300] if description else "",
            "published_at": published_at,
            "source": config["source"],
            "symbols_mentioned": all_symbols,
            "category": config["category"],
        })

        if len(results) >= 30:
            break

    return results


# ─── Public Functions ─────────────────────────────────────────────────────────


def _title_hash(title: str) -> str:
    """MD5 hash của title lowercase-trimmed — dùng để dedup."""
    return hashlib.md5(title.lower().strip().encode()).hexdigest()


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

    # Fetch tất cả nguồn song song — một số nguồn cần Referer riêng
    tasks = [
        ("cafef_market", _fetch_html(NEWS_SOURCES["cafef_market"]["url"])),
        ("cafef_company", _fetch_html(NEWS_SOURCES["cafef_company"]["url"])),
        ("vietstock_market", _fetch_html(NEWS_SOURCES["vietstock_market"]["url"])),
        ("vnexpress_biz", _fetch_html(NEWS_SOURCES["vnexpress_biz"]["url"])),
        ("ndh_market", _fetch_html(
            NEWS_SOURCES["ndh_market"]["url"],
            extra_headers={"Referer": "https://tinnhanhchungkhoan.vn/"},
        )),
        ("hose_market", _fetch_html(
            NEWS_SOURCES["hose_market"]["url"],
            extra_headers={"Referer": "https://www.hsx.vn/"},
        )),
        ("hnx_market", _fetch_html(
            NEWS_SOURCES["hnx_market"]["url"],
            extra_headers={"Referer": "https://www.hnx.vn/"},
            verify_ssl=False,  # HNX có SSL cert không khớp issuer
        )),
        ("ssc_market", _fetch_html(
            NEWS_SOURCES["ssc_market"]["url"],
            extra_headers={"Referer": "https://baodautu.vn/"},
        )),
        ("fireant_market", _fetch_html(
            NEWS_SOURCES["fireant_market"]["url"],
            extra_headers={"Referer": "https://fireant.vn/"},
        )),
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
            elif key == "ndh_market":
                news = _parse_ndh_news(html)
            elif key == "hose_market":
                news = _parse_hose_news(html)
            elif key == "hnx_market":
                news = _parse_hnx_news(html)
            elif key == "ssc_market":
                news = _parse_ssc_news(html)
            elif key == "fireant_market":
                news = _parse_fireant_news(html)
            else:
                news = []
            all_news.extend(news)
        except Exception as e:
            logger.warning("Parse news %s failed: %s", key, e)

    # Deduplicate by URL and title hash (catches same article from multiple sources)
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    unique_news: list[dict[str, Any]] = []
    for item in all_news:
        url = item.get("url", "")
        th = item.get("title_hash") or _title_hash(item.get("title", ""))
        if url and url in seen_urls:
            continue
        if th and th in seen_hashes:
            continue
        if url:
            seen_urls.add(url)
        if th:
            seen_hashes.add(th)
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

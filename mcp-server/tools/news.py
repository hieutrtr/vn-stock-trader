"""
tools/news.py — MCP tool tin tức thị trường.

Tools:
  - get_news : Tin tức thị trường chứng khoán, filter theo mã hoặc category
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Đăng ký news tools vào FastMCP instance."""

    @mcp.tool()
    async def get_news(
        symbol: str = "",
        category: str = "market",
        limit: int = 10,
    ) -> str:
        """
        Get latest Vietnamese stock market news, optionally filtered by stock symbol.

        Sources: CafeF, Vietstock, VNExpress. News is cached for 10 minutes.

        Args:
            symbol: Stock ticker to filter news (e.g. "VNM"). Empty string = all market news.
            category: "market" (default) | "company" | "macro"
            limit: Number of articles to return (default 10, max 30)
        """
        from data_sources.news_scraper import get_market_news, get_news_by_symbol

        limit = max(1, min(30, limit))
        symbol = symbol.upper().strip()
        valid_categories = {"market", "company", "macro"}
        if category not in valid_categories:
            category = "market"

        # Lấy tin
        if symbol:
            articles = await get_news_by_symbol(symbol, limit=limit)
            title = f"📰 Tin tức — {symbol} (tìm kiếm trong {limit} tin gần nhất)"
        else:
            articles = await get_market_news(limit=limit)
            cat_labels = {
                "market": "Thị trường chứng khoán",
                "company": "Doanh nghiệp",
                "macro": "Kinh tế vĩ mô",
            }
            title = f"📰 Tin tức {cat_labels.get(category, category)} ({limit} tin gần nhất)"
            # Filter theo category nếu không filter theo symbol
            if category != "market":
                articles = [a for a in articles if a.get("category") == category][:limit]

        if not articles:
            if symbol:
                return f"⚠️ Không tìm thấy tin tức liên quan đến **{symbol}** trong các nguồn đang theo dõi."
            return "⚠️ Không lấy được tin tức. Có thể các nguồn tin đang bận hoặc không kết nối được."

        lines = [title, ""]

        for i, article in enumerate(articles, 1):
            art_title = article.get("title", "Không có tiêu đề")
            art_url = article.get("url", "")
            art_summary = article.get("summary", "")
            art_date = article.get("published_at", "")
            art_source = article.get("source", "")
            art_symbols = article.get("symbols_mentioned", [])

            # Format ngày
            date_str = ""
            if art_date:
                try:
                    from datetime import datetime
                    if "T" in art_date:
                        dt = datetime.fromisoformat(art_date)
                    else:
                        dt = datetime.strptime(art_date[:10], "%Y-%m-%d")
                    date_str = dt.strftime("%d/%m/%Y %H:%M") if "T" in art_date else dt.strftime("%d/%m/%Y")
                except Exception:
                    date_str = art_date[:16]

            # Source icon
            source_icons = {
                "cafef": "☕",
                "vietstock": "📊",
                "vnexpress": "📱",
            }
            source_icon = source_icons.get(art_source.lower(), "📄")

            # Build article block
            lines.append(f"**{i}. {art_title}**")
            meta_parts = []
            if date_str:
                meta_parts.append(date_str)
            if art_source:
                meta_parts.append(f"{source_icon} {art_source.upper()}")
            if art_symbols:
                meta_parts.append(f"Mã: {', '.join(art_symbols[:5])}")
            if meta_parts:
                lines.append(f"_{' | '.join(meta_parts)}_")
            if art_summary:
                # Truncate summary at 200 chars
                summary_display = art_summary[:200] + "..." if len(art_summary) > 200 else art_summary
                lines.append(summary_display)
            if art_url:
                lines.append(f"🔗 {art_url}")
            lines.append("")

        lines.append("_Cache 10 phút. Nguồn: CafeF, Vietstock, VNExpress_")
        return "\n".join(lines)

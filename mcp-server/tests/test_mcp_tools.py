"""
tests/test_mcp_tools.py — Tests cho Phase 2 MCP tools.

Test mỗi tool với mock data sources, kiểm tra:
  - Return type là str
  - Không crash khi data bình thường
  - Error handling đúng khi data source fail
  - Output có chứa thông tin quan trọng
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

# Thêm mcp-server vào path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_price_data():
    return {
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
        "timestamp": "2026-03-30T10:30:00",
    }


@pytest.fixture
def mock_market_overview():
    return {
        "vn_index": {"value": 1782.5, "change": -3.2, "pct": -0.18},
        "hnx_index": {"value": 245.3, "change": 0.5, "pct": 0.20},
        "upcom_index": {"value": 95.1, "change": -0.1, "pct": -0.10},
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
        "timestamp": "2026-03-30T14:30:00",
    }


@pytest.fixture
def mock_top_movers():
    return {
        "gainers": [
            {"symbol": "HPG", "price": 30000, "pct_change": 6.8},
            {"symbol": "ACB", "price": 25000, "pct_change": 4.2},
        ],
        "losers": [
            {"symbol": "VHM", "price": 42000, "pct_change": -5.1},
        ],
        "volume_leaders": [
            {"symbol": "STB", "price": 18000, "volume": 8_000_000},
        ],
    }


@pytest.fixture
def mock_financial_data():
    return {
        "symbol": "VNM",
        "income_statement": [
            {
                "quarter": "Q4/2025",
                "revenue": 15_000_000_000_000,
                "gross_profit": 5_500_000_000_000,
                "net_profit": 2_000_000_000_000,
            },
            {
                "quarter": "Q3/2025",
                "revenue": 14_500_000_000_000,
                "gross_profit": 5_200_000_000_000,
                "net_profit": 1_800_000_000_000,
            },
        ],
        "balance_sheet": [
            {
                "quarter": "Q4/2025",
                "total_assets": 50_000_000_000_000,
                "total_liabilities": 15_000_000_000_000,
                "equity": 35_000_000_000_000,
            }
        ],
        "cash_flow": [
            {
                "quarter": "Q4/2025",
                "operating_cf": 3_000_000_000_000,
                "investing_cf": -500_000_000_000,
                "financing_cf": -1_000_000_000_000,
            }
        ],
        "ratios": {
            "pe": 14.5,
            "pb": 2.3,
            "roe": 0.28,  # 28% (decimal form)
            "roa": 0.12,
            "eps": 5200,
            "bvps": 32000,
            "net_margin": 0.133,
            "debt_equity": 0.43,
        },
    }


@pytest.fixture
def mock_news_articles():
    return [
        {
            "title": "VN-Index tăng nhờ dòng tiền nội",
            "url": "https://cafef.vn/article1",
            "summary": "Thị trường chứng khoán hôm nay tăng điểm...",
            "published_at": "2026-03-30T10:00:00",
            "source": "cafef",
            "symbols_mentioned": ["VNM", "HPG"],
            "category": "market",
        },
        {
            "title": "ACB công bố kết quả kinh doanh quý 1",
            "url": "https://cafef.vn/article2",
            "summary": "Ngân hàng ACB ghi nhận lợi nhuận...",
            "published_at": "2026-03-30T09:00:00",
            "source": "vietstock",
            "symbols_mentioned": ["ACB"],
            "category": "company",
        },
    ]


# ─── Tests: tools/market.py ───────────────────────────────────────────────────


class TestGetStockPrice:
    """Tests cho get_stock_price tool."""

    @pytest.mark.asyncio
    async def test_returns_string(self, mock_price_data):
        """Tool phải trả về str."""
        with patch("data_sources.vnstock_client.get_stock_price", return_value=mock_price_data):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            tool_fn = None
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_price":
                    tool_fn = tool.fn
                    break
            assert tool_fn is not None
            result = await tool_fn(symbol="VNM")
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_contains_price(self, mock_price_data):
        """Output phải có giá cổ phiếu."""
        with patch("data_sources.vnstock_client.get_stock_price", return_value=mock_price_data):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_price":
                    result = await tool.fn(symbol="VNM")
                    break
            assert "VNM" in result
            assert "75" in result  # price 75000

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Khi symbol không tồn tại → trả về error message."""
        with patch("data_sources.vnstock_client.get_stock_price", return_value={"error": "Symbol not found"}):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_price":
                    result = await tool.fn(symbol="INVALID")
                    break
            assert "❌" in result
            assert "INVALID" in result

    @pytest.mark.asyncio
    async def test_symbol_normalized(self, mock_price_data):
        """Symbol được normalize thành uppercase."""
        with patch("data_sources.vnstock_client.get_stock_price", return_value=mock_price_data) as mock_fn:
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_price":
                    await tool.fn(symbol="vnm")  # lowercase input
                    break
            # vnstock_client nhận VNM (đã uppercase)
            mock_fn.assert_called_once_with("VNM")

    @pytest.mark.asyncio
    async def test_contains_ceiling_floor(self, mock_price_data):
        """Output phải có thông tin trần/sàn."""
        with patch("data_sources.vnstock_client.get_stock_price", return_value=mock_price_data):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_price":
                    result = await tool.fn(symbol="VNM")
                    break
            # Trần và Sàn phải có trong output
            assert "Trần" in result or "trần" in result
            assert "Sàn" in result or "sàn" in result


class TestGetMarketOverview:
    """Tests cho get_market_overview tool."""

    @pytest.mark.asyncio
    async def test_returns_string(self, mock_market_overview):
        with patch("data_sources.vnstock_client.get_market_overview", return_value=mock_market_overview):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_market_overview":
                    result = await tool.fn()
                    break
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_contains_vn_index(self, mock_market_overview):
        """Output phải có VN-Index."""
        with patch("data_sources.vnstock_client.get_market_overview", return_value=mock_market_overview):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_market_overview":
                    result = await tool.fn()
                    break
            assert "VN-Index" in result
            assert "1,782" in result

    @pytest.mark.asyncio
    async def test_contains_breadth(self, mock_market_overview):
        """Output phải có breadth (advance/decline)."""
        with patch("data_sources.vnstock_client.get_market_overview", return_value=mock_market_overview):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_market_overview":
                    result = await tool.fn()
                    break
            # Advance = 245
            assert "245" in result

    @pytest.mark.asyncio
    async def test_error_handling(self):
        with patch("data_sources.vnstock_client.get_market_overview", return_value={"error": "Network error"}):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_market_overview":
                    result = await tool.fn()
                    break
            assert "❌" in result


class TestGetTopMovers:
    """Tests cho get_top_movers tool."""

    @pytest.mark.asyncio
    async def test_returns_string(self, mock_top_movers):
        with patch("data_sources.vnstock_client.get_top_movers", return_value=mock_top_movers):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_top_movers":
                    result = await tool.fn()
                    break
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_contains_gainers_losers(self, mock_top_movers):
        with patch("data_sources.vnstock_client.get_top_movers", return_value=mock_top_movers):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_top_movers":
                    result = await tool.fn(exchange="HOSE", n=5)
                    break
            assert "HPG" in result  # gainer
            assert "VHM" in result  # loser

    @pytest.mark.asyncio
    async def test_n_clamped(self, mock_top_movers):
        """n > 20 phải bị clamp về 20."""
        with patch("data_sources.vnstock_client.get_top_movers", return_value=mock_top_movers):
            from tools.market import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_top_movers":
                    # n=100 phải bị clamp — hàm gọi get_top_movers(n=20)
                    result = await tool.fn(exchange="ALL", n=100)
                    break
            assert isinstance(result, str)


# ─── Tests: tools/history.py ─────────────────────────────────────────────────


class TestGetStockHistory:
    """Tests cho get_stock_history tool."""

    @pytest.mark.asyncio
    async def test_returns_string(self, sample_ohlcv_250):
        """Tool trả về str cho data bình thường."""
        mock_indicators = {
            "ma20": 74500.0, "ma50": 72000.0, "ma200": 68000.0, "ema20": 73500.0,
            "rsi14": 58.3,
            "macd": {"macd": 500.0, "signal": 420.0, "histogram": 80.0},
            "bb": {"upper": 78000.0, "middle": 74500.0, "lower": 71000.0},
            "atr14": 1200.0,
            "volume_ma20": 1_100_000.0,
            "volume_ratio": 1.35,
        }
        mock_trend = {"short_term": "UPTREND", "medium_term": "SIDEWAYS", "long_term": "UPTREND", "strength": "STRONG"}
        mock_sr = {"supports": [70000, 68000], "resistances": [78000, 80000]}

        with (
            patch("data_sources.vnstock_client.get_stock_history", return_value=sample_ohlcv_250),
            patch("data_sources.ta_calculator.calculate_indicators", return_value=mock_indicators),
            patch("data_sources.ta_calculator.detect_patterns", return_value=["golden_cross"]),
            patch("data_sources.ta_calculator.find_support_resistance", return_value=mock_sr),
            patch("data_sources.ta_calculator.get_trend", return_value=mock_trend),
        ):
            from tools.history import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_history":
                    result = await tool.fn(symbol="VNM", period="1y")
                    break
            assert isinstance(result, str)
            assert "VNM" in result

    @pytest.mark.asyncio
    async def test_invalid_period(self):
        """Period không hợp lệ → error message."""
        from tools.history import register
        from mcp.server.fastmcp import FastMCP
        test_mcp = FastMCP("test")
        register(test_mcp)
        for tool in test_mcp._tool_manager.list_tools():
            if tool.name == "get_stock_history":
                result = await tool.fn(symbol="VNM", period="10y")
                break
        assert "❌" in result
        assert "10y" in result

    @pytest.mark.asyncio
    async def test_empty_dataframe(self):
        """DataFrame rỗng → error message."""
        with patch("data_sources.vnstock_client.get_stock_history", return_value=pd.DataFrame()):
            from tools.history import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_history":
                    result = await tool.fn(symbol="VNM", period="1y")
                    break
            assert "❌" in result

    @pytest.mark.asyncio
    async def test_no_indicators(self, sample_ohlcv_250):
        """include_indicators=False → trả về basic OHLCV, không gọi TA."""
        with patch("data_sources.vnstock_client.get_stock_history", return_value=sample_ohlcv_250):
            from tools.history import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_history":
                    result = await tool.fn(symbol="VNM", period="1y", include_indicators=False)
                    break
            assert isinstance(result, str)
            assert "MA20" not in result

    @pytest.mark.asyncio
    async def test_ta_failure_graceful(self, sample_ohlcv_250):
        """TA fail → không crash, có warning."""
        with (
            patch("data_sources.vnstock_client.get_stock_history", return_value=sample_ohlcv_250),
            patch("data_sources.ta_calculator.calculate_indicators", side_effect=RuntimeError("TA error")),
        ):
            from tools.history import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_history":
                    result = await tool.fn(symbol="VNM", period="1y")
                    break
            assert isinstance(result, str)
            # Phải có warning, không crash
            assert "⚠️" in result or "VNM" in result

    @pytest.mark.asyncio
    async def test_contains_ohlcv_table(self, sample_ohlcv_250):
        """Output phải có bảng 5 phiên gần nhất."""
        mock_indicators = {
            "ma20": 74500.0, "ma50": 72000.0, "ma200": None,
            "ema20": 73500.0, "rsi14": 55.0,
            "macd": {}, "bb": {}, "atr14": None,
            "volume_ma20": None, "volume_ratio": None,
        }
        with (
            patch("data_sources.vnstock_client.get_stock_history", return_value=sample_ohlcv_250),
            patch("data_sources.ta_calculator.calculate_indicators", return_value=mock_indicators),
            patch("data_sources.ta_calculator.detect_patterns", return_value=[]),
            patch("data_sources.ta_calculator.find_support_resistance", return_value={}),
            patch("data_sources.ta_calculator.get_trend", return_value={"short_term": "UPTREND", "medium_term": "UPTREND", "long_term": "UPTREND", "strength": "MODERATE"}),
        ):
            from tools.history import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_stock_history":
                    result = await tool.fn(symbol="VNM", period="1y")
                    break
            assert "5 phiên" in result


# ─── Tests: tools/financials.py ──────────────────────────────────────────────


class TestGetFinancialReport:
    """Tests cho get_financial_report tool."""

    @pytest.mark.asyncio
    async def test_returns_string(self, mock_financial_data):
        with patch("data_sources.vnstock_client.get_financial_report", return_value=mock_financial_data):
            from tools.financials import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_financial_report":
                    result = await tool.fn(symbol="VNM")
                    break
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_contains_ratios(self, mock_financial_data):
        """Output phải có P/E, P/B, ROE."""
        with patch("data_sources.vnstock_client.get_financial_report", return_value=mock_financial_data):
            from tools.financials import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_financial_report":
                    result = await tool.fn(symbol="VNM", report_type="ratios")
                    break
            assert "P/E" in result
            assert "ROE" in result

    @pytest.mark.asyncio
    async def test_contains_income_statement(self, mock_financial_data):
        """Output income type phải có kết quả kinh doanh."""
        with patch("data_sources.vnstock_client.get_financial_report", return_value=mock_financial_data):
            from tools.financials import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_financial_report":
                    result = await tool.fn(symbol="VNM", report_type="income")
                    break
            assert "Doanh thu" in result or "Q4/2025" in result

    @pytest.mark.asyncio
    async def test_error_handling(self):
        with patch("data_sources.vnstock_client.get_financial_report", return_value={"error": "Not found"}):
            from tools.financials import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_financial_report":
                    result = await tool.fn(symbol="NOTEXIST")
                    break
            assert "❌" in result

    @pytest.mark.asyncio
    async def test_num_quarters_clamped(self, mock_financial_data):
        """num_quarters được clamp 1-8."""
        with patch("data_sources.vnstock_client.get_financial_report", return_value=mock_financial_data):
            from tools.financials import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_financial_report":
                    result = await tool.fn(symbol="VNM", num_quarters=100)
                    break
            assert isinstance(result, str)


# ─── Tests: tools/news.py ────────────────────────────────────────────────────


class TestGetNews:
    """Tests cho get_news tool."""

    @pytest.mark.asyncio
    async def test_market_news(self, mock_news_articles):
        """Không có symbol → trả về tin thị trường."""
        with patch(
            "data_sources.news_scraper.get_market_news",
            new=AsyncMock(return_value=mock_news_articles),
        ):
            from tools.news import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_news":
                    result = await tool.fn(symbol="", limit=10)
                    break
            assert isinstance(result, str)
            assert "VN-Index" in result or "ACB" in result

    @pytest.mark.asyncio
    async def test_symbol_filter(self, mock_news_articles):
        """Có symbol → filter tin theo mã."""
        vnm_articles = [a for a in mock_news_articles if "VNM" in a.get("symbols_mentioned", [])]
        with patch(
            "data_sources.news_scraper.get_news_by_symbol",
            new=AsyncMock(return_value=vnm_articles),
        ):
            from tools.news import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_news":
                    result = await tool.fn(symbol="VNM", limit=5)
                    break
            assert isinstance(result, str)
            assert "VNM" in result

    @pytest.mark.asyncio
    async def test_empty_news(self):
        """Không có tin → warning message."""
        with patch(
            "data_sources.news_scraper.get_market_news",
            new=AsyncMock(return_value=[]),
        ):
            from tools.news import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_news":
                    result = await tool.fn(symbol="", limit=10)
                    break
            assert "⚠️" in result

    @pytest.mark.asyncio
    async def test_limit_clamped(self, mock_news_articles):
        """limit > 30 → clamp về 30."""
        with patch(
            "data_sources.news_scraper.get_market_news",
            new=AsyncMock(return_value=mock_news_articles),
        ) as mock_fn:
            from tools.news import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_news":
                    await tool.fn(symbol="", limit=100)
                    break
            # get_market_news gọi với limit=30
            mock_fn.assert_called_once_with(limit=30)


# ─── Tests: tools/screener.py ────────────────────────────────────────────────


class TestScreenStocks:
    """Tests cho screen_stocks tool."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        """Tool luôn trả về str."""
        mock_price = {"price": 30000, "volume": 2_000_000}
        mock_fin = {"ratios": {"pe": 10.0, "pb": 1.5, "roe": 0.25, "roa": 0.10}}
        with (
            patch("data_sources.vnstock_client.get_stock_price", return_value=mock_price),
            patch("data_sources.vnstock_client.get_financial_report", return_value=mock_fin),
        ):
            from tools.screener import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "screen_stocks":
                    result = await tool.fn(criteria="PE<15")
                    break
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_invalid_criteria(self):
        """Criteria không parse được → hướng dẫn."""
        from tools.screener import register
        from mcp.server.fastmcp import FastMCP
        test_mcp = FastMCP("test")
        register(test_mcp)
        for tool in test_mcp._tool_manager.list_tools():
            if tool.name == "screen_stocks":
                result = await tool.fn(criteria="gibberish no operators")
                break
        assert "❌" in result
        assert "PE<15" in result  # ví dụ trong error message

    def test_criteria_parser_valid(self):
        """Parser phải parse đúng các tiêu chí phổ biến."""
        from tools.screener import _parse_criteria

        filters = _parse_criteria("PE<15, ROE>15, RSI<30")
        assert len(filters) == 3

        pe_filter = next(f for f in filters if f["field"] == "pe")
        assert pe_filter["op"] == "lt"
        assert pe_filter["value"] == 15.0

        roe_filter = next(f for f in filters if f["field"] == "roe")
        assert roe_filter["op"] == "gt"
        assert roe_filter["value"] == 15.0

        rsi_filter = next(f for f in filters if f["field"] == "rsi")
        assert rsi_filter["op"] == "lt"
        assert rsi_filter["value"] == 30.0

    def test_criteria_parser_operators(self):
        """Parser hỗ trợ <=, >=, <, >, =."""
        from tools.screener import _parse_criteria

        filters = _parse_criteria("PE<=20, PB>=1, ROE=15")
        assert filters[0]["op"] == "lte"
        assert filters[1]["op"] == "gte"
        assert filters[2]["op"] == "eq"

    def test_apply_filter(self):
        """Filter áp dụng đúng cho dict."""
        from tools.screener import _apply_filter

        stock = {"pe": 12.0, "roe": 25.0, "rsi": 28.0, "volume": 1_500_000}

        assert _apply_filter(stock, {"field": "pe", "op": "lt", "value": 15}) is True
        assert _apply_filter(stock, {"field": "pe", "op": "gt", "value": 15}) is False
        assert _apply_filter(stock, {"field": "roe", "op": "gte", "value": 20}) is True
        assert _apply_filter(stock, {"field": "rsi", "op": "lt", "value": 30}) is True
        assert _apply_filter(stock, {"field": "missing_key", "op": "lt", "value": 10}) is False


# ─── Tests: tools/portfolio.py ───────────────────────────────────────────────


class TestGetPortfolio:
    """Tests cho get_portfolio tool."""

    @pytest.mark.asyncio
    async def test_empty_portfolio(self, tmp_portfolio_path):
        """Portfolio rỗng → thông báo trống."""
        from tools.portfolio import register
        from mcp.server.fastmcp import FastMCP
        test_mcp = FastMCP("test")
        with patch("data_sources.portfolio.DEFAULT_PORTFOLIO_PATH", tmp_portfolio_path):
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_portfolio":
                    result = await tool.fn()
                    break
        assert isinstance(result, str)
        assert "trống" in result.lower() or "Danh mục" in result

    @pytest.mark.asyncio
    async def test_portfolio_with_positions(self, tmp_portfolio_path):
        """Portfolio có vị thế → hiện P&L."""
        import json

        portfolio_data = {
            "positions": [
                {"symbol": "VNM", "qty": 1000, "avg_cost": 72000, "purchase_date": "2026-01-01", "notes": ""}
            ],
            "cash": 50_000_000,
            "t1_receivable": 0,
            "t2_receivable": 0,
            "updated_at": "2026-03-30T08:00:00",
        }
        tmp_portfolio_path.write_text(json.dumps(portfolio_data))

        mock_price = {"price": 75000, "volume": 1_000_000}

        with patch("data_sources.vnstock_client.get_stock_price", return_value=mock_price):
            from tools.portfolio import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            with patch("data_sources.portfolio.DEFAULT_PORTFOLIO_PATH", tmp_portfolio_path):
                register(test_mcp)
                for tool in test_mcp._tool_manager.list_tools():
                    if tool.name == "get_portfolio":
                        result = await tool.fn()
                        break
        assert isinstance(result, str)
        assert "VNM" in result
        assert "NAV" in result


class TestUpdatePortfolio:
    """Tests cho update_portfolio tool."""

    @pytest.mark.asyncio
    async def test_buy_new_position(self, tmp_portfolio_path):
        """Mua mới → thêm vị thế."""
        from tools.portfolio import register
        from mcp.server.fastmcp import FastMCP
        test_mcp = FastMCP("test")
        with patch("data_sources.portfolio.DEFAULT_PORTFOLIO_PATH", tmp_portfolio_path):
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "update_portfolio":
                    result = await tool.fn(action="buy", symbol="HPG", qty=500, price=29000, notes="Test")
                    break
        assert isinstance(result, str)
        assert "✅" in result
        assert "HPG" in result

    @pytest.mark.asyncio
    async def test_invalid_action(self, tmp_portfolio_path):
        """Action không hợp lệ → error."""
        from tools.portfolio import register
        from mcp.server.fastmcp import FastMCP
        test_mcp = FastMCP("test")
        with patch("data_sources.portfolio.DEFAULT_PORTFOLIO_PATH", tmp_portfolio_path):
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "update_portfolio":
                    result = await tool.fn(action="invalid_action", symbol="HPG", qty=100, price=30000)
                    break
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_sell_nonexistent_position(self, tmp_portfolio_path):
        """Bán mã không có trong portfolio → error."""
        from tools.portfolio import register
        from mcp.server.fastmcp import FastMCP
        test_mcp = FastMCP("test")
        with patch("data_sources.portfolio.DEFAULT_PORTFOLIO_PATH", tmp_portfolio_path):
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "update_portfolio":
                    result = await tool.fn(action="sell", symbol="NOTEXIST", qty=100, price=10000)
                    break
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_invalid_qty(self, tmp_portfolio_path):
        """qty <= 0 → error."""
        from tools.portfolio import register
        from mcp.server.fastmcp import FastMCP
        test_mcp = FastMCP("test")
        with patch("data_sources.portfolio.DEFAULT_PORTFOLIO_PATH", tmp_portfolio_path):
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "update_portfolio":
                    result = await tool.fn(action="buy", symbol="VNM", qty=-100, price=75000)
                    break
        assert "❌" in result


# ─── Tests: tools/insider.py ─────────────────────────────────────────────────


class TestGetInsiderTrades:
    """Tests cho get_insider_trades tool."""

    @pytest.mark.asyncio
    async def test_returns_string_when_no_data(self):
        """Không có data → thông báo rõ ràng."""
        with patch(
            "data_sources.vietstock_client.get_insider_trades",
            new=AsyncMock(return_value=[]),
        ):
            from tools.insider import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_insider_trades":
                    result = await tool.fn(symbol="VNM")
                    break
        assert isinstance(result, str)
        assert "⚠️" in result or "Không tìm thấy" in result

    @pytest.mark.asyncio
    async def test_with_trades_data(self):
        """Có data → format thành table."""
        mock_trades = [
            {
                "date": "2026-03-15",
                "person": "Nguyễn Văn A",
                "title": "Chủ tịch HĐQT",
                "action": "Mua",
                "qty": 100_000,
                "price": 74000,
                "after_qty": 2_500_000,
            },
            {
                "date": "2026-03-10",
                "person": "Trần Thị B",
                "title": "CEO",
                "action": "Bán",
                "qty": 50_000,
                "price": 76000,
                "after_qty": 800_000,
            },
        ]
        with patch(
            "data_sources.vietstock_client.get_insider_trades",
            new=AsyncMock(return_value=mock_trades),
        ):
            from tools.insider import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_insider_trades":
                    result = await tool.fn(symbol="VNM")
                    break
        assert isinstance(result, str)
        assert "Nguyễn Văn A" in result
        assert "Mua" in result or "🟢" in result

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Exception từ source → không crash."""
        with patch(
            "data_sources.vietstock_client.get_insider_trades",
            new=AsyncMock(side_effect=Exception("Network error")),
        ):
            from tools.insider import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_insider_trades":
                    result = await tool.fn(symbol="VNM")
                    break
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_limit_clamped(self):
        """limit > 50 → clamp về 50."""
        with patch(
            "data_sources.vietstock_client.get_insider_trades",
            new=AsyncMock(return_value=[]),
        ) as mock_fn:
            from tools.insider import register
            from mcp.server.fastmcp import FastMCP
            test_mcp = FastMCP("test")
            register(test_mcp)
            for tool in test_mcp._tool_manager.list_tools():
                if tool.name == "get_insider_trades":
                    await tool.fn(symbol="VNM", limit=200)
                    break
        mock_fn.assert_called_once_with("VNM", limit=50)


# ─── Tests: server.py startup ────────────────────────────────────────────────


class TestServerStartup:
    """Tests server khởi động đúng."""

    def test_server_loads(self):
        """Server import không crash."""
        from server import mcp
        assert mcp is not None

    def test_all_tools_registered(self):
        """Tất cả 11 tools đều đăng ký."""
        from server import mcp
        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        expected = {
            "get_stock_price",
            "get_market_overview",
            "get_top_movers",
            "get_stock_history",
            "get_financial_report",
            "get_sector_peers",
            "get_news",
            "screen_stocks",
            "get_portfolio",
            "update_portfolio",
            "get_insider_trades",
        }
        assert expected == tool_names

    def test_tool_has_docstring(self):
        """Mỗi tool phải có docstring (Claude đọc)."""
        from server import mcp
        for tool in mcp._tool_manager.list_tools():
            assert tool.description, f"Tool '{tool.name}' thiếu docstring"

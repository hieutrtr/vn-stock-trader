"""
tests/test_automation.py — Tests cho automation scripts.

Test morning_brief, session_summary, portfolio_monitor, watchlist_alert
với mock data (không gọi vnstock thật).

Coverage targets:
  - is_trading_day()
  - is_trading_session()
  - evaluate_alert() (all conditions)
  - check_price_changes(), check_near_ceiling_floor(), check_volume_spike()
  - _section_* formatter functions
  - morning_brief() và session_summary() end-to-end với mock
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Đảm bảo scripts/ có trong path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(MCP_SERVER_DIR))


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
def mock_market_data():
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
def mock_portfolio_data():
    return {
        "_schema": "vn-stock-trader portfolio v1",
        "positions": [
            {"symbol": "VNM", "qty": 1000, "avg_cost": 72000, "purchase_date": "2026-01-15", "notes": ""},
            {"symbol": "HPG", "qty": 2000, "avg_cost": 28000, "purchase_date": "2026-02-01", "notes": ""},
        ],
        "cash": 50_000_000,
        "t1_receivable": 0,
        "t2_receivable": 0,
    }


@pytest.fixture
def mock_watchlist_data():
    return {
        "_schema": "vn-stock-trader watchlist v1",
        "symbols": ["HPG", "ACB", "MBB"],
        "alerts": [
            {"symbol": "HPG", "condition": "price_below", "value": 28000, "note": "Vùng hỗ trợ"},
            {"symbol": "ACB", "condition": "price_above", "value": 30000, "note": "Breakout test"},
            {"symbol": "MBB", "condition": "pct_change_above", "value": 5.0, "note": "Tăng mạnh"},
        ],
    }


@pytest.fixture
def mock_automation_config():
    return {
        "schedule": {
            "morning_brief_time": "08:30",
            "session_summary_time": "14:50",
            "monitor_interval_minutes": 5,
        },
        "alert_thresholds": {
            "price_change_pct": 5.0,
            "volume_spike_ratio": 3.0,
            "near_ceiling_pct": 1.0,
            "near_floor_pct": 1.0,
        },
        "trading_hours": {
            "morning_open": "09:00",
            "morning_close": "11:30",
            "afternoon_open": "13:00",
            "afternoon_close": "14:45",
        },
    }


# ─── Test: is_trading_day ─────────────────────────────────────────────────────


class TestIsTradingDay:
    """Tests for morning_brief.is_trading_day()"""

    def test_monday_is_trading_day(self):
        from morning_brief import is_trading_day
        monday = date(2026, 3, 30)  # 2026-03-30 là thứ 2
        assert is_trading_day(monday) is True

    def test_saturday_not_trading_day(self):
        from morning_brief import is_trading_day
        saturday = date(2026, 4, 4)  # Thứ 7
        assert is_trading_day(saturday) is False

    def test_sunday_not_trading_day(self):
        from morning_brief import is_trading_day
        sunday = date(2026, 4, 5)  # Chủ nhật
        assert is_trading_day(sunday) is False

    def test_new_year_not_trading_day(self):
        from morning_brief import is_trading_day
        new_year = date(2026, 1, 1)
        assert is_trading_day(new_year) is False

    def test_liberation_day_not_trading(self):
        from morning_brief import is_trading_day
        lib_day = date(2026, 4, 30)
        assert is_trading_day(lib_day) is False

    def test_normal_weekday_is_trading(self):
        from morning_brief import is_trading_day
        # 2026-03-25 là thứ 4 (không phải lễ)
        assert is_trading_day(date(2026, 3, 25)) is True


# ─── Test: is_trading_session ─────────────────────────────────────────────────


class TestIsTradingSession:
    """Tests for portfolio_monitor.is_trading_session()"""

    def test_morning_session_is_trading(self):
        from portfolio_monitor import is_trading_session
        # Thứ 4, 10:00 sáng
        dt = datetime(2026, 3, 25, 10, 0)
        with patch("portfolio_monitor.load_config", return_value={}):
            assert is_trading_session(dt) is True

    def test_afternoon_session_is_trading(self):
        from portfolio_monitor import is_trading_session
        dt = datetime(2026, 3, 25, 13, 30)
        with patch("portfolio_monitor.load_config", return_value={}):
            assert is_trading_session(dt) is True

    def test_lunch_break_not_trading(self):
        from portfolio_monitor import is_trading_session
        dt = datetime(2026, 3, 25, 12, 0)
        with patch("portfolio_monitor.load_config", return_value={}):
            assert is_trading_session(dt) is False

    def test_after_close_not_trading(self):
        from portfolio_monitor import is_trading_session
        dt = datetime(2026, 3, 25, 15, 30)
        with patch("portfolio_monitor.load_config", return_value={}):
            assert is_trading_session(dt) is False

    def test_saturday_not_trading(self):
        from portfolio_monitor import is_trading_session
        dt = datetime(2026, 4, 4, 10, 0)  # Saturday
        with patch("portfolio_monitor.load_config", return_value={}):
            assert is_trading_session(dt) is False

    def test_before_open_not_trading(self):
        from portfolio_monitor import is_trading_session
        dt = datetime(2026, 3, 25, 8, 0)  # Trước 9:00
        with patch("portfolio_monitor.load_config", return_value={}):
            assert is_trading_session(dt) is False


# ─── Test: evaluate_alert ─────────────────────────────────────────────────────


class TestEvaluateAlert:
    """Tests for watchlist_alert.evaluate_alert()"""

    @pytest.fixture(autouse=True)
    def price_data(self, mock_price_data):
        self.price = mock_price_data  # price=75000, pct=1.35, ceil=79180, floor=68820

    def test_price_below_triggered(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "price_below", "value": 80000}
        triggered, msg = evaluate_alert(alert, self.price)
        assert triggered is True
        assert "VNM" in msg
        assert "price_below" in msg

    def test_price_below_not_triggered(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "price_below", "value": 70000}
        triggered, _ = evaluate_alert(alert, self.price)
        assert triggered is False

    def test_price_above_triggered(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "price_above", "value": 70000}
        triggered, msg = evaluate_alert(alert, self.price)
        assert triggered is True
        assert "price_above" in msg

    def test_price_above_not_triggered(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "price_above", "value": 80000}
        triggered, _ = evaluate_alert(alert, self.price)
        assert triggered is False

    def test_pct_change_above_triggered(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "pct_change_above", "value": 1.0}
        triggered, msg = evaluate_alert(alert, self.price)  # pct=1.35
        assert triggered is True
        assert "pct_change_above" in msg

    def test_pct_change_above_not_triggered(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "pct_change_above", "value": 5.0}
        triggered, _ = evaluate_alert(alert, self.price)  # pct=1.35
        assert triggered is False

    def test_pct_change_below_triggered(self):
        from watchlist_alert import evaluate_alert
        price_down = {**self.price, "pct_change": -4.0}
        alert = {"symbol": "VNM", "condition": "pct_change_below", "value": -3.0}
        triggered, msg = evaluate_alert(alert, price_down)
        assert triggered is True

    def test_near_ceiling_triggered(self):
        from watchlist_alert import evaluate_alert
        # price=75000, ceil=79180 → room = (79180-75000)/75000 = 5.57%
        # near_ceiling với value=6% → nên trigger
        alert = {"symbol": "VNM", "condition": "near_ceiling", "value": 6.0}
        triggered, msg = evaluate_alert(alert, self.price)
        assert triggered is True
        assert "near_ceiling" in msg

    def test_near_ceiling_not_triggered(self):
        from watchlist_alert import evaluate_alert
        # room = 5.57%, value = 2% → không trigger
        alert = {"symbol": "VNM", "condition": "near_ceiling", "value": 2.0}
        triggered, _ = evaluate_alert(alert, self.price)
        assert triggered is False

    def test_near_floor_triggered(self):
        from watchlist_alert import evaluate_alert
        # price=75000, floor=68820 → room = (75000-68820)/75000 = 8.24%
        alert = {"symbol": "VNM", "condition": "near_floor", "value": 9.0}
        triggered, msg = evaluate_alert(alert, self.price)
        assert triggered is True

    def test_unknown_condition_returns_false(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "unknown_cond", "value": 1000}
        triggered, _ = evaluate_alert(alert, self.price)
        assert triggered is False

    def test_error_price_data_returns_false(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "price_below", "value": 80000}
        triggered, _ = evaluate_alert(alert, {"error": "Not found"})
        assert triggered is False

    def test_empty_price_data_returns_false(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "price_below", "value": 80000}
        triggered, _ = evaluate_alert(alert, {})
        assert triggered is False

    def test_note_included_in_message(self):
        from watchlist_alert import evaluate_alert
        alert = {"symbol": "VNM", "condition": "price_below", "value": 80000, "note": "Test note"}
        triggered, msg = evaluate_alert(alert, self.price)
        assert triggered is True
        assert "Test note" in msg


# ─── Test: check_price_changes ────────────────────────────────────────────────


class TestCheckPriceChanges:
    """Tests for portfolio_monitor.check_price_changes()"""

    def test_detects_high_positive_change(self):
        from portfolio_monitor import check_price_changes
        positions = [{"symbol": "HPG"}]
        prices = {"HPG": {"price": 30000, "pct_change": 6.8}}
        alerts = check_price_changes(positions, prices, threshold_pct=5.0)
        assert len(alerts) == 1
        msg, key = alerts[0]
        assert "HPG" in msg
        assert "6.8" in msg or "+6.80" in msg

    def test_detects_high_negative_change(self):
        from portfolio_monitor import check_price_changes
        positions = [{"symbol": "VHM"}]
        prices = {"VHM": {"price": 42000, "pct_change": -5.1}}
        alerts = check_price_changes(positions, prices, threshold_pct=5.0)
        assert len(alerts) == 1

    def test_no_alert_below_threshold(self):
        from portfolio_monitor import check_price_changes
        positions = [{"symbol": "VNM"}]
        prices = {"VNM": {"price": 75000, "pct_change": 1.35}}
        alerts = check_price_changes(positions, prices, threshold_pct=5.0)
        assert len(alerts) == 0

    def test_error_price_data_skipped(self):
        from portfolio_monitor import check_price_changes
        positions = [{"symbol": "VNM"}]
        prices = {"VNM": {"error": "not found"}}
        alerts = check_price_changes(positions, prices, threshold_pct=5.0)
        assert len(alerts) == 0

    def test_missing_price_skipped(self):
        from portfolio_monitor import check_price_changes
        positions = [{"symbol": "VNM"}]
        prices = {}
        alerts = check_price_changes(positions, prices, threshold_pct=5.0)
        assert len(alerts) == 0


# ─── Test: check_near_ceiling_floor ──────────────────────────────────────────


class TestCheckNearCeilingFloor:
    """Tests for portfolio_monitor.check_near_ceiling_floor()"""

    def test_near_ceiling_triggers(self):
        from portfolio_monitor import check_near_ceiling_floor
        positions = [{"symbol": "HPG"}]
        prices = {"HPG": {"price": 29700, "ceiling": 30000, "floor": 27900}}
        # room_ceil = (30000-29700)/29700 = 1.0%
        alerts = check_near_ceiling_floor(positions, prices, near_threshold_pct=1.1)
        assert len(alerts) >= 1
        msg, key = alerts[0]
        assert "HPG" in msg
        assert "TRẦN" in msg or "near_ceiling" in msg.lower() or "ceil" in key

    def test_near_floor_triggers(self):
        from portfolio_monitor import check_near_ceiling_floor
        positions = [{"symbol": "HPG"}]
        prices = {"HPG": {"price": 28200, "ceiling": 30000, "floor": 28000}}
        # room_floor = (28200-28000)/28200 = 0.7%
        alerts = check_near_ceiling_floor(positions, prices, near_threshold_pct=1.0)
        assert len(alerts) >= 1
        msg, key = alerts[0]
        assert "HPG" in msg

    def test_no_alert_when_far_from_limits(self):
        from portfolio_monitor import check_near_ceiling_floor
        positions = [{"symbol": "VNM"}]
        prices = {"VNM": {"price": 75000, "ceiling": 79180, "floor": 68820}}
        alerts = check_near_ceiling_floor(positions, prices, near_threshold_pct=1.0)
        assert len(alerts) == 0


# ─── Test: section formatters ────────────────────────────────────────────────


class TestMorningBriefSections:
    """Tests cho _section_* formatters trong morning_brief.py"""

    def test_section_market_overview_returns_string_list(self, mock_market_data):
        from morning_brief import _section_market_overview
        lines = _section_market_overview(mock_market_data)
        assert isinstance(lines, list)
        assert any("VN-Index" in line for line in lines)
        assert any("HNX" in line for line in lines)

    def test_section_market_overview_with_error(self):
        from morning_brief import _section_market_overview
        lines = _section_market_overview({"error": "Connection failed"})
        assert isinstance(lines, list)
        assert len(lines) > 0
        # Should contain error message
        assert any("Connection failed" in line for line in lines)

    def test_section_portfolio_status_empty(self):
        from morning_brief import _section_portfolio_status
        lines = _section_portfolio_status({"positions": [], "cash": 0}, {})
        assert isinstance(lines, list)
        assert any("trống" in line.lower() for line in lines)

    def test_section_portfolio_status_with_positions(self, mock_price_data):
        from morning_brief import _section_portfolio_status
        portfolio = {
            "positions": [{"symbol": "VNM", "qty": 1000, "avg_cost": 72000}],
            "cash": 50_000_000,
        }
        prices = {"VNM": mock_price_data}
        lines = _section_portfolio_status(portfolio, prices)
        assert isinstance(lines, list)
        assert any("VNM" in line for line in lines)
        assert any("P&L" in line or "Tổng" in line for line in lines)

    def test_section_watchlist_empty(self):
        from morning_brief import _section_watchlist
        lines = _section_watchlist([], {})
        assert isinstance(lines, list)
        assert any("trống" in line.lower() for line in lines)

    def test_section_watchlist_with_prices(self, mock_price_data):
        from morning_brief import _section_watchlist
        lines = _section_watchlist(["VNM"], {"VNM": mock_price_data})
        assert isinstance(lines, list)
        assert any("VNM" in line for line in lines)
        assert any("75,000" in line or "75000" in line for line in lines)

    def test_section_news_empty(self):
        from morning_brief import _section_news
        lines = _section_news([])
        assert isinstance(lines, list)
        assert any("không có" in line.lower() for line in lines)

    def test_section_news_with_articles(self):
        from morning_brief import _section_news
        news = [
            {
                "title": "VN-Index tăng",
                "url": "https://cafef.vn/test",
                "published_at": "2026-03-30T10:00:00",
                "source": "cafef",
            }
        ]
        lines = _section_news(news)
        assert isinstance(lines, list)
        assert any("VN-Index tăng" in line for line in lines)


# ─── Test: session_summary sections ──────────────────────────────────────────


class TestSessionSummarySections:
    """Tests cho session_summary section formatters."""

    def test_section_market_result_returns_list(self, mock_market_data):
        from session_summary import _section_market_result
        lines = _section_market_result(mock_market_data)
        assert isinstance(lines, list)
        assert any("VN-Index" in line for line in lines)

    def test_section_top_movers_with_data(self):
        from session_summary import _section_top_movers
        movers = {
            "gainers": [{"symbol": "HPG", "price": 30000, "pct_change": 6.8}],
            "losers": [{"symbol": "VHM", "price": 42000, "pct_change": -5.1}],
            "volume_leaders": [{"symbol": "STB", "price": 18000, "volume": 8_000_000}],
        }
        lines = _section_top_movers(movers)
        assert isinstance(lines, list)
        assert any("HPG" in line for line in lines)
        assert any("VHM" in line for line in lines)

    def test_section_portfolio_pnl_empty_portfolio(self):
        from session_summary import _section_portfolio_pnl
        lines = _section_portfolio_pnl({"positions": [], "cash": 0}, {})
        assert isinstance(lines, list)
        assert any("trống" in line.lower() for line in lines)

    def test_section_portfolio_pnl_with_positions(self, mock_price_data):
        from session_summary import _section_portfolio_pnl
        portfolio_data = {
            "positions": [{"symbol": "VNM", "qty": 1000, "avg_cost": 72000}],
            "cash": 50_000_000,
        }
        prices = {"VNM": mock_price_data}
        lines = _section_portfolio_pnl(portfolio_data, prices)
        assert isinstance(lines, list)
        assert any("VNM" in line for line in lines)
        assert any("P&L" in line or "NAV" in line for line in lines)

    def test_section_tomorrow_plan_returns_list(self, mock_market_data):
        from session_summary import _section_tomorrow_plan
        lines = _section_tomorrow_plan(mock_market_data, {})
        assert isinstance(lines, list)
        assert len(lines) > 0

    def test_section_anomalies_no_anomaly(self, mock_market_data, mock_portfolio_data):
        from session_summary import _section_anomalies
        prices = {
            "VNM": {"price": 75000, "pct_change": 1.0},
            "HPG": {"price": 28000, "pct_change": 0.5},
        }
        config = {"alert_thresholds": {"price_change_pct": 5.0}}
        lines = _section_anomalies(mock_market_data, {}, mock_portfolio_data, prices, config)
        # Không có bất thường → trả về list rỗng
        assert isinstance(lines, list)
        assert len(lines) == 0  # No anomalies

    def test_section_anomalies_detects_price_change(self, mock_market_data, mock_portfolio_data):
        from session_summary import _section_anomalies
        prices = {
            "VNM": {"price": 75000, "pct_change": 6.5},  # > 5% threshold
            "HPG": {"price": 28000, "pct_change": 0.5},
        }
        config = {"alert_thresholds": {"price_change_pct": 5.0}}
        lines = _section_anomalies(mock_market_data, {}, mock_portfolio_data, prices, config)
        assert len(lines) > 0
        assert any("VNM" in line for line in lines)


# ─── Test: morning_brief integration ─────────────────────────────────────────


class TestMorningBriefIntegration:
    """Integration tests cho morning_brief() với mocked data sources."""

    @pytest.mark.asyncio
    async def test_skip_on_weekend(self):
        from morning_brief import morning_brief
        saturday = date(2026, 4, 4)
        with patch("morning_brief.date") as mock_date:
            mock_date.today.return_value = saturday
            result = await morning_brief(force=False)
        assert "không phải ngày giao dịch" in result

    @pytest.mark.asyncio
    async def test_force_runs_on_weekend(self, mock_market_data, mock_price_data):
        from morning_brief import morning_brief

        with (
            patch("morning_brief.date") as mock_date,
            patch("morning_brief.load_watchlist", return_value={"symbols": ["VNM"], "alerts": []}),
            patch("morning_brief.load_portfolio_summary", return_value={"positions": [], "cash": 0, "symbols": []}),
            patch("morning_brief.load_config", return_value={}),
            patch("data_sources.vnstock_client.get_market_overview", return_value=mock_market_data),
            patch("data_sources.vnstock_client.get_stock_price", return_value=mock_price_data),
        ):
            mock_date.today.return_value = date(2026, 4, 4)  # Saturday
            mock_date.side_effect = None

            # Patch get_market_news separately as async
            import morning_brief as mb
            with patch.object(mb, "morning_brief", wraps=morning_brief):
                result = await morning_brief(force=True)

        # Should return brief content (not weekend message)
        assert isinstance(result, str)
        assert len(result) > 50

    @pytest.mark.asyncio
    async def test_returns_markdown_on_trading_day(self, mock_market_data, mock_price_data):
        from morning_brief import morning_brief

        with (
            patch("morning_brief.is_trading_day", return_value=True),
            patch("morning_brief.load_watchlist", return_value={"symbols": ["VNM"], "alerts": []}),
            patch("morning_brief.load_portfolio_summary", return_value={"positions": [], "cash": 0, "symbols": []}),
            patch("morning_brief.load_config", return_value={}),
        ):
            # Mock the import inside morning_brief
            with patch.dict("sys.modules", {
                "data_sources.vnstock_client": MagicMock(
                    get_market_overview=MagicMock(return_value=mock_market_data),
                    get_stock_price=MagicMock(return_value=mock_price_data),
                ),
                "data_sources.news_scraper": MagicMock(
                    get_market_news=AsyncMock(return_value=[])
                ),
            }):
                result = await morning_brief(force=False)

        assert isinstance(result, str)
        assert "Morning Brief" in result or "Tổng quan" in result or "thị trường" in result.lower()


# ─── Test: session_summary integration ───────────────────────────────────────


class TestSessionSummaryIntegration:
    """Integration tests cho session_summary()."""

    @pytest.mark.asyncio
    async def test_skip_on_weekend(self):
        from session_summary import session_summary

        with patch("session_summary.is_trading_day", return_value=False):
            result = await session_summary(force=False)
        assert "không phải ngày giao dịch" in result

    @pytest.mark.asyncio
    async def test_returns_markdown_with_mock(self, mock_market_data, mock_price_data):
        from session_summary import session_summary

        with (
            patch("session_summary.is_trading_day", return_value=True),
            patch("session_summary.load_portfolio_data", return_value={"positions": [], "cash": 0}),
            patch("session_summary.load_watchlist", return_value={"symbols": []}),
            patch("session_summary.load_config", return_value={}),
        ):
            with patch.dict("sys.modules", {
                "data_sources.vnstock_client": MagicMock(
                    get_market_overview=MagicMock(return_value=mock_market_data),
                    get_stock_price=MagicMock(return_value=mock_price_data),
                    get_top_movers=MagicMock(return_value={"gainers": [], "losers": [], "volume_leaders": []}),
                ),
                "data_sources.news_scraper": MagicMock(
                    get_market_news=AsyncMock(return_value=[])
                ),
            }):
                result = await session_summary(force=False)

        assert isinstance(result, str)
        assert "Session Summary" in result or "Kết quả phiên" in result


# ─── Test: watchlist_alert integration ───────────────────────────────────────


class TestWatchlistAlertIntegration:
    """Integration tests cho check_watchlist()."""

    def test_check_watchlist_triggers_alert(self, mock_watchlist_data):
        from watchlist_alert import check_watchlist

        # HPG price_below 28000: mock price = 27500 → trigger
        prices_map = {
            "HPG": {"price": 27500, "pct_change": -1.8, "ceiling": 29960, "floor": 25820},
            "ACB": {"price": 25000, "pct_change": 0.5, "ceiling": 28000, "floor": 23200},
            "MBB": {"price": 26000, "pct_change": 2.0, "ceiling": 27600, "floor": 24400},
        }

        with patch.dict("sys.modules", {
            "data_sources.vnstock_client": MagicMock(
                get_stock_price=MagicMock(side_effect=lambda sym: prices_map.get(sym, {"error": "not found"}))
            )
        }):
            triggered = check_watchlist(mock_watchlist_data, dry_run=True)

        assert len(triggered) >= 1
        syms = [a["symbol"] for a in triggered]
        assert "HPG" in syms  # price_below 28000 triggered

    def test_check_watchlist_no_alerts(self, mock_watchlist_data):
        from watchlist_alert import check_watchlist

        # Prices không satisfy bất kỳ condition nào
        prices_map = {
            "HPG": {"price": 30000, "pct_change": 1.0, "ceiling": 32000, "floor": 27900},
            "ACB": {"price": 25000, "pct_change": 0.5, "ceiling": 26500, "floor": 23500},
            "MBB": {"price": 26000, "pct_change": 2.0, "ceiling": 27600, "floor": 24400},
        }

        with patch.dict("sys.modules", {
            "data_sources.vnstock_client": MagicMock(
                get_stock_price=MagicMock(side_effect=lambda sym: prices_map.get(sym, {"error": "not found"}))
            )
        }):
            triggered = check_watchlist(mock_watchlist_data, dry_run=True)

        # HPG price (30000) > 28000 → price_below NOT triggered
        # ACB price (25000) < 30000 → price_above NOT triggered
        # MBB pct (2.0%) < 5.0% → pct_change_above NOT triggered
        assert len(triggered) == 0

    def test_check_watchlist_import_error_returns_empty(self, mock_watchlist_data):
        from watchlist_alert import check_watchlist

        with patch.dict("sys.modules", {"data_sources.vnstock_client": None}):
            # Sẽ raise ImportError → return []
            try:
                triggered = check_watchlist(mock_watchlist_data, dry_run=True)
                # nếu không raise, phải trả về []
                assert isinstance(triggered, list)
            except SystemExit:
                pass  # OK nếu script exit

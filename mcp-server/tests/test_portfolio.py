"""
Tests cho portfolio.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from data_sources.portfolio import Portfolio, PortfolioManager, Position


class TestPosition:
    def test_from_dict(self) -> None:
        data = {"symbol": "vnm", "qty": 1000, "avg_cost": 72000, "notes": "Test"}
        pos = Position.from_dict(data)
        assert pos.symbol == "VNM"
        assert pos.qty == 1000
        assert pos.avg_cost == 72000.0

    def test_to_dict(self) -> None:
        pos = Position(symbol="HPG", qty=500, avg_cost=29000)
        d = pos.to_dict()
        assert d["symbol"] == "HPG"
        assert d["qty"] == 500
        assert "current_price" not in d  # computed field không save


class TestPortfolio:
    def test_from_dict_round_trip(self) -> None:
        data = {
            "positions": [{"symbol": "VNM", "qty": 1000, "avg_cost": 72000}],
            "cash": 50_000_000,
            "t1_receivable": 0,
            "t2_receivable": 5_000_000,
        }
        p = Portfolio.from_dict(data)
        assert len(p.positions) == 1
        assert p.positions[0].symbol == "VNM"
        assert p.total_receivable == 5_000_000

    def test_to_dict_is_valid_json(self) -> None:
        p = Portfolio(
            positions=[Position("VNM", 1000, 72000)],
            cash=10_000_000,
        )
        d = p.to_dict()
        assert json.dumps(d)  # không lỗi


class TestPortfolioManager:
    def test_load_nonexistent_returns_empty(self, tmp_portfolio_path: Path) -> None:
        manager = PortfolioManager(tmp_portfolio_path)
        p = manager.load()
        assert len(p.positions) == 0
        assert p.cash == 0.0

    def test_save_and_reload(self, tmp_portfolio_path: Path) -> None:
        manager = PortfolioManager(tmp_portfolio_path)
        p = manager.load()
        p.positions.append(Position("FPT", 200, 120000))
        p.cash = 30_000_000

        assert manager.save(p)

        manager2 = PortfolioManager(tmp_portfolio_path)
        p2 = manager2.load()
        assert len(p2.positions) == 1
        assert p2.positions[0].symbol == "FPT"
        assert p2.cash == 30_000_000

    def test_add_position_new(self, tmp_portfolio_path: Path) -> None:
        manager = PortfolioManager(tmp_portfolio_path)
        manager.load()
        manager.portfolio.cash = 100_000_000

        manager.add_position("VNM", 100, 75000)

        pos = manager.portfolio.positions[0]
        assert pos.symbol == "VNM"
        assert pos.qty == 100
        assert pos.avg_cost == 75000
        # Cash bị trừ
        assert manager.portfolio.cash == 100_000_000 - 100 * 75000

    def test_add_position_weighted_avg(self, tmp_portfolio_path: Path) -> None:
        """Mua thêm → tính giá vốn bình quân gia quyền."""
        manager = PortfolioManager(tmp_portfolio_path)
        manager.load()
        manager.portfolio.cash = 200_000_000

        manager.add_position("HPG", 100, 30000)
        manager.add_position("HPG", 100, 28000)

        pos = manager.portfolio.positions[0]
        assert pos.qty == 200
        # WAC = (100*30000 + 100*28000) / 200 = 29000
        assert pos.avg_cost == 29000.0

    def test_remove_position_calculates_pnl(self, tmp_portfolio_path: Path) -> None:
        """Bán cổ phiếu → tính realized P&L đúng."""
        manager = PortfolioManager(tmp_portfolio_path)
        manager.load()
        manager.portfolio.positions = [Position("VNM", 1000, 70000)]
        manager.portfolio.cash = 0

        result = manager.remove_position("VNM", 500, 75000)

        assert result["realized_pnl"] == 500 * (75000 - 70000)
        # pnl_pct = (sell_price - avg_cost) / avg_cost * 100 = (75000-70000)/70000*100 ≈ 7.14%
        assert result["realized_pnl_pct"] == pytest.approx((75000 - 70000) / 70000 * 100, abs=0.01)
        assert manager.portfolio.positions[0].qty == 500
        assert manager.portfolio.cash == 500 * 75000

    def test_remove_position_clears_when_sold_all(self, tmp_portfolio_path: Path) -> None:
        """Bán hết → xóa vị thế khỏi danh sách."""
        manager = PortfolioManager(tmp_portfolio_path)
        manager.load()
        manager.portfolio.positions = [Position("ACB", 200, 25000)]

        manager.remove_position("ACB", 200, 26000)

        assert len(manager.portfolio.positions) == 0

    def test_remove_position_exceeds_qty(self, tmp_portfolio_path: Path) -> None:
        """Bán nhiều hơn số đang nắm → trả về error."""
        manager = PortfolioManager(tmp_portfolio_path)
        manager.load()
        manager.portfolio.positions = [Position("VNM", 100, 70000)]

        result = manager.remove_position("VNM", 200, 75000)

        assert "error" in result
        assert manager.portfolio.positions[0].qty == 100  # không thay đổi

    def test_calculate_pnl(self, tmp_portfolio_path: Path) -> None:
        """Tính P&L và tỷ trọng danh mục."""
        manager = PortfolioManager(tmp_portfolio_path)
        manager.load()
        manager.portfolio.positions = [
            Position("VNM", 1000, 70000),
            Position("HPG", 500, 28000),
        ]
        manager.portfolio.cash = 50_000_000

        prices = {"VNM": 75000, "HPG": 30000}
        result = manager.calculate_pnl(prices)

        # VNM: 1000 * 75000 = 75M, HPG: 500 * 30000 = 15M
        assert result["total_market_value"] == 75_000_000 + 15_000_000
        assert result["total_unrealized_pnl"] > 0  # cả hai đều lãi

        # NAV = 90M stock + 50M cash = 140M
        assert result["nav"] == 140_000_000

        # Tổng weight = 100%
        total_weight = sum(p["weight_pct"] for p in result["positions"]) + result["cash_weight_pct"]
        assert abs(total_weight - 100.0) < 0.1

    def test_remove_nonexistent_symbol(self, tmp_portfolio_path: Path) -> None:
        """Bán mã không có → trả về error."""
        manager = PortfolioManager(tmp_portfolio_path)
        manager.load()
        result = manager.remove_position("XXXX", 100, 50000)
        assert "error" in result


class TestNewsScraperExtractSymbols:
    """Test extract_symbols_from_text riêng (không cần HTTP)."""

    def test_basic_extraction(self) -> None:
        from data_sources.news_scraper import extract_symbols_from_text
        result = extract_symbols_from_text("HPG tăng mạnh, NKG cũng tích cực")
        assert "HPG" in result
        assert "NKG" in result

    def test_false_positives_filtered(self) -> None:
        from data_sources.news_scraper import extract_symbols_from_text
        text = "VND mất giá, GDP tăng 7%, ROE của ngành ngân hàng cải thiện"
        result = extract_symbols_from_text(text)
        assert "VND" not in result
        assert "GDP" not in result
        assert "ROE" not in result

    def test_known_symbols_extracted(self) -> None:
        from data_sources.news_scraper import extract_symbols_from_text
        text = "VNM, VCB, HPG dẫn đầu đà tăng hôm nay"
        result = extract_symbols_from_text(text)
        assert "VNM" in result
        assert "VCB" in result
        assert "HPG" in result

    def test_empty_text(self) -> None:
        from data_sources.news_scraper import extract_symbols_from_text
        assert extract_symbols_from_text("") == []
        assert extract_symbols_from_text(None) == []

    def test_max_10_symbols(self) -> None:
        from data_sources.news_scraper import extract_symbols_from_text
        text = " ".join([f"VN{i:03d}" for i in range(20)])
        result = extract_symbols_from_text(text)
        assert len(result) <= 10

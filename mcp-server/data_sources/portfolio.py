"""
portfolio.py — Quản lý portfolio chứng khoán.

Load/save từ JSON file, tính P&L, tỷ trọng, tổng giá trị NAV.
Hỗ trợ T+2 settlement (Việt Nam).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PORTFOLIO_PATH = Path(__file__).parent.parent.parent / "data" / "portfolio.json"


# ─── Data Models ─────────────────────────────────────────────────────────────


@dataclass
class Position:
    symbol: str
    qty: int                    # số cổ phiếu đang nắm
    avg_cost: float             # giá vốn bình quân (VNĐ/CP)
    purchase_date: str = ""     # ISO date string
    notes: str = ""

    # Được tính toán, không lưu
    current_price: float = field(default=0.0, repr=False)
    market_value: float = field(default=0.0, repr=False)
    unrealized_pnl: float = field(default=0.0, repr=False)
    unrealized_pnl_pct: float = field(default=0.0, repr=False)
    weight_pct: float = field(default=0.0, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_cost": self.avg_cost,
            "purchase_date": self.purchase_date,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Position:
        return cls(
            symbol=str(data.get("symbol", "")).upper(),
            qty=int(data.get("qty", 0)),
            avg_cost=float(data.get("avg_cost", 0)),
            purchase_date=str(data.get("purchase_date", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass
class Portfolio:
    positions: list[Position] = field(default_factory=list)
    cash: float = 0.0           # tiền mặt sẵn dùng (VNĐ)
    t1_receivable: float = 0.0  # tiền về T+1
    t2_receivable: float = 0.0  # tiền về T+2
    updated_at: str = ""

    @property
    def total_receivable(self) -> float:
        return self.t1_receivable + self.t2_receivable

    @property
    def available_cash(self) -> float:
        return self.cash

    def to_dict(self) -> dict[str, Any]:
        return {
            "_schema": "vn-stock-trader portfolio v1",
            "positions": [p.to_dict() for p in self.positions],
            "cash": self.cash,
            "t1_receivable": self.t1_receivable,
            "t2_receivable": self.t2_receivable,
            "updated_at": self.updated_at or datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Portfolio:
        positions = [Position.from_dict(p) for p in data.get("positions", [])]
        return cls(
            positions=positions,
            cash=float(data.get("cash", 0)),
            t1_receivable=float(data.get("t1_receivable", 0)),
            t2_receivable=float(data.get("t2_receivable", 0)),
            updated_at=str(data.get("updated_at", "")),
        )


# ─── Portfolio Manager ────────────────────────────────────────────────────────


class PortfolioManager:
    """Load, save, và tính toán portfolio."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_PORTFOLIO_PATH
        self._portfolio: Portfolio | None = None

    def load(self) -> Portfolio:
        """Load portfolio từ JSON file."""
        if not self.path.exists():
            logger.info("Portfolio file not found, creating empty portfolio: %s", self.path)
            self._portfolio = Portfolio()
            return self._portfolio

        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self._portfolio = Portfolio.from_dict(data)
            logger.info("Loaded portfolio: %d positions from %s", len(self._portfolio.positions), self.path)
            return self._portfolio
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to load portfolio: %s", e)
            self._portfolio = Portfolio()
            return self._portfolio

    def save(self, portfolio: Portfolio | None = None) -> bool:
        """Save portfolio ra JSON file."""
        p = portfolio or self._portfolio
        if p is None:
            logger.error("No portfolio to save")
            return False

        p.updated_at = datetime.now().isoformat()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(p.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info("Portfolio saved to %s", self.path)
            return True
        except OSError as e:
            logger.error("Failed to save portfolio: %s", e)
            return False

    @property
    def portfolio(self) -> Portfolio:
        if self._portfolio is None:
            self.load()
        return self._portfolio  # type: ignore[return-value]

    # ─── Portfolio Operations ────────────────────────────────────────────────

    def add_position(self, symbol: str, qty: int, price: float, notes: str = "") -> None:
        """Thêm hoặc cập nhật position (tính giá vốn bình quân gia quyền)."""
        symbol = symbol.upper().strip()
        portfolio = self.portfolio

        existing = next((p for p in portfolio.positions if p.symbol == symbol), None)
        if existing:
            # Weighted average cost
            total_qty = existing.qty + qty
            total_cost = existing.qty * existing.avg_cost + qty * price
            existing.avg_cost = total_cost / total_qty if total_qty > 0 else price
            existing.qty = total_qty
            existing.notes = notes or existing.notes
        else:
            portfolio.positions.append(Position(
                symbol=symbol, qty=qty, avg_cost=price,
                purchase_date=datetime.now().strftime("%Y-%m-%d"),
                notes=notes,
            ))

        # Trừ cash
        portfolio.cash -= qty * price
        logger.info("Added position: %s x%d @ %.0f", symbol, qty, price)

    def remove_position(self, symbol: str, qty: int, price: float) -> dict[str, Any]:
        """
        Bán cổ phiếu, tính realized P&L.

        Returns:
            {"symbol": ..., "qty_sold": ..., "avg_cost": ..., "sell_price": ...,
             "realized_pnl": ..., "realized_pnl_pct": ...}
        """
        symbol = symbol.upper().strip()
        portfolio = self.portfolio

        existing = next((p for p in portfolio.positions if p.symbol == symbol), None)
        if not existing:
            return {"error": f"Không có vị thế {symbol}"}

        if qty > existing.qty:
            return {"error": f"Số lượng bán ({qty}) vượt quá số đang nắm ({existing.qty})"}

        avg_cost = existing.avg_cost
        realized_pnl = qty * (price - avg_cost)
        realized_pnl_pct = (price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0

        existing.qty -= qty
        if existing.qty == 0:
            portfolio.positions.remove(existing)

        portfolio.cash += qty * price
        logger.info(
            "Sold %s x%d @ %.0f — P&L: %.0f VNĐ (%.2f%%)",
            symbol, qty, price, realized_pnl, realized_pnl_pct
        )

        return {
            "symbol": symbol,
            "qty_sold": qty,
            "avg_cost": avg_cost,
            "sell_price": price,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": round(realized_pnl_pct, 2),
        }

    def calculate_pnl(self, prices: dict[str, float]) -> dict[str, Any]:
        """
        Tính P&L và tổng giá trị danh mục với giá thị trường hiện tại.

        Args:
            prices: {"VNM": 75000, "HPG": 29500, ...}

        Returns:
            {
                "positions": [...],  # mỗi position với P&L và tỷ trọng
                "total_market_value": ...,
                "total_cost": ...,
                "total_unrealized_pnl": ...,
                "total_unrealized_pnl_pct": ...,
                "nav": ...,  # total_market_value + cash + receivables
                "cash": ...,
                "t1_receivable": ...,
                "t2_receivable": ...,
                "cash_weight_pct": ...,
            }
        """
        portfolio = self.portfolio
        total_market_value = 0.0
        total_cost = 0.0

        # Tính giá trị từng position
        enriched_positions = []
        for pos in portfolio.positions:
            current_price = prices.get(pos.symbol, 0.0)
            market_value = pos.qty * current_price
            cost_basis = pos.qty * pos.avg_cost
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0

            total_market_value += market_value
            total_cost += cost_basis

            enriched_positions.append({
                "symbol": pos.symbol,
                "qty": pos.qty,
                "avg_cost": round(pos.avg_cost),
                "current_price": round(current_price),
                "market_value": round(market_value),
                "cost_basis": round(cost_basis),
                "unrealized_pnl": round(unrealized_pnl),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                "weight_pct": 0.0,  # sẽ tính sau
                "notes": pos.notes,
            })

        nav = total_market_value + portfolio.cash + portfolio.total_receivable
        total_unrealized_pnl = total_market_value - total_cost
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0

        # Tính tỷ trọng
        for p in enriched_positions:
            p["weight_pct"] = round(p["market_value"] / nav * 100, 2) if nav > 0 else 0.0

        cash_weight = round(portfolio.cash / nav * 100, 2) if nav > 0 else 0.0

        return {
            "positions": sorted(enriched_positions, key=lambda x: x["market_value"], reverse=True),
            "total_market_value": round(total_market_value),
            "total_cost": round(total_cost),
            "total_unrealized_pnl": round(total_unrealized_pnl),
            "total_unrealized_pnl_pct": round(total_unrealized_pnl_pct, 2),
            "nav": round(nav),
            "cash": round(portfolio.cash),
            "t1_receivable": round(portfolio.t1_receivable),
            "t2_receivable": round(portfolio.t2_receivable),
            "cash_weight_pct": cash_weight,
        }

    def get_summary(self) -> dict[str, Any]:
        """Tóm tắt portfolio không cần giá thị trường."""
        portfolio = self.portfolio
        return {
            "num_positions": len(portfolio.positions),
            "symbols": [p.symbol for p in portfolio.positions],
            "total_qty_value": sum(p.qty * p.avg_cost for p in portfolio.positions),
            "cash": portfolio.cash,
            "t1_receivable": portfolio.t1_receivable,
            "t2_receivable": portfolio.t2_receivable,
            "updated_at": portfolio.updated_at,
        }

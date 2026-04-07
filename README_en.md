# VN Stock Trader — Claude Code Plugin for Vietnamese Stock Markets

[![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-Plugin-blue)](https://github.com/hieutran/vn-stock-trader)
[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://github.com/hieutran/vn-stock-trader/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Claude Code plugin for Vietnamese stock traders — real-time market data, portfolio management, technical/fundamental analysis, automated alerts, and news monitoring in one place.

---

## Features

| Feature | Count | Description |
|---------|-------|-------------|
| **MCP Tools** | 11 | Real-time data: price, history, financials, news, screener, portfolio, insider trades |
| **Skills** | 10 | TA, FA, News Impact, Portfolio Review, Screener, Sector Compare, Morning Brief, Session Summary, Portfolio Monitor, Watchlist |
| **Slash Commands** | 8 | `/analyze`, `/screen`, `/portfolio`, `/news`, `/compare`, `/report`, `/alert`, `/trading-session` |
| **Agents** | 4 | Market Watcher, News Analyst, Portfolio Manager, Research Agent |

---

## Installation

### Requirements

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **[Claude Code](https://claude.ai/claude-code)** — CLI tool from Anthropic

### Option 1: Plugin Install (Recommended)

```bash
# Clone repo
git clone https://github.com/hieutran/vn-stock-trader.git
cd vn-stock-trader

# Run installer
./install.sh
```

Then in Claude Code:

```
# Register marketplace
/plugin marketplace add ./path/to/vn-stock-trader

# Install plugin
/plugin install vn-stock-trader@vn-stock-trader
```

### Option 2: Install from GitHub

```
# In Claude Code
/plugin marketplace add github:hieutran/vn-stock-trader
/plugin install vn-stock-trader@vn-stock-trader
```

### Option 3: Development Mode

```bash
# Load directly for development
claude --plugin-dir ./path/to/vn-stock-trader
```

### Option 4: Manual Setup

```bash
# Clone and install dependencies
git clone https://github.com/hieutran/vn-stock-trader.git
cd vn-stock-trader
uv sync

# Verify
uv run python -c "import vnstock; import pandas_ta; print('OK')"
uv run pytest mcp-server/tests/ -q   # 102+ tests should pass
```

Add the MCP server to your project's `.mcp.json` or global `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "vn-stock-trader": {
      "command": "uv",
      "args": ["run", "python", "mcp-server/server.py"],
      "cwd": "/path/to/vn-stock-trader"
    }
  }
}
```

Verify the MCP server:
```bash
uv run mcp dev mcp-server/server.py
```

---

## 🛠️ Project Structure

```
vn-stock-trader/
├── mcp-server/               # Python MCP server
│   ├── server.py             # Entry point (FastMCP)
│   ├── tools/                # 11 MCP tools
│   │   ├── market.py         # get_stock_price, get_market_overview, get_top_movers
│   │   ├── history.py        # get_stock_history (OHLCV + TA indicators)
│   │   ├── financials.py     # get_financial_report, get_sector_peers
│   │   ├── news.py           # get_news
│   │   ├── screener.py       # screen_stocks
│   │   ├── portfolio.py      # get_portfolio, update_portfolio
│   │   └── insider.py        # get_insider_trades
│   ├── data_sources/         # Data layer
│   │   ├── vnstock_client.py  # vnstock3 wrapper with SQLite cache
│   │   ├── vietstock_client.py# Vietstock data source
│   │   ├── news_scraper.py    # 7 news sources: CafeF, VnEconomy, VNExpress,
│   │   │                      # Tin Nhanh CK, VietnamBiz, HNX, Bao Dau tu
│   │   ├── ta_calculator.py   # pandas-ta indicators
│   │   └── portfolio.py       # Portfolio data model
│   ├── cache/                # SQLite cache module
│   └── tests/                # 102+ pytest tests
├── scripts/                  # Automation scripts
│   ├── morning_brief.py      # Pre-market summary (8:30 AM)
│   ├── session_summary.py    # Post-market summary (2:50 PM)
│   ├── portfolio_monitor.py  # Live monitoring during session
│   └── watchlist_alert.py    # Check watchlist conditions
├── .claude/
│   ├── skills/               # 10 skills (auto-triggered)
│   ├── commands/             # 8 slash commands
│   └── agents/               # 4 specialized agents
└── data/
    ├── portfolio.json         # Your holdings
    ├── watchlist.json         # Watchlist + alert conditions
    └── automation_config.json # Automation configuration
```

---

## 💬 Usage with Claude Code

### Slash Commands

```
/analyze VNM              # Full analysis for VNM (TA + FA + News)
/analyze HPG              # Full analysis for HPG
/screen value             # Screen stocks by value strategy
/screen growth            # Screen by growth
/screen momentum          # Screen by momentum
/portfolio                # Review current portfolio
/news VNM                 # News and impact analysis for VNM
/compare VNM HPG          # Compare 2 stocks
/report daily             # Today's market report
/report weekly            # Weekly market report
/alert VNM 70000          # Set price alert for VNM
```

### Natural Language (Skills auto-trigger)

```
# Technical Analysis
"Technical analysis for VNM"
"What are RSI and MACD levels for HPG right now?"
"Is VCB at support or resistance?"

# Fundamental Analysis
"P/E and P/B of MBB vs sector?"
"ACB Q4/2025 financial report"
"What is the fair value of FPT?"

# News & Impact
"What news is affecting VNM today?"
"What catalyst is driving HPG higher?"

# Portfolio
"Review my portfolio"
"Which sector is my portfolio too concentrated in?"
"How should I rebalance my portfolio?"

# Sector Comparison
"Compare banks: ACB, MBB, VCB, TCB"
"Which real estate stock is cheapest vs peers?"
```

### Direct MCP Tool Calls

```python
# In Python code or other tools
from mcp_client import call_tool

# Get stock price
result = await call_tool("get_stock_price", {"symbol": "VNM"})

# Get financial report
result = await call_tool("get_financial_report", {"symbol": "VNM", "num_quarters": 4})

# Manage portfolio
result = await call_tool("update_portfolio", {
    "action": "buy",
    "symbol": "HPG",
    "qty": 1000,
    "price": 28500
})
```

---

## 📊 MCP Tools Reference

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_stock_price` | `symbol` | Current price + OHLCV + foreign flow |
| `get_market_overview` | — | VN-Index, HNX, UPCOM, breadth, liquidity |
| `get_top_movers` | `exchange`, `n` | Top gainers/losers/volume |
| `get_stock_history` | `symbol`, `period`, `include_indicators` | Historical OHLCV + TA indicators |
| `get_financial_report` | `symbol`, `num_quarters`, `report_type` | Financials, P/E, P/B, ROE, EPS |
| `get_sector_peers` | `symbol` | Stocks in the same sector |
| `get_news` | `symbol`, `category`, `limit` | Market and company news |
| `screen_stocks` | `preset`, `filters`, `limit` | Filter stocks by criteria |
| `get_portfolio` | — | Portfolio + live P&L |
| `update_portfolio` | `action`, `symbol`, `qty`, `price` | Buy/sell/remove positions |
| `get_insider_trades` | `symbol`, `limit` | Insider transactions |

---

## 🤖 Automation Scripts

### Morning Brief (8:30 AM)
```bash
uv run python scripts/morning_brief.py           # Output to file + stdout
uv run python scripts/morning_brief.py --force   # Skip holiday check
uv run python scripts/morning_brief.py --output stdout
```

Output: `data/briefs/YYYY-MM-DD.md`

### Session Summary (2:50 PM after ATC)
```bash
uv run python scripts/session_summary.py
uv run python scripts/session_summary.py --quick   # Market + P&L only
```

Output: `data/summaries/YYYY-MM-DD.md`

### Portfolio Monitor (run during session)
```bash
# Run continuously every 5 minutes
uv run python scripts/portfolio_monitor.py

# Custom interval
uv run python scripts/portfolio_monitor.py --interval 300

# Run once
uv run python scripts/portfolio_monitor.py --once
```

Alert conditions:
- Stock changes > 5% vs reference price
- Volume spike > 3× 20-session average
- Approaching ceiling/floor (within 1%)
- VN-Index changes > 1%

### Watchlist Alert
```bash
uv run python scripts/watchlist_alert.py           # Check all alerts
uv run python scripts/watchlist_alert.py --status  # Print current prices for all watchlist stocks
uv run python scripts/watchlist_alert.py --dry-run # Preview without logging
```

### Watchlist Alert Configuration (`data/watchlist.json`)

```json
{
  "symbols": ["HPG", "ACB", "MBB", "FPT", "VHM"],
  "alerts": [
    {"symbol": "HPG", "condition": "price_below", "value": 28000, "note": "Support zone"},
    {"symbol": "ACB", "condition": "price_above", "value": 30000, "note": "Breakout"},
    {"symbol": "MBB", "condition": "pct_change_above", "value": 5.0, "note": "Strong move up"},
    {"symbol": "VHM", "condition": "near_ceiling", "value": 1.0, "note": "Approaching ceiling"},
    {"symbol": "FPT", "condition": "pct_change_below", "value": -5.0, "note": "Stop loss"}
  ]
}
```

**Supported conditions:**
- `price_below` — Price ≤ value
- `price_above` — Price ≥ value
- `pct_change_above` — Daily % change ≥ value
- `pct_change_below` — Daily % change ≤ value
- `near_ceiling` — Within ≤ value% of ceiling price
- `near_floor` — Within ≤ value% of floor price

---

## 📁 Portfolio Management (`data/portfolio.json`)

```json
{
  "positions": [
    {
      "symbol": "VNM",
      "qty": 1000,
      "avg_cost": 72000,
      "purchase_date": "2026-01-15",
      "notes": "Bought at MA200 support zone"
    }
  ],
  "cash": 50000000,
  "t1_receivable": 0,
  "t2_receivable": 0
}
```

Or use MCP tools to update:
```
"Buy 1000 HPG at 28500"
"Sell 500 VNM at 76000"
```

---

## ⚙️ Automation Configuration (`data/automation_config.json`)

```json
{
  "alert_thresholds": {
    "price_change_pct": 5.0,
    "volume_spike_ratio": 3.0,
    "near_ceiling_pct": 1.0
  },
  "trading_hours": {
    "morning_open": "09:00",
    "morning_close": "11:30",
    "afternoon_open": "13:00",
    "afternoon_close": "14:45"
  },
  "telegram": {
    "enabled": false,
    "bot_token": "",
    "chat_id": ""
  }
}
```

---

## 📰 Data Sources

### Market Data
| Source | Data Types |
|--------|-----------|
| **TCBS** (via vnstock3) | Real-time price, historical OHLCV, financials, insider trades |
| **VCI** (via vnstock3) | Fallback/backup for price data |
| **Vietstock** | Supplementary data |

### News Sources (7 sources)
| Source | URL | Method |
|--------|-----|--------|
| **CafeF** | cafef.vn/thi-truong-chung-khoan.chn | HTML scraping |
| **VnEconomy** | vneconomy.vn/chung-khoan.rss | RSS |
| **VNExpress** | vnexpress.net/kinh-doanh/chung-khoan | HTML scraping |
| **Tin Nhanh Chung Khoan** | tinnhanhchungkhoan.vn/chung-khoan | HTML scraping |
| **VietnamBiz** | vietnambiz.vn/chung-khoan.rss | RSS |
| **HNX** | hnx.vn/tin-tuc-su-kien-ttcbhnx | HTML scraping |
| **Bao Dau tu** | baodautu.vn/dau-tu-tai-chinh-d6 | HTML scraping |

---

## 🧪 Tests

```bash
# Run all tests
uv run pytest mcp-server/tests/ -v

# With coverage report
uv run pytest mcp-server/tests/ --cov=mcp-server --cov-report=term-missing

# Automation scripts only
uv run pytest mcp-server/tests/test_automation.py -v

# Lint
uv run ruff check mcp-server/ scripts/
```

---

## 🏗️ Architecture

```
Claude Code (chat)
    │
    ├── Skills (auto-triggered by context)
    │   └── technical-analysis, fundamental-analysis, news-impact, ...
    │
    ├── Commands (/analyze, /screen, ...)
    │   └── Markdown templates → call MCP tools
    │
    ├── Agents (subagents for complex tasks)
    │   └── market-watcher, research-agent, portfolio-manager, ...
    │
    └── MCP Tools (interface with data layer)
        │
        ├── data_sources/vnstock_client.py   ──→ vnstock3 API (TCBS/VCI)
        ├── data_sources/vietstock_client.py ──→ Vietstock API
        ├── data_sources/news_scraper.py     ──→ CafeF, VnEconomy, VNExpress,
        │                                        Tin Nhanh CK, VietnamBiz,
        │                                        HNX, Bao Dau tu
        ├── data_sources/ta_calculator.py    ──→ pandas-ta
        ├── data_sources/portfolio.py        ──→ data/portfolio.json
        └── cache/cache.py                   ──→ SQLite (TTL cache)
```

**Cache TTL:**
| Data Type | TTL |
|-----------|-----|
| Stock price | 15 minutes |
| Market overview | 10 minutes |
| Price history | 60 minutes |
| Financial reports | 24 hours |
| News | 10 minutes |

---

## Vietnamese Market Specifics

| Aspect | Details |
|--------|---------|
| **Exchanges** | HOSE (large-cap), HNX (mid-cap), UPCOM (small-cap/OTC) |
| **Price bands** | HOSE ±7%, HNX ±10%, UPCOM ±15% |
| **Settlement** | T+2 (can sell 2 trading days after purchase) |
| **Trading hours** | 9:00–11:30 (morning), 13:00–14:30 (afternoon) + ATO/ATC auctions |
| **Currency** | All prices in VND |
| **Coverage** | ~1,700 listed stocks |
| **Data delay** | ~15 minutes (not real-time) |

---

## ⚠️ Limitations

- **~15-minute data delay** — not real-time; not suitable for high-frequency day trading
- **TCBS dependency** — relies on TCBS API, which may change without notice
- **No order execution** — read-only; cannot connect to a broker to place orders
- **Vietnam market only** — supports HOSE, HNX, UPCOM only (no US stocks, crypto, etc.)
- **T+2 settlement** — portfolio updates must account for T+2 manually

---

## 📜 License

MIT License — see [LICENSE](LICENSE)

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Commit: `git commit -m "feat: add your feature"`
4. Push: `git push origin feat/your-feature`
5. Open a Pull Request

---

_Built with ❤️ for Vietnamese stock traders using Claude Code and vnstock3_

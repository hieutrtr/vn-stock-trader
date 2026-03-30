# CLAUDE.md — VN Stock Trader

## 1. PROJECT OVERVIEW

**Purpose:** Claude plugins/skills for Vietnamese stock traders — market analysis, trading tools, broker integrations.

**Status:** Phase 1 complete. MCP server built and tested (102 tests passing). Skills, commands, and agents configured.

**Tech stack:** Python 3.12, FastMCP (mcp library), vnstock3, pandas, pandas-ta, SQLite cache.

### What's Built
- **MCP server** (`mcp-server/`) — 11 tools exposing VN stock market data
- **6 Skills** — technical-analysis, fundamental-analysis, news-impact, portfolio-review, stock-screener, sector-compare
- **7 Commands** — /analyze, /screen, /portfolio, /news, /compare, /report, /alert
- **4 Agents** — market-watcher, news-analyst, portfolio-manager, research-agent

## 2. BUILD & TEST COMMANDS

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest mcp-server/tests/ -v

# Run tests with coverage
uv run pytest mcp-server/tests/ --cov=mcp-server

# Lint/format
uv run ruff check mcp-server/
uv run ruff format mcp-server/

# Start MCP server (stdio transport — used by Claude Code)
uv run python mcp-server/server.py

# MCP dev inspector (interactive tool testing)
uv run mcp dev mcp-server/server.py
```

## 3. PROJECT STRUCTURE

```
vn-stock-trader/
├── CLAUDE.md                          # This file
├── .mcp.json                          # MCP server registration for Claude Code
├── pyproject.toml                     # Python project config (uv, ruff, pytest)
├── mcp-server/
│   ├── server.py                      # FastMCP entry point — runs with stdio transport
│   ├── tools/
│   │   ├── market.py                  # get_stock_price, get_market_overview, get_top_movers
│   │   ├── history.py                 # get_stock_history (OHLCV + TA indicators)
│   │   ├── financials.py              # get_financial_report, get_sector_peers
│   │   ├── news.py                    # get_news
│   │   ├── screener.py                # screen_stocks
│   │   ├── portfolio.py               # get_portfolio, update_portfolio
│   │   └── insider.py                 # get_insider_trades
│   ├── core/
│   │   ├── vnstock_client.py          # vnstock3 wrapper with caching
│   │   ├── ta_calculator.py           # Technical indicator calculations
│   │   └── cache.py                   # SQLite-backed TTL cache
│   └── tests/                         # 102 tests (pytest)
│       ├── test_mcp_tools.py
│       ├── test_cache.py
│       ├── test_portfolio.py
│       ├── test_ta_calculator.py
│       └── test_vnstock_client.py
├── .claude/
│   ├── settings.json                  # Tool permissions
│   ├── settings.local.json            # Claude Bridge hook (post-session callback)
│   ├── skills/                        # 6 skill definitions (SKILL.md files)
│   │   ├── technical-analysis/
│   │   ├── fundamental-analysis/
│   │   ├── news-impact/
│   │   ├── portfolio-review/
│   │   ├── stock-screener/
│   │   └── sector-compare/
│   ├── commands/                      # 7 slash commands
│   │   ├── analyze.md
│   │   ├── screen.md
│   │   ├── portfolio.md
│   │   ├── news.md
│   │   ├── compare.md
│   │   ├── report.md
│   │   └── alert.md
│   └── agents/                        # 4 specialized agents
│       ├── market-watcher.md
│       ├── news-analyst.md
│       ├── portfolio-manager.md
│       └── research-agent.md
└── docs/
    ├── EXTENSION_AUDIT.md             # Full audit of skills/commands/agents/MCP
    └── ...
```

## 4. MCP TOOLS

All tools use prefix `mcp__vn-stock-trader__`:

| Tool | Description |
|------|-------------|
| `get_stock_price` | Giá hiện tại, OHLCV, trần/sàn |
| `get_market_overview` | VN-Index, HNX, breadth, foreign flow |
| `get_top_movers` | Top tăng/giảm/volume |
| `get_stock_history` | OHLCV lịch sử + TA indicators (MA, RSI, MACD, BB, ATR) |
| `get_financial_report` | BCTC, P/E, P/B, ROE, EPS (4 quý gần nhất) |
| `get_sector_peers` | Cổ phiếu cùng ngành |
| `get_news` | Tin tức thị trường và doanh nghiệp |
| `screen_stocks` | Lọc cổ phiếu theo tiêu chí tài chính/kỹ thuật |
| `get_portfolio` | Danh mục + P&L hiện tại |
| `update_portfolio` | Mua/bán/cập nhật vị thế |
| `get_insider_trades` | Giao dịch nội bộ (cổ đông, ban lãnh đạo) |

## 5. SKILLS (Auto-triggered)

Skills are in `.claude/skills/` and Claude Code auto-invokes them based on `description`:

| Skill | Trigger | Tools Used |
|-------|---------|-----------|
| `technical-analysis` | TA, chart, RSI, MACD, hỗ trợ/kháng cự | `get_stock_price`, `get_stock_history` |
| `fundamental-analysis` | FA, P/E, P/B, ROE, BCTC, định giá | `get_stock_price`, `get_financial_report`, `get_sector_peers` |
| `news-impact` | tin tức, news, catalyst, sentiment | `get_news`, `WebSearch`, `WebFetch` |
| `portfolio-review` | review danh mục, phân bổ, tái cơ cấu | `get_portfolio`, `get_stock_price`, `get_stock_history`, `get_financial_report`, `get_sector_peers` |
| `stock-screener` | lọc cổ phiếu, screener, scan | `screen_stocks`, `get_stock_price`, `get_financial_report` |
| `sector-compare` | so sánh ngành, peer analysis | `get_sector_peers`, `get_stock_price`, `get_financial_report`, `get_stock_history` |

## 6. COMMANDS

```
/analyze <SYMBOL>          # TA + FA + News combined analysis
/screen [strategy]         # Stock screener với preset strategies
/portfolio                 # Review danh mục hiện tại
/news <SYMBOL>             # Tin tức và impact analysis
/compare <SYM1> <SYM2>    # So sánh 2 cổ phiếu
/report [daily|weekly]     # Báo cáo thị trường
/alert <SYMBOL> <price>    # Đặt cảnh báo giá
```

## 7. AGENTS

| Agent | Purpose | Tools |
|-------|---------|-------|
| `market-watcher` | Giám sát thị trường, alert volume spike | `get_stock_price`, `get_market_overview`, `get_top_movers`, `get_portfolio` |
| `news-analyst` | Phân tích tin tức, sentiment | `get_news`, `get_stock_price`, `get_portfolio`, `WebSearch`, `WebFetch` |
| `portfolio-manager` | Quản lý danh mục, P&L, rebalancing | `get_portfolio`, `get_stock_price`, `get_stock_history`, `get_financial_report`, `update_portfolio` |
| `research-agent` | Deep-dive research 1500+ từ | `get_stock_price`, `get_stock_history`, `get_financial_report`, `get_sector_peers`, `get_news`, `get_insider_trades`, `WebFetch` |

## 8. CONVENTIONS

- **Language:** Python 3.12
- **Formatting:** `ruff` (line-length 100, double quotes)
- **Testing:** `pytest` with `pytest-asyncio`; all tests in `mcp-server/tests/`
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- **VN market specifics:** Prices in VNĐ, T+2 settlement, HOSE ±7% / HNX ±10% / UPCOM ±15% bands

## 9. AGENT CONTEXT

This project has a dedicated Bridge agent (`vn-stock-trader--vn-stock-trader`).

**Primary focus:** Build Claude plugins/skills for Vietnamese stock traders — market analysis, trading tools, broker integrations.

When working on tasks, prioritize:
- Vietnamese market specifics (VND currency, T+2 settlement, trading sessions, price bands)
- Integration with local broker APIs
- Data sources relevant to VN equities (SSI iBoard, VNDirect, CafeF, Vietstock)
- Regulatory context (State Securities Commission of Vietnam rules)

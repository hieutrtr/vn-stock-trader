# VN Stock Trader — Claude Code Plugin for Vietnamese Stock Markets

[![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-Plugin-blue)](https://github.com/hieutran/vn-stock-trader)
[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://github.com/hieutran/vn-stock-trader/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bộ plugins/skills/commands cho Claude Code giúp trader chứng khoán Việt Nam phân tích thị trường, quản lý danh mục, và nhận cảnh báo tự động.

---

## Tính năng

| Tính năng | Số lượng | Mô tả |
|-----------|---------|-------|
| **MCP Tools** | 11 | Dữ liệu realtime: giá, lịch sử, BCTC, tin tức, screener, danh mục, insider |
| **Skills** | 10 | TA, FA, News Impact, Portfolio Review, Screener, Sector Compare, Morning Brief, Session Summary, Portfolio Monitor, Watchlist |
| **Slash Commands** | 8 | `/analyze`, `/screen`, `/portfolio`, `/news`, `/compare`, `/report`, `/alert`, `/trading-session` |
| **Agents** | 4 | Market Watcher, News Analyst, Portfolio Manager, Research Agent |

---

## Cài đặt

### Yêu cầu

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **[Claude Code](https://claude.ai/claude-code)** — CLI tool từ Anthropic

### Cách 1: Plugin Install (Khuyến nghị)

```bash
# Clone repo
git clone https://github.com/hieutran/vn-stock-trader.git
cd vn-stock-trader

# Chạy installer
./install.sh
```

Sau đó trong Claude Code:

```
# Đăng ký marketplace
/plugin marketplace add ./path/to/vn-stock-trader

# Cài đặt plugin
/plugin install vn-stock-trader@vn-stock-trader
```

### Cách 2: Install từ GitHub

```
# Trong Claude Code
/plugin marketplace add github:hieutran/vn-stock-trader
/plugin install vn-stock-trader@vn-stock-trader
```

### Cách 3: Development Mode

```bash
# Load trực tiếp để phát triển
claude --plugin-dir ./path/to/vn-stock-trader
```

### Cách 4: Manual Setup

```bash
# Clone và cài dependencies
git clone https://github.com/hieutran/vn-stock-trader.git
cd vn-stock-trader
uv sync

# Verify
uv run python -c "import vnstock; import pandas_ta; print('OK')"
uv run pytest mcp-server/tests/ -q   # 102+ tests should pass
```

Thêm MCP server vào `.mcp.json` của project hoặc `~/.claude/mcp.json` toàn cục:

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

Kiểm tra MCP server:
```bash
uv run mcp dev mcp-server/server.py
```

---

## 🛠️ Cấu trúc Project

```
vn-stock-trader/
├── mcp-server/               # MCP server Python
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
│   │   ├── vnstock_client.py # vnstock3 wrapper với SQLite cache
│   │   ├── news_scraper.py   # CafeF / Vietstock crawler
│   │   ├── ta_calculator.py  # pandas-ta indicators
│   │   └── portfolio.py      # Portfolio data model
│   ├── cache/                # SQLite cache module
│   └── tests/                # 102+ pytest tests
├── scripts/                  # Automation scripts
│   ├── morning_brief.py      # Tổng hợp trước phiên (8:30)
│   ├── session_summary.py    # Tổng kết phiên (14:50)
│   ├── portfolio_monitor.py  # Monitor liên tục trong phiên
│   └── watchlist_alert.py    # Check watchlist conditions
├── .claude/
│   ├── skills/               # 10 skills (auto-triggered)
│   ├── commands/             # 8 slash commands
│   └── agents/               # 4 specialized agents
└── data/
    ├── portfolio.json         # Danh mục đầu tư
    ├── watchlist.json         # Watchlist + alert conditions
    └── automation_config.json # Cấu hình automation
```

---

## 💬 Sử dụng với Claude Code

### Slash Commands

```
/analyze VNM              # Phân tích toàn diện VNM (TA + FA + News)
/analyze HPG              # Phân tích HPG
/screen value             # Lọc cổ phiếu theo chiến lược value
/screen growth            # Lọc tăng trưởng
/screen momentum          # Lọc momentum
/portfolio                # Review danh mục hiện tại
/news VNM                 # Tin tức và impact analysis cho VNM
/compare VNM HPG          # So sánh 2 cổ phiếu
/report daily             # Báo cáo thị trường hôm nay
/report weekly            # Báo cáo tuần
/alert VNM 70000          # Đặt cảnh báo giá cho VNM
```

### Hỏi tự nhiên (Skills auto-trigger)

```
# Technical Analysis
"Phân tích kỹ thuật VNM"
"RSI và MACD của HPG hiện tại như thế nào?"
"VCB đang ở vùng hỗ trợ hay kháng cự?"

# Fundamental Analysis
"P/E và P/B của MBB so với ngành?"
"BCTC quý 4/2025 của ACB"
"Định giá hợp lý của FPT là bao nhiêu?"

# News & Impact
"Tin tức gì ảnh hưởng đến VNM hôm nay?"
"Catalyst nào đang thúc đẩy HPG tăng?"

# Portfolio
"Review danh mục của tôi"
"Danh mục của tôi tập trung quá vào ngành nào?"
"Nên rebalance danh mục như thế nào?"

# Sector Comparison
"So sánh các ngân hàng: ACB, MBB, VCB, TCB"
"Cổ phiếu bất động sản nào đang rẻ nhất so với peers?"
```

### MCP Tools trực tiếp

```python
# Trong code Python hoặc tools khác
from mcp_client import call_tool

# Lấy giá cổ phiếu
result = await call_tool("get_stock_price", {"symbol": "VNM"})

# Lấy BCTC
result = await call_tool("get_financial_report", {"symbol": "VNM", "num_quarters": 4})

# Quản lý danh mục
result = await call_tool("update_portfolio", {
    "action": "buy",
    "symbol": "HPG",
    "qty": 1000,
    "price": 28500
})
```

---

## 📊 MCP Tools Reference

| Tool | Tham số | Mô tả |
|------|---------|-------|
| `get_stock_price` | `symbol` | Giá hiện tại + OHLCV + khối ngoại |
| `get_market_overview` | — | VN-Index, HNX, UPCOM, breadth, thanh khoản |
| `get_top_movers` | `exchange`, `n` | Top tăng/giảm/volume |
| `get_stock_history` | `symbol`, `period`, `include_indicators` | OHLCV lịch sử + TA indicators |
| `get_financial_report` | `symbol`, `num_quarters`, `report_type` | BCTC, P/E, P/B, ROE, EPS |
| `get_sector_peers` | `symbol` | Cổ phiếu cùng ngành |
| `get_news` | `symbol`, `category`, `limit` | Tin tức thị trường/doanh nghiệp |
| `screen_stocks` | `preset`, `filters`, `limit` | Lọc cổ phiếu theo tiêu chí |
| `get_portfolio` | — | Danh mục + P&L live |
| `update_portfolio` | `action`, `symbol`, `qty`, `price` | Mua/bán/xóa vị thế |
| `get_insider_trades` | `symbol`, `limit` | Giao dịch nội bộ |

---

## 🤖 Automation Scripts

### Morning Brief (8:30 sáng)
```bash
uv run python scripts/morning_brief.py           # Output ra file + stdout
uv run python scripts/morning_brief.py --force   # Bỏ qua check ngày lễ
uv run python scripts/morning_brief.py --output stdout
```

Output: `data/briefs/YYYY-MM-DD.md`

### Session Summary (14:50 sau ATC)
```bash
uv run python scripts/session_summary.py
uv run python scripts/session_summary.py --quick   # Chỉ market + P&L
```

Output: `data/summaries/YYYY-MM-DD.md`

### Portfolio Monitor (chạy trong phiên)
```bash
# Chạy liên tục mỗi 5 phút
uv run python scripts/portfolio_monitor.py

# Tùy chỉnh interval
uv run python scripts/portfolio_monitor.py --interval 300

# Chạy một lần
uv run python scripts/portfolio_monitor.py --once
```

Alert conditions:
- Cổ phiếu thay đổi > 5% so với tham chiếu
- Volume spike > 3× trung bình 20 phiên
- Sắp chạm trần/sàn (còn < 1%)
- VN-Index thay đổi > 1%

### Watchlist Alert
```bash
uv run python scripts/watchlist_alert.py           # Check tất cả alerts
uv run python scripts/watchlist_alert.py --status  # In giá hiện tại toàn bộ watchlist
uv run python scripts/watchlist_alert.py --dry-run # Preview không ghi log
```

### Cấu hình Watchlist Alerts (`data/watchlist.json`)

```json
{
  "symbols": ["HPG", "ACB", "MBB", "FPT", "VHM"],
  "alerts": [
    {"symbol": "HPG", "condition": "price_below", "value": 28000, "note": "Vùng hỗ trợ"},
    {"symbol": "ACB", "condition": "price_above", "value": 30000, "note": "Breakout"},
    {"symbol": "MBB", "condition": "pct_change_above", "value": 5.0, "note": "Tăng mạnh"},
    {"symbol": "VHM", "condition": "near_ceiling", "value": 1.0, "note": "Sắp chạm trần"},
    {"symbol": "FPT", "condition": "pct_change_below", "value": -5.0, "note": "Stop loss"}
  ]
}
```

**Conditions hỗ trợ:**
- `price_below` — Giá ≤ value
- `price_above` — Giá ≥ value
- `pct_change_above` — % thay đổi ngày ≥ value
- `pct_change_below` — % thay đổi ngày ≤ value
- `near_ceiling` — Còn ≤ value% đến trần
- `near_floor` — Còn ≤ value% đến sàn

---

## 📁 Quản lý Danh mục (`data/portfolio.json`)

```json
{
  "positions": [
    {
      "symbol": "VNM",
      "qty": 1000,
      "avg_cost": 72000,
      "purchase_date": "2026-01-15",
      "notes": "Mua tại vùng hỗ trợ MA200"
    }
  ],
  "cash": 50000000,
  "t1_receivable": 0,
  "t2_receivable": 0
}
```

Hoặc dùng MCP tool để cập nhật:
```
"Mua 1000 HPG giá 28500"
"Bán 500 VNM giá 76000"
```

---

## ⚙️ Cấu hình Automation (`data/automation_config.json`)

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

## 🧪 Tests

```bash
# Chạy tất cả tests
uv run pytest mcp-server/tests/ -v

# Với coverage report
uv run pytest mcp-server/tests/ --cov=mcp-server --cov-report=term-missing

# Chỉ test automation scripts
uv run pytest mcp-server/tests/test_automation.py -v

# Lint
uv run ruff check mcp-server/ scripts/
```

---

## 🏗️ Architecture

```
Claude Code (chat)
    │
    ├── Skills (auto-trigger theo context)
    │   └── technical-analysis, fundamental-analysis, news-impact, ...
    │
    ├── Commands (/analyze, /screen, ...)
    │   └── Markdown templates → gọi MCP tools
    │
    ├── Agents (subagents cho task phức tạp)
    │   └── market-watcher, research-agent, portfolio-manager, ...
    │
    └── MCP Tools (giao tiếp với data layer)
        │
        ├── data_sources/vnstock_client.py  ──→ vnstock3 API (TCBS/VCI)
        ├── data_sources/news_scraper.py    ──→ CafeF, Vietstock, VNExpress
        ├── data_sources/ta_calculator.py   ──→ pandas-ta
        ├── data_sources/portfolio.py       ──→ data/portfolio.json
        └── cache/cache.py                  ──→ SQLite (TTL cache)
```

**Cache TTL:**
| Loại dữ liệu | TTL |
|-------------|-----|
| Giá cổ phiếu | 15 phút |
| Market overview | 10 phút |
| Lịch sử giá | 60 phút |
| BCTC | 24 giờ |
| Tin tức | 10 phút |

---

## ⚠️ Giới hạn

- **Dữ liệu delay ~15 phút** — không phải realtime, không dùng cho day trading tần suất cao
- **Nguồn: TCBS** — phụ thuộc vào API của TCBS, có thể thay đổi
- **Không thể đặt lệnh** — chỉ đọc dữ liệu, không kết nối broker để giao dịch
- **Thị trường VN** — chỉ hỗ trợ HOSE, HNX, UPCOM (không phải US stocks, crypto, ...)
- **T+2 settlement** — cập nhật danh mục phải tính thủ công T+2

---

## 📜 License

MIT License — xem [LICENSE](LICENSE)

---

## 🤝 Contributing

1. Fork repo
2. Tạo branch: `git checkout -b feat/your-feature`
3. Commit: `git commit -m "feat: add your feature"`
4. Push: `git push origin feat/your-feature`
5. Tạo Pull Request

---

_Built with ❤️ for Vietnamese stock traders using Claude Code and vnstock3_

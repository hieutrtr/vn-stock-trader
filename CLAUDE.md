# CLAUDE.md — VN Stock Trader

## 1. PROJECT OVERVIEW

**Purpose:** Claude plugins/skills for Vietnamese stock traders — market analysis, trading tools, broker integrations.

**Status:** Phase 1 complete. MCP server built and tested (102 tests passing). Skills, commands, and agents configured.

**Tech stack:** Python 3.12, FastMCP (mcp library), vnstock3, pandas, pandas-ta, SQLite cache.

### What's Built
- **MCP server** (`mcp-server/`) — 11 tools exposing VN stock market data
- **10 Skills** — morning-brief, session-summary, portfolio-monitor, watchlist-check, technical-analysis, fundamental-analysis, news-impact, portfolio-review, stock-screener, sector-compare
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
│   ├── skills/                        # 10 skill definitions (SKILL.md files)
│   │   ├── morning-brief/
│   │   ├── session-summary/
│   │   ├── portfolio-monitor/
│   │   ├── watchlist-check/
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

Skills are in `.claude/skills/` and Claude Code auto-invokes them based on `description`.

### 5.1 Workflow Skills (Theo lịch / lặp lại)

| Skill | Trigger Keywords | Allowed Tools | Mô tả |
|-------|-----------------|---------------|-------|
| `morning-brief` | "morning brief", "tóm tắt trước phiên", "trước khi mở cửa" | `get_market_overview`, `get_portfolio`, `get_news`, `get_stock_price` | Tổng hợp thị trường + danh mục + tin tức trước 9h; chạy thủ công mỗi sáng giao dịch |
| `session-summary` | "tổng kết phiên", "session summary", "kết thúc phiên", "cuối ngày" | `get_market_overview`, `get_portfolio`, `get_top_movers`, `get_news` | Tổng kết phiên: P&L danh mục, market recap, top movers, action items cho ngày mai |
| `portfolio-monitor` | "monitor danh mục", "giám sát vị thế", "portfolio alert" | `get_stock_price`, `get_portfolio` | Giám sát danh mục trong phiên; phát hiện volume spike, giá chạm trần/sàn, biến động >3%; được Bridge Bot tự động gọi định kỳ |
| `watchlist-check` | "check watchlist", "kiểm tra watchlist", "watchlist alert" | `get_stock_price` | Đọc `data/watchlist.json`, kiểm tra điều kiện giá (price_above/below, pct_change, near_ceiling/floor); được Bridge Bot tự động gọi định kỳ |

### 5.2 Analysis Skills (Theo yêu cầu)

| Skill | Trigger Keywords | Allowed Tools | Mô tả |
|-------|-----------------|---------------|-------|
| `technical-analysis` | chart, RSI, MACD, hỗ trợ, kháng cự, support, resistance, TA, tín hiệu mua/bán kỹ thuật | `get_stock_price`, `get_stock_history` | Phân tích xu hướng, momentum, tín hiệu mua/bán; cho điểm 6 tín hiệu; output: entry, stoploss, target cụ thể |
| `fundamental-analysis` | P/E, P/B, ROE, EPS, BCTC, định giá, FA, báo cáo tài chính | `get_stock_price`, `get_financial_report`, `get_sector_peers` | Đánh giá nội tại doanh nghiệp: valuation, tăng trưởng, sức khoẻ tài chính; output: MUA/GIỮ/BÁN + target 12 tháng |
| `news-impact` | tin tức, news, sự kiện, catalyst, sentiment | `get_news`, `WebSearch`, `WebFetch` | Phân tích sentiment và mức độ tác động tin tức (-5 đến +5); dự báo phản ứng giá ngắn hạn |
| `portfolio-review` | review danh mục, đánh giá danh mục, phân bổ tài sản, tái cơ cấu, rebalancing | `get_portfolio`, `get_stock_price`, `get_stock_history`, `get_financial_report`, `get_sector_peers` | Phân tích toàn diện danh mục: P&L, alpha vs VN-Index, concentration risk, action plan từng vị thế |
| `stock-screener` | lọc cổ phiếu, screener, scan cơ hội, tìm mã theo điều kiện | `screen_stocks`, `get_stock_price`, `get_financial_report` | Lọc ~1,700 mã theo 5 preset strategies (Growth, Value, Momentum, Dividend, Recovery) hoặc tiêu chí tuỳ chỉnh |
| `sector-compare` | so sánh ngành, peer analysis, ngành nào tốt, cổ phiếu tốt nhất trong ngành | `get_sector_peers`, `get_stock_price`, `get_financial_report`, `get_stock_history` | So sánh vị thế tương đối trong ngành: Leader/Challenger/Value Play/Laggard; sector outlook bull/bear |

## 5.3 Daily Workflow (Lịch sử dụng đề xuất)

```
☀️  Sáng (trước 9:00)
    → morning-brief
      Tổng hợp thị trường, danh mục, tin tức đêm qua

📊  Trong phiên (9:00 – 15:00) — tự động qua Bridge Bot
    → portfolio-monitor   (giám sát vị thế, alert trần/sàn/volume)
    → watchlist-check     (kiểm tra điều kiện watchlist)
    ⚠️  Automation (loop, schedule) được cài đặt bên Bridge Bot.
        Agent này chỉ chạy tasks khi được dispatch.

🔍  Khi cần phân tích sâu
    → technical-analysis <SYMBOL>   (TA, chart, tín hiệu vào/thoát)
    → fundamental-analysis <SYMBOL> (FA, định giá, outlook)
    → news-impact <SYMBOL>          (tin tức, catalyst, rủi ro sự kiện)
    → sector-compare <SYMBOL>       (so sánh peer, sector outlook)

📋  Cuối tuần / Đánh giá định kỳ
    → portfolio-review              (P&L, alpha, rebalancing plan)
    → stock-screener [strategy]     (scan cơ hội mới cho tuần tới)

🌙  Cuối phiên (sau 15:00)
    → session-summary               (P&L ngày, market recap, action items ngày mai)
```

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

## 8. OUTPUT RULES — BẮT BUỘC

> **Lý do:** Kết quả từ agent được bridge tự động gửi về Telegram cho user. Nếu không output đầy đủ trong response, user sẽ không nhận được thông tin.

### ⚠️ 8.0 QUY TẮC QUAN TRỌNG NHẤT — BRIDGE / TELEGRAM DISPATCH

Khi được dispatch task từ Bridge (Telegram), kết quả của bạn được gửi **trực tiếp về Telegram** cho user. Vì vậy:

1. **KHÔNG chạy Python scripts** (`morning_brief.py`, v.v.) để lấy kết quả — scripts lưu kết quả ra file, user **không nhận được** thông tin
2. **PHẢI dùng MCP tools trực tiếp** (`get_market_overview`, `get_portfolio`, `get_stock_price`, `get_news`, v.v.)
3. **PHẢI viết kết quả phân tích đầy đủ trong response text** — đây là cách **DUY NHẤT** user nhận được thông tin
4. Tuân thủ đúng format trong SKILL.md tương ứng với task

**❌ Ví dụ SAI:** Chạy `uv run python scripts/morning_brief.py` → kết quả lưu file, user không thấy gì

**✅ Ví dụ ĐÚNG:** Gọi `get_market_overview()` → `get_portfolio()` → `get_news()` → tổng hợp và **viết đầy đủ trong response**

---

### 8.1 Nguyên tắc cốt lõi

- **LUÔN output kết quả phân tích đầy đủ trong response** — KHÔNG chỉ lưu file hay in ra console
- **KHÔNG nói "đã lưu vào file X"** thay cho việc hiển thị nội dung — file output là phụ, response text là chính
- Output phải theo **đúng format tiếng Việt** đã định nghĩa trong mỗi SKILL.md tương ứng
- Viết output như thể user đọc trực tiếp trên **Telegram mobile** — không giả định user nhìn thấy terminal

### 8.2 Format tối ưu cho Telegram

- Ưu tiên **văn bản thuần** + emoji thay vì bảng ASCII (bảng thường vỡ layout trên mobile)
- Dùng **bold** (`**text**`) để highlight thông tin quan trọng
- Mỗi section cách nhau bởi dòng trống hoặc `---`
- Số liệu tài chính: định dạng có đơn vị rõ ràng (VD: `1,234 VNĐ`, `+2.5%`, `P/E: 12.3x`)

### 8.3 Xử lý output dài

Nếu phân tích quá dài (>1500 từ), chia thành các phần theo thứ tự ưu tiên:

1. **Tóm tắt nhanh** — 3–5 dòng: kết luận chính + hành động khuyến nghị
2. **Chi tiết chính** — nội dung phân tích đầy đủ theo format skill
3. **Phụ lục** (nếu cần) — bảng số liệu chi tiết, lịch sử

Luôn output **Phần 1** trước, sau đó mới đến Phần 2 và 3.

### 8.4 Quy tắc theo từng skill

| Skill / Command | Output bắt buộc |
|-----------------|-----------------|
| `morning-brief` | Toàn bộ brief: thị trường + danh mục + tin tức + action plan |
| `session-summary` | P&L ngày + market recap + top movers + action items ngày mai |
| `portfolio-monitor` | Alert nếu có trigger; "Không có biến động" nếu yên tĩnh |
| `watchlist-check` | Alert các mã chạm điều kiện; "Watchlist bình thường" nếu không có |
| `technical-analysis` | Trend + signals + entry/stoploss/target cụ thể |
| `fundamental-analysis` | Valuation + khuyến nghị MUA/GIỮ/BÁN + target 12 tháng |
| `news-impact` | Sentiment score + tóm tắt tin + dự báo phản ứng giá |
| `portfolio-review` | P&L + concentration risk + action plan từng vị thế |
| `stock-screener` | Danh sách mã lọc được + lý do ngắn gọn từng mã |
| `sector-compare` | Ranking peer + sector outlook + mã tốt nhất trong ngành |
| `/analyze` | TA + FA + News tổng hợp + khuyến nghị cuối |
| `/report` | Tổng kết thị trường đầy đủ theo ngày/tuần |

## 10. CONVENTIONS

- **Language:** Python 3.12
- **Formatting:** `ruff` (line-length 100, double quotes)
- **Testing:** `pytest` with `pytest-asyncio`; all tests in `mcp-server/tests/`
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- **VN market specifics:** Prices in VNĐ, T+2 settlement, HOSE ±7% / HNX ±10% / UPCOM ±15% bands

## 11. AGENT CONTEXT

This project has a dedicated Bridge agent (`vn-stock-trader--vn-stock-trader`).

**Primary focus:** Build Claude plugins/skills for Vietnamese stock traders — market analysis, trading tools, broker integrations.

When working on tasks, prioritize:
- Vietnamese market specifics (VND currency, T+2 settlement, trading sessions, price bands)
- Integration with local broker APIs
- Data sources relevant to VN equities (SSI iBoard, VNDirect, CafeF, Vietstock)
- Regulatory context (State Securities Commission of Vietnam rules)

> **Automation note:** Automation (loop, schedule) được cài đặt bên Bridge Bot (có reply tool gửi Telegram). Agent này chỉ chạy tasks khi được dispatch — không tự quản lý scheduling hay loop.

## 12. HELP MENU

Khi user nói **"help"** hoặc **"trợ giúp"**, output menu sau:

---

📋 **VN STOCK TRADER — MENU LỆNH**

**📊 Phân tích cổ phiếu**
• `/analyze <MÃ>` — Phân tích toàn diện TA + FA + News (VD: `/analyze VNM`)
• `/technical <MÃ>` — Phân tích kỹ thuật: xu hướng, RSI, MACD, entry/stoploss/target
• `/fundamental <MÃ>` — Phân tích cơ bản: P/E, P/B, ROE, định giá, khuyến nghị
• `/news <MÃ>` — Tin tức và sentiment analysis
• `/compare <MÃ1> <MÃ2>` — So sánh 2 cổ phiếu nên chọn cái nào

**💼 Danh mục**
• `/portfolio` — Xem danh mục: P&L, phân bổ, khuyến nghị tái cơ cấu

**🔍 Tìm kiếm cơ hội**
• `/screen [strategy]` — Lọc cổ phiếu theo chiến lược
  - Strategies: `growth` | `value` | `momentum` | `dividend` | `recovery`

**🏭 Ngành**
• `/sector <MÃ>` — So sánh peer, ranking trong ngành, sector outlook

**📰 Thị trường**
• `/report [daily|weekly]` — Báo cáo thị trường tổng hợp
• `morning brief` — Tóm tắt trước phiên: thị trường + danh mục + tin tức
• `session summary` — Tổng kết cuối phiên: P&L ngày + action items

**🔔 Cảnh báo**
• `/alert <MÃ> <giá>` — Đặt cảnh báo giá (VD: `/alert VNM 65000`)

**❓ Trợ giúp**
• `help` / `trợ giúp` — Hiện menu này

---

💡 *Tip: Bạn có thể hỏi tự nhiên bằng tiếng Việt — VD: "phân tích VNM", "lọc cổ phiếu tăng trưởng", "danh mục của tôi hôm nay thế nào?"*

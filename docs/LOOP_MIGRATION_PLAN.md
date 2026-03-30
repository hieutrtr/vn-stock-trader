# Loop Migration Plan — Cron Scripts → Claude Code /loop + Skills

## Tổng quan

Chuyển đổi 4 automation scripts (Python cron) sang Claude Code skills + /loop.

### Tại sao chuyển?

| Cron Scripts | /loop + Skills |
|---|---|
| Chạy isolated, không context | Claude giữ full context giữa iterations |
| Output file markdown tĩnh | Phân tích context-aware, so sánh với lần trước |
| Cần setup crontab riêng | Chạy ngay trong Claude Code terminal |
| Không tương tác được | User hỏi follow-up ngay lập tức |
| Tốt cho Telegram notify (headless) | Tốt cho interactive trading session |

### Khi nào vẫn dùng scripts cũ?

- Khi cần gửi Telegram notification (bot chạy headless)
- Khi Claude Code không mở (overnight, weekend)
- Backup automation layer

---

## Migration Map

| Script | → Skill | → Command | /loop Usage |
|---|---|---|---|
| `morning_brief.py` | `/morning-brief` | — | Gọi manual mỗi sáng |
| `session_summary.py` | `/session-summary` | — | Gọi manual cuối phiên |
| `portfolio_monitor.py` | `/portfolio-monitor` | — | `/loop 5m /portfolio-monitor` |
| `watchlist_alert.py` | `/watchlist-check` | — | `/loop 5m /watchlist-check` |

**Orchestrator:** `/trading-session` command khởi động tất cả loops + morning brief.

---

## Implementation Steps

### Step 1: Tạo 4 Skills mới

Mỗi skill = `.claude/skills/<name>/SKILL.md` với:
- Frontmatter: name, description, allowed-tools
- Quy trình: gọi MCP tools → phân tích → format output
- Context-aware: so sánh với lần check trước (Claude nhớ)

#### 1.1 morning-brief
- Tools: `get_market_overview`, `get_portfolio`, `get_news`, `get_stock_price`
- Read `data/watchlist.json` cho symbols
- So sánh với phiên hôm qua (nếu có context)
- Output: markdown brief giống format scripts nhưng có AI commentary

#### 1.2 session-summary
- Tools: `get_market_overview`, `get_portfolio`, `get_top_movers`, `get_news`
- Tổng kết P&L, sector rotation, notable events
- Context: so sánh với morning brief đầu ngày

#### 1.3 portfolio-monitor
- Tools: `get_stock_price`, `get_portfolio`
- Check thresholds từ `data/automation_config.json`
- Alert: price >5%, volume spike 3x, near ceiling/floor
- Context-aware: so sánh giá với lần check 5 phút trước

#### 1.4 watchlist-check
- Tools: `get_stock_price`
- Read `data/watchlist.json` cho conditions
- Check từng alert condition
- Only report khi có trigger mới (tránh spam)

### Step 2: Tạo /trading-session Command

File: `.claude/commands/trading-session.md`

Workflow:
1. Chạy `/morning-brief` ngay
2. Start loops: `/loop 5m /portfolio-monitor`, `/loop 5m /watchlist-check`, `/loop 30m /news`
3. Monitor cho đến 14:45 hoặc user nói "kết thúc phiên"
4. Chạy `/session-summary` khi kết thúc

### Step 3: Mark Scripts Legacy

- Thêm docstring/comment ở đầu mỗi script
- Thêm `scripts/README.md` giải thích legacy status

### Step 4: Update Docs

- CLAUDE.md: thêm section Skills mới + /loop usage
- README.md: thêm /loop workflow
- SETUP_AND_INTEGRATION.md: thêm phần /loop automation

---

## File Changes Summary

### New Files
```
.claude/skills/morning-brief/SKILL.md
.claude/skills/session-summary/SKILL.md
.claude/skills/portfolio-monitor/SKILL.md
.claude/skills/watchlist-check/SKILL.md
.claude/commands/trading-session.md
```

### Modified Files
```
scripts/morning_brief.py          # Legacy header
scripts/session_summary.py        # Legacy header
scripts/portfolio_monitor.py      # Legacy header
scripts/watchlist_alert.py        # Legacy header
CLAUDE.md                         # New skills + commands
README.md                         # /loop usage section
docs/SETUP_AND_INTEGRATION.md     # Automation update
```

# Setup & Integration Guide — VN Stock Trader

_Cập nhật: 2026-03-30_

---

## Phần 1: Chi tiết `install.sh` — Từng bước cài đặt

### Tổng quan

`install.sh` là one-command setup script. User chỉ cần:

```bash
git clone <repo>
cd vn-stock-trader
./install.sh
```

### Chi tiết từng bước

#### Bước 1: Check & cài `uv` (Python package manager)

```bash
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
```

- **Cài gì:** `uv` — Rust-based Python package manager (thay thế pip/pipenv/poetry)
- **Tại sao:** Project dùng `uv sync` để quản lý dependencies, `uv run` để chạy scripts
- **Nếu đã có:** Skip, không cài lại
- **Output:** `"📦 Cài đặt uv..."` nếu cần cài

#### Bước 2: Cài Python dependencies

```bash
uv sync
```

- **Cài gì** (từ `pyproject.toml`):
  | Package | Version | Mục đích |
  |---------|---------|----------|
  | `vnstock` | >=3.4.0 | Nguồn dữ liệu chứng khoán VN (TCBS/VCI) |
  | `pandas` | >=2.0.0 | Xử lý dữ liệu tài chính |
  | `pandas-ta` | >=0.3.14b0 | Technical indicators (RSI, MACD, BB, ATR...) |
  | `httpx` | >=0.27.0 | HTTP client async |
  | `beautifulsoup4` | >=4.12.0 | Scraping tin tức |
  | `lxml` | >=5.0.0 | HTML/XML parser |
  | `python-dotenv` | >=1.0.0 | Load .env config |
  | `rich` | >=13.0.0 | Terminal UI (tables, progress) |
  | `mcp` | >=1.0.0 | FastMCP framework cho MCP server |

- **Tạo gì:** `.venv/` — virtual environment tại project root
- **Yêu cầu:** Python >= 3.12 (uv tự cài nếu chưa có)
- **Output:** Danh sách packages đã cài

#### Bước 3: Tạo thư mục data

```bash
mkdir -p data/briefs data/summaries
```

- **Tạo gì:**
  - `data/briefs/` — Lưu morning brief hàng ngày (YYYY-MM-DD.md)
  - `data/summaries/` — Lưu session summary hàng ngày
- **Nếu đã có:** `mkdir -p` tự skip

#### Bước 4: Copy `.env` config

```bash
if [ ! -f .env ]; then
    cp .env.example .env
fi
```

- **Config gì:**
  ```env
  # Broker API keys (tùy chọn, mặc định dùng TCBS public)
  SSI_USERNAME=
  SSI_PASSWORD=
  TCBS_TOKEN=
  VNDIRECT_USERNAME=
  VNDIRECT_PASSWORD=

  # Paths
  CACHE_DB_PATH=mcp-server/cache/vn_stock.db
  PORTFOLIO_PATH=data/portfolio.json
  WATCHLIST_PATH=data/watchlist.json

  # Tuning
  LOG_LEVEL=INFO
  REQUEST_DELAY_MIN=1.0
  REQUEST_DELAY_MAX=2.5
  ```
- **Lưu ý:** Hiện tại `.env` chưa được load bởi code (Phase E trong PACKAGING_PLAN). Cần thêm `load_dotenv()` vào `server.py` và scripts.
- **Output:** `"✅ Tạo .env từ .env.example — chỉnh sửa nếu cần"`

#### Bước 5: Tạo watchlist mẫu

```bash
if [ ! -f data/watchlist.json ]; then
    cat > data/watchlist.json <<'EOF'
    {
      "symbols": ["VCB", "HPG", "FPT", "MBB", "ACB"],
      "alerts": [],
      "updated_at": ""
    }
    EOF
fi
```

- **Tạo gì:** `data/watchlist.json` — Danh sách mã theo dõi
- **Mặc định:** 5 blue-chip (VCB, HPG, FPT, MBB, ACB)
- **Nếu đã có:** Skip, giữ nguyên data user
- **User cần làm:** Sửa danh sách symbols theo ý

#### Bước 6: Tạo portfolio trống

```bash
if [ ! -f data/portfolio.json ]; then
    cat > data/portfolio.json <<'EOF'
    {
      "positions": [],
      "cash": 0,
      "t1_receivable": 0,
      "t2_receivable": 0,
      "updated_at": ""
    }
    EOF
fi
```

- **Tạo gì:** `data/portfolio.json` — Danh mục đầu tư
- **Mặc định:** Trống (chưa có vị thế nào)
- **User cần làm:** Nhập positions qua `/portfolio` command hoặc sửa file trực tiếp
- **Lưu ý:** Cũng có thể dùng MCP tool `update_portfolio` để cập nhật

#### Bước 7: Verify — Test import dependencies

```bash
uv run python -c "
from mcp.server.fastmcp import FastMCP
import vnstock
import pandas_ta
import httpx
import bs4
print('✅ Tất cả dependencies OK')
"
```

- **Verify gì:**
  - `FastMCP` — MCP server framework
  - `vnstock` — Data source VN stock
  - `pandas_ta` — Technical analysis lib
  - `httpx` — HTTP client
  - `bs4` — HTML parser
- **Nếu fail:** In lỗi ImportError, user biết package nào thiếu

#### Bước 8: Verify — Test MCP tools syntax

```bash
uv run python -c "
import sys; sys.path.insert(0, 'mcp-server')
from tools.market import register
from tools.history import register
print('✅ MCP tools import OK')
"
```

- **Verify gì:** MCP tool modules import được, không có syntax error
- **Tại sao:** Đảm bảo server sẽ start thành công khi Claude Code load

#### Output cuối cùng

```
✅ Cài đặt hoàn tất!

📋 Bước tiếp theo:
  1. Mở Claude Code tại thư mục này: code .
  2. MCP server sẽ tự động khởi động
  3. Thêm cổ phiếu vào watchlist: data/watchlist.json
  4. Chạy morning brief: uv run python scripts/morning_brief.py --output stdout

⚙️  Cài đặt cron tự động: ./setup_cron.sh
```

### Tổng kết install.sh

| Bước | Hành động | Tạo/sửa gì | Điều kiện |
|------|-----------|-------------|-----------|
| 1 | Check/cài uv | `~/.cargo/bin/uv` | Chỉ nếu chưa có |
| 2 | `uv sync` | `.venv/`, 9 packages | Luôn chạy |
| 3 | Tạo dirs | `data/briefs/`, `data/summaries/` | `mkdir -p` |
| 4 | Copy .env | `.env` | Chỉ nếu chưa có |
| 5 | Tạo watchlist | `data/watchlist.json` | Chỉ nếu chưa có |
| 6 | Tạo portfolio | `data/portfolio.json` | Chỉ nếu chưa có |
| 7 | Test imports | — | Luôn chạy |
| 8 | Test MCP tools | — | Luôn chạy |

### Những gì install.sh KHÔNG làm (cần manual)

1. **Cài cron jobs** — Chạy riêng `./setup_cron.sh`
2. **Config Telegram** — Sửa `data/automation_config.json` (bot_token, chat_id)
3. **Nhập portfolio thực** — Sửa `data/portfolio.json` hoặc dùng `/portfolio`
4. **Config broker API keys** — Sửa `.env` (tùy chọn, mặc định dùng public API)

---

## Phần 2: Kết hợp VN Stock Trader với MCP Telegram Channel

### 2.1. MCP Channel là gì? Khác gì MCP Server?

#### MCP Server (cái ta đang có)

MCP Server là dạng **pull-based** — Claude Code chủ động gọi tool khi cần:

```
Claude Code → gọi get_stock_price("VNM") → MCP Server → trả kết quả
```

- Claude là bên khởi tạo request
- Server chỉ phản hồi khi được gọi
- Config trong `.mcp.json`, tự động available

#### MCP Channel (cái mới)

MCP Channel là dạng **push-based** — sự kiện bên ngoài được đẩy VÀO session Claude:

```
Telegram User gửi tin → Channel nhận → Push vào Claude Code → Claude xử lý → Reply
```

- Bên ngoài khởi tạo (user gửi tin, webhook, alert...)
- Claude nhận event và phản ứng
- Cần flag `--channels` khi khởi động Claude Code

#### So sánh chi tiết

| Khía cạnh | MCP Server | MCP Channel |
|-----------|------------|-------------|
| **Hướng** | Pull — Claude gọi tool | Push — Event đẩy vào Claude |
| **Ai khởi tạo** | Claude Code | Hệ thống bên ngoài |
| **Use case** | Truy vấn dữ liệu on-demand | Chat bridge, webhook, monitoring |
| **Khai báo** | Standard MCP capabilities | Thêm `claude/channel` capability |
| **Kích hoạt** | Tự động qua `.mcp.json` | Phải dùng `--channels` flag |
| **Giao tiếp** | Request → Response | Notification → (optional) Reply |

#### Quan trọng: Channel VẪN LÀ MCP Server

Channel dùng cùng MCP SDK, cùng stdio transport, cùng JSON-RPC protocol. Điểm khác duy nhất: nó khai báo thêm capability `claude/channel`, cho phép đẩy notification vào Claude session.

### 2.2. Claude Code `--channels` flag

#### Cú pháp

```bash
# Dùng plugin chính thức (Telegram)
claude --channels plugin:telegram@claude-plugins-official

# Nhiều channels cùng lúc
claude --channels plugin:telegram@claude-plugins-official plugin:discord@claude-plugins-official

# Channel tự phát triển (development)
claude --dangerously-load-development-channels server:my-webhook
```

#### Quy tắc quan trọng

1. Config trong `.mcp.json` là **KHÔNG ĐỦ** — phải thêm `--channels` flag
2. Giai đoạn research preview: plugin chính thức dùng `--channels`, custom channel cần `--dangerously-load-development-channels`
3. Yêu cầu đăng nhập claude.ai (không hỗ trợ API key auth)
4. Team/Enterprise phải bật `channelsEnabled` trong admin settings

### 2.3. Telegram MCP Channel — Setup cụ thể

#### Package chính thức

- **Tên:** `telegram@claude-plugins-official`
- **Source:** [github.com/anthropics/claude-plugins-official/tree/main/external_plugins/telegram](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/telegram)
- **Không có trên npm** — phân phối qua plugin marketplace của Claude Code

#### Bước setup

```bash
# 1. Tạo bot qua BotFather trên Telegram
#    → /newbot → đặt tên → nhận token

# 2. Cài plugin trong Claude Code
/plugin install telegram@claude-plugins-official

# 3. Config token
/telegram:configure <YOUR_BOT_TOKEN>
# Token lưu tại: ~/.claude/channels/telegram/.env

# 4. Khởi động Claude Code với channel
claude --channels plugin:telegram@claude-plugins-official

# 5. Pair tài khoản Telegram
#    → DM bot trên Telegram → nhận pairing code
/telegram:access pair <CODE>

# 6. Khóa access (chỉ cho phép user đã pair)
/telegram:access policy allowlist
```

#### Tools mà Telegram channel expose cho Claude

| Tool | Mô tả |
|------|--------|
| `reply` | Gửi tin nhắn (text + file đính kèm, max 50MB) |
| `react` | Thêm emoji reaction |
| `edit_message` | Sửa tin nhắn đã gửi |

#### Giới hạn

- Bot API **không có message history** — chỉ thấy tin khi nó đến
- Ảnh bị Telegram nén — user nên "Send as File" để giữ chất lượng
- Events chỉ đến khi session đang mở
- Telegram message limit: 4096 ký tự

### 2.4. Architecture — Luồng xử lý end-to-end

#### Use case mục tiêu

User trên Telegram gửi: **"phân tích VNM"** → nhận kết quả phân tích đầy đủ

#### Diagram

```
┌─────────────────┐
│  Telegram User   │
│  (phone/desktop) │
└────────┬────────┘
         │ DM: "phân tích VNM"
         ▼
┌─────────────────┐
│ Telegram Bot API │
│    (cloud)       │
└────────┬────────┘
         │ Long polling
         ▼
┌──────────────────────────────────────────────────┐
│  Telegram Channel Plugin                          │
│  (local subprocess của Claude Code)               │
│                                                    │
│  • Nhận message qua Bot API polling               │
│  • Check sender allowlist                         │
│  • Emit: notifications/claude/channel             │
└────────┬─────────────────────────────▲───────────┘
         │ stdio (JSON-RPC)            │ reply tool
         ▼                            │
┌──────────────────────────────────────┴───────────┐
│  Claude Code Session (local terminal)             │
│                                                    │
│  Nhận event dạng:                                 │
│  <channel source="telegram" sender="user123">     │
│    phân tích VNM                                  │
│  </channel>                                        │
│                                                    │
│  Claude quyết định:                               │
│  1. Gọi get_stock_price("VNM")     ──┐           │
│  2. Gọi get_stock_history("VNM")     │           │
│  3. Gọi get_financial_report("VNM")  │           │
│  4. Tổng hợp kết quả                 │           │
│  5. Gọi reply() trả về Telegram      │           │
└───────────────────────┬──────────────┘           │
                        │ stdio (JSON-RPC)          │
                        ▼                           │
┌──────────────────────────────────────────────────┐
│  VN Stock Trader MCP Server                       │
│  (local subprocess của Claude Code)               │
│                                                    │
│  • get_stock_price → vnstock3 API → TCBS         │
│  • get_stock_history → OHLCV + TA indicators     │
│  • get_financial_report → P/E, P/B, ROE, EPS     │
│  • Cached qua SQLite (TTL)                        │
└──────────────────────────────────────────────────┘
```

#### Chi tiết kỹ thuật

1. **Telegram Plugin** chạy **local** như subprocess của Claude Code
2. Plugin poll Telegram Bot API (không cần webhook URL, không cần public IP)
3. Giao tiếp Plugin ↔ Claude Code qua **stdio** (standard MCP transport)
4. Claude Code nhận message trong tag `<channel source="telegram" ...>`
5. Claude xử lý, gọi MCP tools (vn-stock-trader), rồi gọi `reply` tool
6. Typing indicator tự động hiện trên Telegram khi Claude đang xử lý
7. **Permission relay**: Claude có thể forward tool approval prompt qua Telegram — user approve/deny bằng `yes <id>` / `no <id>`

### 2.5. Config kết hợp cả hai

#### Bước 1: Cài VN Stock Trader (MCP Server)

```bash
cd vn-stock-trader
./install.sh
```

Đã có sẵn `.mcp.json`:

```json
{
  "mcpServers": {
    "vn-stock-trader": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "mcp-server/server.py"],
      "env": {}
    }
  }
}
```

#### Bước 2: Cài Telegram Channel Plugin

```bash
# Trong Claude Code session:
/plugin install telegram@claude-plugins-official
/telegram:configure <BOT_TOKEN>
```

#### Bước 3: Khởi động với cả hai

```bash
# Từ thư mục vn-stock-trader (có .mcp.json)
claude --channels plugin:telegram@claude-plugins-official
```

Khi khởi động:
- Claude Code đọc `.mcp.json` → start **vn-stock-trader MCP server**
- `--channels` flag → start **Telegram channel plugin**
- Cả hai chạy song song như subprocesses

#### Bước 4: Pair Telegram user

```bash
# Trong Claude Code:
/telegram:access pair <CODE_TỪ_TELEGRAM>
/telegram:access policy allowlist
```

#### Kết quả

Từ Telegram, user gửi:
- `"giá VNM"` → Claude gọi `get_stock_price("VNM")` → reply giá
- `"phân tích FPT"` → Claude gọi multiple tools → reply phân tích TA+FA+News
- `"/screen PE<15"` → Claude gọi `screen_stocks` → reply danh sách
- `"review danh mục"` → Claude gọi `get_portfolio` + prices → reply P&L

### 2.6. Automation Integration — Morning Brief & Alerts qua Telegram

#### Vấn đề: 2 con đường gửi Telegram

Có **2 cách** để gửi thông tin qua Telegram, phục vụ mục đích khác nhau:

| Cách | Khi nào dùng | Cần gì |
|------|-------------|--------|
| **A. Telegram Bot API trực tiếp** | Cron scripts tự động (morning_brief, alerts) | Bot token + chat_id |
| **B. Telegram MCP Channel** | Interactive chat (user hỏi, Claude trả lời) | Claude Code session đang chạy |

#### Cách A: Cron scripts → Telegram Bot API trực tiếp

Đây là cách **phù hợp cho automation** vì:
- Cron chạy **không cần Claude Code session**
- Script Python gọi Telegram Bot API trực tiếp qua `httpx`
- Đơn giản, đáng tin cậy, không phụ thuộc Claude

**Flow:**

```
Cron (8:30 sáng)
  → morning_brief.py
    → vnstock3 API (lấy data)
    → Tổng hợp brief
    → telegram_notify.send_brief()
      → httpx.post("https://api.telegram.org/bot{TOKEN}/sendMessage")
        → Telegram User nhận brief
```

**Config:** `data/automation_config.json`

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "123456:ABC-DEF...",
    "chat_id": "987654321"
  }
}
```

**Tích hợp vào scripts hiện có:**

```python
# morning_brief.py — thêm sau khi tạo brief:
from telegram_notify import send_brief
send_brief(f"Morning Brief {today}", brief)

# portfolio_monitor.py — thêm khi phát hiện alert:
from telegram_notify import send_alert
send_alert(symbol, f"Giá {price:,.0f} vượt ngưỡng {threshold:,.0f}")

# watchlist_alert.py — thêm khi trigger:
from telegram_notify import send_alert
send_alert(sym, alert_message)
```

#### Cách B: Telegram MCP Channel — Interactive Chat

Đây là cách **phù hợp cho interactive** vì:
- User hỏi → Claude phân tích → trả lời
- Claude có access đầy đủ MCP tools, skills, context
- Phân tích phức tạp (TA, FA, so sánh ngành...)

**Flow:**

```
Telegram User: "so sánh VNM và VCB"
  → Telegram Channel Plugin
    → Claude Code Session
      → Gọi get_stock_price("VNM"), get_stock_price("VCB")
      → Gọi get_financial_report("VNM"), get_financial_report("VCB")
      → Tổng hợp so sánh
      → reply() → Telegram User nhận kết quả
```

**Yêu cầu:** Claude Code session phải đang chạy.

#### Recommendation: Dùng CẢ HAI

```
┌─────────────────────────────────────────────────────┐
│                    TELEGRAM BOT                      │
│                  (cùng bot token)                     │
├─────────────────────┬───────────────────────────────┤
│   Automation Path   │      Interactive Path          │
│   (Cách A)          │      (Cách B)                  │
├─────────────────────┼───────────────────────────────┤
│ Cron scripts        │ Claude Code + Channel          │
│ → Bot API trực tiếp │ → MCP tools + AI reasoning    │
│                     │                                │
│ • Morning brief     │ • "phân tích VNM"             │
│ • Portfolio alerts  │ • "so sánh HPG vs HSG"        │
│ • Price alerts      │ • "lọc PE < 10, ROE > 15"    │
│ • Session summary   │ • "review danh mục"           │
│                     │                                │
│ Chạy: 24/7 via cron │ Chạy: khi Claude Code mở     │
│ Không cần Claude    │ Cần Claude Code session       │
└─────────────────────┴───────────────────────────────┘
```

**Cùng bot, cùng chat_id** — user nhận cả automated alerts và interactive responses trong cùng 1 conversation Telegram.

### 2.7. Setup flow tổng hợp — Từ zero đến hoàn chỉnh

```bash
# ── Bước 1: Cài VN Stock Trader ──
git clone <repo>
cd vn-stock-trader
./install.sh

# ── Bước 2: Tạo Telegram Bot ──
# Trên Telegram: @BotFather → /newbot → lấy token
# DM bot 1 tin → lấy chat_id từ:
# https://api.telegram.org/bot<TOKEN>/getUpdates

# ── Bước 3: Config automation (cho cron scripts) ──
# Sửa data/automation_config.json:
#   "telegram": { "enabled": true, "bot_token": "...", "chat_id": "..." }

# ── Bước 4: Cài cron jobs ──
./setup_cron.sh

# ── Bước 5: Cài Telegram Channel (cho interactive chat) ──
# Mở Claude Code tại thư mục này:
claude
/plugin install telegram@claude-plugins-official
/telegram:configure <BOT_TOKEN>
# Thoát Claude Code

# ── Bước 6: Chạy với channel ──
claude --channels plugin:telegram@claude-plugins-official
/telegram:access pair <CODE>
/telegram:access policy allowlist

# ── Done! ──
# Automation: cron gửi brief/alerts qua Bot API
# Interactive: Telegram user hỏi → Claude trả lời qua Channel
```

### 2.8. Các plugin MCP Channel chính thức khác

Repo `claude-plugins-official` có các channel plugins:

| Plugin | Loại | Mô tả |
|--------|------|--------|
| `telegram` | Channel | Telegram bot bridge |
| `discord` | Channel | Discord bot bridge |
| `imessage` | Channel | macOS iMessage bridge (đọc chat.db) |
| `fakechat` | Channel | Demo localhost với web UI port 8787 |

Non-channel plugins: asana, github, gitlab, linear, playwright, slack, supabase, terraform...

### 2.9. Lưu ý quan trọng

1. **Telegram Channel ở giai đoạn research preview** — API có thể thay đổi
2. **Claude Code session phải đang chạy** để interactive chat hoạt động
3. **Automation nên dùng Bot API trực tiếp** — không phụ thuộc Claude session
4. **Cùng bot token** có thể dùng cho cả automation (scripts) và interactive (channel)
5. **Message limit 4096 ký tự** — brief/phân tích dài cần truncate
6. **Không có message history** — bot chỉ thấy tin khi nó đến (không search lại được)
7. **Permission relay** — Claude có thể hỏi approve/deny tool qua Telegram, rất hữu ích cho trading actions

---

## Tham khảo

- [Claude Code Channels Documentation](https://code.claude.com/docs/en/channels)
- [Channels Reference](https://code.claude.com/docs/en/channels-reference)
- [Telegram Plugin — GitHub](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/telegram)
- [claude-plugins-official Repository](https://github.com/anthropics/claude-plugins-official)

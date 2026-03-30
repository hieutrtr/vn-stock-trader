# Packaging Plan — VN Stock Trader
_Dựa trên Deep Review 2026-03-30_

---

## Phần 1: Vấn đề hiện tại

### User phải làm gì để cài đặt? (hiện tại)

```
1. git clone hoặc copy thư mục
2. cd vn-stock-trader
3. uv sync                          ← cài Python deps
4. Mở Claude Code tại thư mục này  ← MCP server tự load
5. cp .env.example .env             ← copy config (nhưng không có effect)
6. nano data/watchlist.json         ← tự sửa watchlist bằng tay
7. nano data/portfolio.json         ← tự nhập portfolio bằng tay
8. crontab -e → thêm 2 jobs bằng tay ← setup automation bằng tay
9. Viết Telegram bot code nếu muốn  ← không có hướng dẫn
```

**Tổng: 9 bước, 3 bước manual JSON editing, 1 bước thiếu hẳn code (Telegram).**

### Hardcoded gì?

| Chỗ | Hardcode | Vấn đề |
|-----|---------|--------|
| `data_sources/vnstock_client.py` | `source="TCBS"` | Không cấu hình được qua env |
| `data_sources/vnstock_client.py` | ceiling/floor ±7% | HNX/UPCOM tính sai |
| `cache/cache.py` | `_DEFAULT_DB = Path(__file__).parent / "vn_stock.db"` | Không đọc env var |
| `scripts/*.py` | `PROJECT_ROOT / "data" / ...` | Cố định relative path — OK nếu chạy từ project root |
| `.mcp.json` | `"command": "uv"` | Cần uv có trong PATH |

### Thiếu gì để chạy end-to-end?

1. **Bug fixes** (xem DEEP_REVIEW.md) — 2 critical bugs ảnh hưởng output
2. **Telegram send code** — config có nhưng không có code gửi
3. **Cron setup script** — user phải tự làm
4. **`.env` loading** — `python-dotenv` khai báo nhưng chưa dùng
5. **`watchlist.json` sample data** — có rồi ✅
6. **`portfolio.json` sample data** — có rồi (VNM demo) ✅

---

## Phần 2: Kế hoạch đóng gói

### Mục tiêu install flow lý tưởng

```bash
git clone <repo>
cd vn-stock-trader
./install.sh          ← one-command setup

# Sau đó mở Claude Code tại thư mục này
# Hoặc chạy scripts ngay:
uv run python scripts/morning_brief.py --output stdout
```

---

## Phần 3: Checklist thực hiện

### Phase A: Fix Critical Bugs (làm ngay, < 1h)

**A1. Fix S/R key mismatch trong `tools/history.py`**
```python
# Line 219-220, đổi từ:
supports = sr.get("supports", [])
resistances = sr.get("resistances", [])
# Thành:
supports = sr.get("support", [])
resistances = sr.get("resistance", [])
```

**A2. Fix `get_stock_price()` trả về change = 0**
```python
# Trong vnstock_client.py, lấy 2 ngày để tính change:
start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")  # 5 ngày để cover weekend
# Sau đó:
if len(quote) >= 2:
    prev_close = float(quote.iloc[-2]["close"])
    curr_close = float(quote.iloc[-1]["close"])
    result["change"] = curr_close - prev_close
    result["pct_change"] = (result["change"] / prev_close * 100) if prev_close > 0 else 0.0
```

---

### Phase B: `install.sh` — One-command setup

**Tạo file `install.sh` tại project root:**

```bash
#!/usr/bin/env bash
# install.sh — VN Stock Trader setup

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 VN Stock Trader — Cài đặt..."
echo ""

# 1. Check uv
if ! command -v uv &>/dev/null; then
    echo "📦 Cài đặt uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 2. Cài Python deps
echo "📦 Cài Python dependencies..."
uv sync

# 3. Tạo thư mục data nếu chưa có
mkdir -p data/briefs data/summaries

# 4. Copy .env nếu chưa có
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Tạo .env từ .env.example — chỉnh sửa nếu cần"
fi

# 5. Tạo watchlist mẫu nếu chưa có
if [ ! -f data/watchlist.json ]; then
    cat > data/watchlist.json <<'EOF'
{
  "_schema": "vn-stock-trader watchlist v1",
  "symbols": ["VCB", "HPG", "FPT", "MBB", "ACB"],
  "alerts": [],
  "updated_at": ""
}
EOF
    echo "✅ Tạo data/watchlist.json mẫu"
fi

# 6. Tạo portfolio trống nếu chưa có
if [ ! -f data/portfolio.json ]; then
    cat > data/portfolio.json <<'EOF'
{
  "_schema": "vn-stock-trader portfolio v1",
  "positions": [],
  "cash": 0,
  "t1_receivable": 0,
  "t2_receivable": 0,
  "updated_at": ""
}
EOF
    echo "✅ Tạo data/portfolio.json trống"
fi

# 7. Test import
echo ""
echo "🧪 Kiểm tra cài đặt..."
uv run python -c "
from mcp.server.fastmcp import FastMCP
import vnstock
import pandas_ta
import httpx
import bs4
print('✅ Tất cả dependencies OK')
"

# 8. Test MCP server syntax
uv run python -c "
import sys; sys.path.insert(0,'mcp-server')
from tools.market import register
from tools.history import register
print('✅ MCP tools import OK')
"

echo ""
echo "✅ Cài đặt hoàn tất!"
echo ""
echo "📋 Bước tiếp theo:"
echo "  1. Mở Claude Code tại thư mục này: code ."
echo "  2. MCP server sẽ tự động khởi động"
echo "  3. Thêm cổ phiếu vào watchlist: data/watchlist.json"
echo "  4. Chạy morning brief: uv run python scripts/morning_brief.py --output stdout"
echo ""
echo "⚙️  Cài đặt cron tự động: ./setup_cron.sh"
```

---

### Phase C: `setup_cron.sh` — Cron automation

**Tạo file `setup_cron.sh`:**

```bash
#!/usr/bin/env bash
# setup_cron.sh — Thiết lập cron jobs tự động

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UV_BIN="$(which uv)"

if [ -z "$UV_BIN" ]; then
    echo "❌ uv không tìm thấy. Chạy install.sh trước."
    exit 1
fi

# Cron jobs cần thêm
MORNING_JOB="30 8 * * 1-5 cd $SCRIPT_DIR && $UV_BIN run python scripts/morning_brief.py --output file >> data/automation.log 2>&1"
SUMMARY_JOB="50 14 * * 1-5 cd $SCRIPT_DIR && $UV_BIN run python scripts/session_summary.py --output file >> data/automation.log 2>&1"

echo "📅 Thêm cron jobs:"
echo "  Morning Brief: 8:30 T2-T6"
echo "  Session Summary: 14:50 T2-T6"
echo ""

# Backup crontab hiện tại
crontab -l > /tmp/crontab_backup.txt 2>/dev/null || true

# Thêm jobs nếu chưa có
{
    crontab -l 2>/dev/null | grep -v "vn-stock-trader" || true
    echo "# VN Stock Trader"
    echo "$MORNING_JOB"
    echo "$SUMMARY_JOB"
} | crontab -

echo "✅ Cron jobs đã được thêm!"
echo ""
echo "Kiểm tra: crontab -l | grep vn-stock"
echo "Xóa: crontab -l | grep -v 'vn-stock-trader' | crontab -"
```

---

### Phase D: Telegram Integration

**Thêm module `scripts/telegram_notify.py`:**

```python
"""
telegram_notify.py — Gửi thông báo qua Telegram Bot API.

Setup:
    1. Tạo bot: @BotFather → /newbot → lấy token
    2. Lấy chat_id: nhắn bot 1 tin → https://api.telegram.org/bot{TOKEN}/getUpdates
    3. Điền vào data/automation_config.json:
       "telegram": {"enabled": true, "bot_token": "xxx", "chat_id": "yyy"}
"""
import json
import logging
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)
CONFIG_PATH = Path(__file__).parent.parent / "data" / "automation_config.json"


def load_telegram_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f).get("telegram", {})
    return {}


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """
    Gửi tin nhắn Telegram. Returns True nếu thành công.
    Tự động skip nếu enabled=false.
    """
    config = load_telegram_config()
    if not config.get("enabled", False):
        return False

    token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    if not token or not chat_id:
        logger.warning("Telegram config thiếu bot_token hoặc chat_id")
        return False

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = httpx.post(url, json={
            "chat_id": chat_id,
            "text": text[:4096],  # Telegram max 4096 chars
            "parse_mode": parse_mode,
        }, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
        return False


def send_alert(symbol: str, message: str) -> bool:
    """Gửi alert cho một mã cổ phiếu."""
    return send_message(f"🔔 *ALERT — {symbol}*\n{message}")


def send_brief(title: str, content: str) -> bool:
    """Gửi brief/summary (tóm tắt, có thể bị truncate)."""
    # Telegram limit: 4096 chars
    truncated = content[:3900] + "\n\n_[truncated]_" if len(content) > 3900 else content
    return send_message(f"*{title}*\n\n{truncated}")
```

**Tích hợp vào `scripts/morning_brief.py`:**
```python
# Sau khi tạo xong brief:
from telegram_notify import send_brief
send_brief(f"Morning Brief {today}", brief)
```

**Tích hợp vào `scripts/watchlist_alert.py`:**
```python
# Trong check_watchlist(), sau khi trigger:
from telegram_notify import send_alert
send_alert(sym, msg)
```

---

### Phase E: `.env` Loading

**Thêm vào `mcp-server/server.py` đầu file:**
```python
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
```

**Thêm vào mỗi script trong `scripts/`:**
```python
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")
```

---

### Phase F: Claude Plugin Manifest

**Tạo `.claude-plugin/manifest.json` cho marketplace:**
```json
{
  "name": "vn-stock-trader",
  "version": "1.0.0",
  "description": "Vietnamese stock market analysis tools for Claude — TA, FA, Portfolio, News",
  "author": "VN Stock Trader Team",
  "homepage": "https://github.com/yourusername/vn-stock-trader",
  "mcp_server": {
    "command": "uv",
    "args": ["run", "python", "mcp-server/server.py"],
    "env": {}
  },
  "skills": [
    "technical-analysis",
    "fundamental-analysis",
    "news-impact",
    "portfolio-review",
    "stock-screener",
    "sector-compare"
  ],
  "commands": ["/analyze", "/screen", "/portfolio", "/news", "/compare", "/report", "/alert"],
  "agents": ["market-watcher", "news-analyst", "portfolio-manager", "research-agent"],
  "requirements": {
    "python": ">=3.12",
    "tools": ["uv"]
  },
  "tags": ["vietnam", "stock", "trading", "finance", "market-data"]
}
```

---

### Phase G: README Update

**README.md nên có:**

```markdown
# VN Stock Trader

Claude plugins/skills cho nhà đầu tư chứng khoán Việt Nam.

## Cài đặt

```bash
git clone https://github.com/yourusername/vn-stock-trader
cd vn-stock-trader
./install.sh
```

Mở Claude Code tại thư mục này — MCP server tự khởi động.

## Sử dụng ngay

| Lệnh | Mô tả |
|------|-------|
| `/analyze VNM` | Phân tích TA + FA + News |
| `/portfolio` | Xem danh mục + P&L |
| `/screen PE<15, ROE>15` | Lọc cổ phiếu |
| `/news HPG` | Tin tức HPG |

## Automation (tùy chọn)

```bash
./setup_cron.sh    # Cài morning brief 8:30 + session summary 14:50
```

## Telegram Alerts (tùy chọn)

```json
// data/automation_config.json
"telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
}
```
```

---

## Phần 4: Thứ tự ưu tiên thực hiện

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| 🔴 P0 | Fix S/R key bug (`tools/history.py`) | 5 min | Critical — S/R luôn trống |
| 🔴 P0 | Fix `change=0` bug (`vnstock_client.py`) | 30 min | Critical — % thay đổi sai |
| 🟠 P1 | Tạo `install.sh` | 1h | User experience |
| 🟠 P1 | Tạo `setup_cron.sh` | 30 min | Automation |
| 🟡 P2 | Thêm `telegram_notify.py` | 1h | Alert delivery |
| 🟡 P2 | Tích hợp Telegram vào scripts | 30 min | Alert delivery |
| 🟡 P2 | Load `.env` trong server + scripts | 30 min | Configuration |
| 🟢 P3 | Tạo `manifest.json` | 30 min | Marketplace ready |
| 🟢 P3 | Update README | 1h | Documentation |
| 🟢 P3 | Fix ceiling/floor HNX/UPCOM | 1h | Correctness |
| 🟢 P3 | Auto cache cleanup | 30 min | DB hygiene |

---

## Phần 5: File structure sau khi đóng gói

```
vn-stock-trader/
├── install.sh                    ← NEW: one-command setup
├── setup_cron.sh                 ← NEW: cron automation
├── .claude-plugin/
│   └── manifest.json             ← NEW: plugin manifest
├── mcp-server/
│   ├── server.py                 ← FIX: load .env
│   ├── data_sources/
│   │   └── vnstock_client.py     ← FIX: change/pct_change bug
│   └── tools/
│       └── history.py            ← FIX: S/R key names
├── scripts/
│   ├── telegram_notify.py        ← NEW: Telegram module
│   ├── morning_brief.py          ← UPDATE: add Telegram
│   ├── session_summary.py        ← UPDATE: add Telegram
│   ├── portfolio_monitor.py      ← UPDATE: add Telegram
│   └── watchlist_alert.py        ← UPDATE: add Telegram
├── data/
│   ├── automation_config.json
│   ├── portfolio.json
│   └── watchlist.json
├── .env.example
├── README.md                     ← UPDATE: install guide
└── PACKAGING_PLAN.md             ← This file
```

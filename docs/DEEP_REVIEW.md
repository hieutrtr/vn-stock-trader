# Deep Review — VN Stock Trader
_Reviewed: 2026-03-30 | Tests: 159 passed ✅_

---

## Tổng quan nhanh

| Layer | Status | Vấn đề |
|-------|--------|--------|
| Data Layer | ⚠️ mostly OK | 2 bugs logic, 1 env var bị bỏ qua |
| MCP Server | ✅ OK | Startup clean |
| Tools (11) | ⚠️ 2 bugs | S/R key mismatch, price change = 0 |
| Skills (6) | ✅ OK | Format đúng, tools đúng |
| Commands (7) | ✅ OK | Format đúng |
| Agents (4) | ✅ OK | Tools field đúng |
| Automation Scripts | ⚠️ Telegram thiếu | Config có nhưng code gửi chưa có |
| Tests | ✅ 159 passed | 1 warning nhỏ |

---

## 1. Data Layer

### `mcp-server/data_sources/vnstock_client.py`

**Có chạy thật được không?**
Được — lazy import `_import_vnstock()` tránh crash khi chưa cài. Rate limiting với `threading.Semaphore(3)` và min delay 0.5s. vnstock3 đã cài trong `.venv`.

**Vấn đề tìm thấy:**

❌ **BUG MEDIUM — `get_stock_price()` trả về change = 0 luôn**
```python
# Line 117: Dùng history 1 ngày thay vì quote realtime
quote = _rate_limited_call(stock.quote.history, start=yesterday, end=today)
row = quote.iloc[-1]  # Chỉ có 1 dòng → không có ngày hôm trước để so sánh

result["change"] = 0.0      # Hardcoded 0!
result["pct_change"] = 0.0  # Hardcoded 0!
```
_Hậu quả_: Tools/scripts hiển thị "0.00%" cho tất cả cổ phiếu. Portfolio icons luôn `🟡`. Morning brief không có % thay đổi.

_Fix nên làm_: Lấy 2 ngày history để tính `change = close_today - close_yesterday`.

**Hàm `get_market_overview()`:**
Gọi `vs.stock_screening.market_overview` — đây là API method của vnstock3, cần verify xem có hoạt động với TCBS source không. Best-effort, có fallback trả `{"error": ...}`.

**Hàm `get_top_movers()`:**
Gọi `vs.stock_screening.top_movers` — tương tự, phụ thuộc API vnstock3. Có fallback.

**Hàm `get_sector_peers()`:**
Gọi `vs.stock_screening.stock_screening` để lấy toàn bộ rồi filter — khá nặng. Cache 24h nên OK.

**`ceiling/floor` calculation:**
```python
result["ceiling"] = round(ref * 1.07)   # HOSE +7% ✅
result["floor"] = round(ref * 0.93)     # HOSE -7% ✅
```
_Vấn đề_: HNX ±10%, UPCOM ±15% chưa được phân biệt — tất cả dùng ±7% rule.

---

### `mcp-server/data_sources/vietstock_client.py`

**Crawl thật được không?**
Có khả năng — async httpx, BeautifulSoup lxml, random delay 1-2.5s, set User-Agent + Referer đúng format.

**Anti-bot headers:**
```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Referer": "https://vietstock.vn/",
}
```
Đủ cơ bản. Không có cookie/session management → có thể bị block nếu site dùng Cloudflare.

**URL patterns:**
```
https://finance.vietstock.vn/{SYMBOL}/tai-chinh.htm     # Financial ratios
https://finance.vietstock.vn/{SYMBOL}/bao-cao-tai-chinh.htm  # Income/Balance
https://vietstock.vn/{symbol}/tin-tuc.htm               # News
https://finance.vietstock.vn/data/getinsidertransaction?...  # API JSON insider
```
_Rủi ro_: Vietstock thay đổi DOM structure thường xuyên → HTML scraping fragile.

**`get_insider_trades()`:**
Thử JSON API trước (`/data/getinsidertransaction`), nếu fail → scrape HTML. Good fallback strategy.

---

### `mcp-server/cache/cache.py`

**SQLite path đúng không?**
```python
_DEFAULT_DB = Path(__file__).parent / "vn_stock.db"
# → mcp-server/cache/vn_stock.db ✅
```

⚠️ **Singleton không đọc `CACHE_DB_PATH` env var:**
```python
def get_cache(db_path: str | Path | None = None) -> SQLiteCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SQLiteCache(db_path)  # db_path luôn None khi gọi không arg
    return _cache_instance
```
`.env.example` có `CACHE_DB_PATH=mcp-server/cache/vn_stock.db` nhưng server/scripts không load `.env` file. `python-dotenv` được liệt kê trong dependencies nhưng không được gọi ở bất kỳ đâu.

⚠️ **Cleanup không tự động:** `cleanup()` xóa expired entries nhưng không được gọi theo timer. Database sẽ tích lũy expired rows mãi mãi.

---

### `mcp-server/data_sources/ta_calculator.py`

**Dependencies đúng không?**
`pandas`, `numpy`, `pandas-ta` — tất cả có trong `pyproject.toml`, đã cài trong `.venv`. Có fallback khi `pandas-ta` không có.

**Logic đúng không?**
MACD column order: pandas-ta trả về `[MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9]` tức `[macd, hist, signal]`. Code assign: `macd_val=cols[0]`, `hist_val=cols[1]`, `sig_val=cols[2]` → `{"macd": macd_val, "signal": sig_val, "histogram": hist_val}` ✅ đúng.

---

### `mcp-server/data_sources/portfolio.py`

**Load/save path đúng không?**
```python
DEFAULT_PORTFOLIO_PATH = Path(__file__).parent.parent.parent / "data" / "portfolio.json"
# __file__ = mcp-server/data_sources/portfolio.py
# parent = data_sources/
# parent.parent = mcp-server/
# parent.parent.parent = vn-stock-trader/   → "data/portfolio.json" ✅
```
File `data/portfolio.json` đã tồn tại và có dữ liệu mẫu.

---

### `mcp-server/data_sources/news_scraper.py`

**Các URL nguồn còn valid?**
```
cafef.vn/thi-truong-chung-khoan.chn       # CafeF chứng khoán ✅ likely valid
cafef.vn/doanh-nghiep.chn                  # CafeF doanh nghiệp ✅ likely valid
vietstock.vn/thi-truong/tin-thi-truong.htm # Vietstock ⚠️ URL có thể thay đổi
vnexpress.net/kinh-doanh/chung-khoan       # VNExpress ✅ valid
```

**Multiple sources song song:** `asyncio.gather(*tasks)` ✅

**Fallback:** Nếu 1 nguồn fail, vẫn dùng các nguồn còn lại. Deduplication by URL ✅.

---

## 2. MCP Server

### `mcp-server/server.py`

**Startup OK?**
```python
sys.path.insert(0, str(Path(__file__).parent))  # thêm mcp-server/ vào path ✅
mcp = FastMCP("vn-stock-mcp", instructions="...")
register_market(mcp); register_history(mcp); ...  # 7 modules ✅
mcp.run(transport="stdio")
```
Import đúng, 11 tools đăng ký thành công, logging ra stderr (không can thiệp stdio protocol) ✅.

### 11 tools — edge case handling

| Tool | Empty data | Network error |
|------|-----------|---------------|
| `get_stock_price` | `{"error": ...}` ✅ | `{"error": ...}` ✅ |
| `get_market_overview` | default None fields ✅ | `{"error": ...}` ✅ |
| `get_top_movers` | empty lists ✅ | `{"error": ...}` ✅ |
| `get_stock_history` | empty DataFrame ✅ | empty DataFrame ✅ |
| `get_financial_report` | per-section try/except ✅ | `{"error": ...}` ✅ |
| `get_sector_peers` | `[]` ✅ | `[]` ✅ |
| `get_news` | "không có tin" message ✅ | "không lấy được" ✅ |
| `screen_stocks` | "không mã nào" ✅ | per-symbol errors ✅ |
| `get_portfolio` | "danh mục trống" ✅ | price fallback to cost ✅ |
| `update_portfolio` | input validation ✅ | N/A |
| `get_insider_trades` | "không tìm thấy" ✅ | empty list ✅ |

❌ **BUG CRITICAL — `tools/history.py` line 219-220: S/R key mismatch**
```python
# tools/history.py sử dụng:
supports = sr.get("supports", [])      # key "supports" (có 's')
resistances = sr.get("resistances", [])  # key "resistances" (có 's')

# Nhưng ta_calculator.find_support_resistance() trả về:
return {
    "support": [...],    # key "support" (không có 's')
    "resistance": [...], # key "resistance" (không có 's')
    "current_price": ...,
}
```
_Hậu quả_: Section "🏗️ Vùng Hỗ trợ / Kháng cự" trong `get_stock_history` tool luôn không hiển thị dữ liệu (vì `supports` và `resistances` đều `[]`). Tất cả history calls bị affected.

### `.mcp.json`

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
✅ Không hardcode absolute path. `cwd` không được set → dùng project dir khi Claude Code mở project này.

⚠️ **Không có `cwd` explicit** → nếu user chạy Claude Code từ thư mục khác, MCP server sẽ không tìm thấy `mcp-server/server.py`.

---

## 3. Skills & Commands

### 6 Skills

| Skill | `allowed-tools` prefix | Format |
|-------|----------------------|--------|
| `technical-analysis` | `mcp__vn-stock-trader__` ✅ | Đúng |
| `fundamental-analysis` | `mcp__vn-stock-trader__` ✅ | Đúng |
| `news-impact` | `mcp__vn-stock-trader__` + WebSearch/WebFetch ✅ | Đúng |
| `portfolio-review` | `mcp__vn-stock-trader__` ✅ | Đúng |
| `stock-screener` | `mcp__vn-stock-trader__` ✅ | Đúng |
| `sector-compare` | `mcp__vn-stock-trader__` ✅ | Đúng |

MCP server name trong `.mcp.json` là `vn-stock-trader` → prefix `mcp__vn-stock-trader__` ✅ đúng.

### 7 Commands

Tất cả `.claude/commands/*.md` có frontmatter `description:` đúng format. `/analyze`, `/screen`, `/portfolio`, `/news`, `/compare`, `/report`, `/alert` ✅.

---

## 4. Agents

| Agent | `tools` field | Vấn đề |
|-------|-------------|--------|
| `market-watcher` | Đúng 4 tools ✅ | Output format section trống (line 36: chỉ có placeholder) ⚠️ |
| `news-analyst` | Đúng 5 tools ✅ | OK |
| `portfolio-manager` | Đúng 5 tools ✅ | OK |
| `research-agent` | Đúng 7 tools ✅ | OK |

⚠️ `market-watcher.md` dòng 36-37 có section "## Output Format" nhưng nội dung bị trống (chỉ có blank lines). Agent vẫn hoạt động nhưng output không nhất quán.

---

## 5. Automation Scripts

### Import paths
Tất cả 4 scripts đều có:
```python
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"
sys.path.insert(0, str(MCP_SERVER_DIR))
```
→ Import `data_sources.*` hoạt động khi chạy từ bất kỳ thư mục nào ✅

### Standalone chạy được không?

| Script | Chạy standalone | Vấn đề |
|--------|----------------|--------|
| `morning_brief.py` | ✅ có `if __name__ == "__main__"` | Telegram chưa implement |
| `session_summary.py` | ✅ | Telegram chưa implement |
| `portfolio_monitor.py` | ✅ signal handler SIGINT ✅ | Telegram chưa implement |
| `watchlist_alert.py` | ✅ | Telegram chưa implement |

### ❌ Telegram integration: CHƯA CÓ CODE

`automation_config.json` có:
```json
"telegram": {
    "enabled": false,
    "bot_token": "",
    "chat_id": ""
}
```
Nhưng **không có dòng code nào** trong 4 scripts đọc config `telegram` và gửi message. Các scripts chỉ in ra stdout/stderr. Nếu user bật `enabled: true` thì cũng không có gì xảy ra.

---

## 6. Config & Setup

### `.mcp.json` — hardcoded paths?
Không hardcode. Dùng relative path `mcp-server/server.py` và `uv run`. ✅

### `automation_config.json`
Đã có sẵn trong `data/`. Không cần setup script để tạo. ✅

### `.env.example`
Đủ vars cho: SSI, TCBS, VNDirect (tùy chọn), cache path, portfolio path, logging level. ✅

**Vấn đề:** Không có code nào trong project load `.env` file. `python-dotenv` có trong dependencies nhưng `dotenv.load_dotenv()` không được gọi ở đâu.

### Cron setup
❌ **Không có script tự động setup cron.** User phải tự chạy `crontab -e` và thêm:
```
30 8 * * 1-5  cd /path && uv run python scripts/morning_brief.py
50 14 * * 1-5 cd /path && uv run python scripts/session_summary.py
```

---

## 7. Tests

```
======================= 159 passed, 1 warning in 10.08s =======================
```

**159 tests pass** ✅

**1 warning**: `pandas_ta` `Pandas4Warning` — pandas-ta dùng deprecated `mode.copy_on_write` option. Không phải lỗi.

**Ruff**: 3 issues nhỏ trong `test_mcp_tools.py` (unused import, unsorted imports). Không ảnh hưởng chạy.

---

## 8. Tóm tắt Bugs

### 🔴 Critical — Ảnh hưởng trực tiếp đến output

| # | File | Vấn đề | Impact |
|---|------|--------|--------|
| 1 | `tools/history.py:219-220` | `sr.get("supports")` / `sr.get("resistances")` nhưng keys thực tế là `"support"` / `"resistance"` | S/R section trong `get_stock_history` luôn trống |
| 2 | `data_sources/vnstock_client.py:126-130` | `change=0.0`, `pct_change=0.0` hardcoded | Giá thay đổi luôn hiển thị 0.00% |

### 🟡 Medium — Ảnh hưởng tính năng phụ

| # | File | Vấn đề | Impact |
|---|------|--------|--------|
| 3 | `scripts/*.py` | Telegram code chưa implement | Alert không gửi được dù config có |
| 4 | `data_sources/vnstock_client.py:137-138` | ceiling/floor luôn tính theo HOSE ±7% | HNX/UPCOM sai biên độ |

### 🟢 Minor — Cần cải thiện

| # | File | Vấn đề | Impact |
|---|------|--------|--------|
| 5 | `cache/cache.py` | `get_cache()` không đọc env var | Phải code để override path |
| 6 | Project-wide | `.env` file không được load | Cấu hình qua env bị bỏ qua |
| 7 | `.mcp.json` | Thiếu `cwd` field | Có thể fail nếu chạy từ thư mục khác |
| 8 | `cache/cache.py` | Cleanup không auto | DB tích lũy expired rows |
| 9 | `.claude/agents/market-watcher.md:36` | Output Format section trống | Agent output không nhất quán |

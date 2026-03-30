# Kế hoạch Triển khai — VN Stock Trader Plugin

**Ngày lập:** 2026-03-30
**Căn cứ:** MARKET_ANALYSIS.md + PLUGIN_DESIGN.md
**Mục tiêu:** Triển khai bộ Claude plugin hoàn chỉnh cho trader chứng khoán Việt Nam theo từng phase có thể demo và test được.

---

## Tổng quan các Phase

| Phase | Tên | Thời gian | Deliverable |
|-------|-----|-----------|-------------|
| **Phase 0** | Project Bootstrap | 1 ngày | Cấu trúc project, pyproject.toml, môi trường dev |
| **Phase 1** | Data Layer | 3-4 ngày | vnstock wrapper + Vietstock crawler + SQLite cache |
| **Phase 2** | MCP Server Core | 3-4 ngày | 6 MCP tools hoạt động, trader truy vấn được dữ liệu |
| **Phase 3** | Skills TA & FA | 2-3 ngày | 2 skills đầu tiên: technical + fundamental analysis |
| **Phase 4** | Commands | 2-3 ngày | 4 slash commands: /analyze, /screen, /portfolio, /news |
| **Phase 5** | Skills bổ sung | 3-4 ngày | 4 skills còn lại + stock screener MCP tool |
| **Phase 6** | Subagents | 3-4 ngày | 4 subagents: market-watcher, news-analyst, portfolio-manager, research |
| **Phase 7** | Hooks & Automation | 2-3 ngày | Morning brief, session summary, portfolio monitor scripts |
| **Phase 8** | Polish & Testing | 3-4 ngày | Test coverage >80%, docs, error handling hoàn chỉnh |

**Tổng ước tính:** 22-30 ngày (một developer, làm part-time ~4h/ngày)

---

## Phase 0 — Project Bootstrap

### MVP Deliverable
Cấu trúc thư mục đầy đủ, môi trường Python hoạt động, `uv run python -c "import vnstock"` chạy được.

### Demo Scenario
> "Sau Phase 0, developer có thể clone repo, chạy `uv sync`, và bắt đầu code ngay — không mất thời gian setup."

### Tech Risks & Mitigations
| Rủi ro | Xác suất | Mitigation |
|--------|----------|-----------|
| ta-lib cài khó trên macOS/Linux | Cao | Dùng `pandas-ta` thay thế (pure Python, không cần C build) |
| vnstock version conflict | Thấp | Pin exact version trong pyproject.toml |

---

### Task P0-1: Tạo cấu trúc thư mục

**Mô tả:** Tạo toàn bộ skeleton thư mục theo thiết kế trong PLUGIN_DESIGN.md — chỉ tạo file/folder trống, chưa có code.

**Files cần tạo:**
```
vn-stock-trader/
├── pyproject.toml
├── .python-version
├── .gitignore
├── README.md (ngắn gọn)
│
├── mcp-server/
│   ├── pyproject.toml
│   ├── server.py                  (placeholder)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── market.py              (placeholder)
│   │   ├── history.py             (placeholder)
│   │   ├── financials.py          (placeholder)
│   │   ├── news.py                (placeholder)
│   │   ├── screener.py            (placeholder)
│   │   ├── portfolio.py           (placeholder)
│   │   └── insider.py             (placeholder)
│   ├── data_sources/
│   │   ├── __init__.py
│   │   ├── vnstock_client.py      (placeholder)
│   │   ├── vietstock_client.py    (placeholder)
│   │   └── news_scraper.py        (placeholder)
│   ├── cache/
│   │   └── .gitkeep
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py            (placeholder)
│       ├── test_market.py         (placeholder)
│       ├── test_screener.py       (placeholder)
│       └── test_portfolio.py      (placeholder)
│
├── .claude/
│   ├── settings.json              (hooks config)
│   ├── skills/
│   │   ├── technical-analysis.md
│   │   ├── fundamental-analysis.md
│   │   ├── news-impact.md
│   │   ├── stock-screener.md
│   │   ├── sector-compare.md
│   │   └── portfolio-review.md
│   ├── agents/
│   │   ├── market-watcher.md
│   │   ├── news-analyst.md
│   │   ├── portfolio-manager.md
│   │   └── research-agent.md
│   └── commands/
│       ├── analyze.md
│       ├── screen.md
│       ├── portfolio.md
│       ├── news.md
│       ├── compare.md
│       ├── report.md
│       └── alert.md
│
├── scripts/
│   ├── morning_brief.py           (placeholder)
│   ├── session_summary.py         (placeholder)
│   └── portfolio_monitor.py       (placeholder)
│
└── data/
    ├── portfolio.json             (mẫu rỗng)
    └── watchlist.json             (mẫu rỗng)
```

**Dependencies:** Không có.
**Effort:** S (2-3 giờ)

**Acceptance Criteria:**
- [ ] `ls -la` cho thấy đúng cấu trúc như trên
- [ ] Tất cả `__init__.py` tồn tại
- [ ] `.gitignore` bao gồm: `__pycache__/`, `*.pyc`, `.env`, `cache/*.db`, `cache/*.json`

---

### Task P0-2: Tạo pyproject.toml (root + mcp-server)

**Mô tả:** Cấu hình project Python với `uv` làm package manager. Hai pyproject: một cho root (scripts, tests), một cho mcp-server.

**File: `pyproject.toml` (root)**
```toml
[project]
name = "vn-stock-trader"
version = "0.1.0"
description = "Claude plugins/skills for Vietnamese stock traders"
requires-python = ">=3.11"
dependencies = [
    "vnstock>=3.4.0",
    "pandas>=2.0.0",
    "pandas-ta>=0.3.14b",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "pytest-mock>=3.14.0",
    "responses>=0.25.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["mcp-server/tests"]
```

**File: `mcp-server/pyproject.toml`**
```toml
[project]
name = "vn-stock-mcp"
version = "0.1.0"
description = "MCP server for Vietnamese stock market data"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "vnstock>=3.4.0",
    "pandas>=2.0.0",
    "pandas-ta>=0.3.14b",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
vn-stock-mcp = "server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Dependencies:** P0-1
**Effort:** S (1 giờ)

**Acceptance Criteria:**
- [ ] `uv sync` chạy thành công không có lỗi
- [ ] `uv run python -c "import vnstock; import pandas_ta; print('OK')"` in ra `OK`
- [ ] `uv run ruff check .` không có lỗi

---

### Task P0-3: Tạo data/portfolio.json và data/watchlist.json mẫu

**Mô tả:** Schema chuẩn cho portfolio và watchlist — dùng trong toàn bộ project.

**File: `data/portfolio.json`**
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
  "t2_receivable": 0,
  "updated_at": "2026-03-30T08:00:00"
}
```

**File: `data/watchlist.json`**
```json
{
  "symbols": ["HPG", "ACB", "MBB", "FPT", "VHM"],
  "alerts": [
    {
      "symbol": "HPG",
      "condition": "price_below",
      "value": 28000,
      "note": "Vùng hỗ trợ mạnh"
    }
  ],
  "updated_at": "2026-03-30T08:00:00"
}
```

**Dependencies:** P0-1
**Effort:** S (30 phút)

**Acceptance Criteria:**
- [ ] Cả hai file là valid JSON (`python -m json.tool data/portfolio.json`)
- [ ] Schema được comment trong file

---

## Phase 1 — Data Layer

### MVP Deliverable
Ba module data source hoạt động: `vnstock_client.py` (wrap vnstock), `vietstock_client.py` (crawl Vietstock), `news_scraper.py` (crawl CafeF/Vietstock tin tức) — tất cả có SQLite cache.

### Demo Scenario
> "Sau Phase 1, developer gõ `python -c "from mcp_server.data_sources import vnstock_client; print(vnstock_client.get_stock_price('VNM'))"` và thấy dữ liệu giá thực của VNM."

### Tech Risks & Mitigations
| Rủi ro | Xác suất | Mitigation |
|--------|----------|-----------|
| TCBS API thay đổi endpoint (đã xảy ra 2024-2025) | Cao | Cache 15 phút; fallback sang VCI source của vnstock |
| Vietstock block crawler (rate limit, bot detection) | Trung | User-Agent rotation, delay 1-2s, exponential backoff |
| pandas-ta tính TA cho series ngắn → NaN | Thấp | Min periods check; trả về None thay vì crash |

---

### Task P1-1: Implement `vnstock_client.py`

**Mô tả:** Wrapper quanh thư viện `vnstock` — chuẩn hóa output thành Python dict/DataFrame, xử lý lỗi gracefully, cache SQLite 15 phút.

**File:** `mcp-server/data_sources/vnstock_client.py`

**Functions cần implement:**

```python
def get_stock_price(symbol: str) -> dict:
    """
    Trả về: {
        "symbol": "VNM",
        "price": 75000,
        "change": 1000,
        "pct_change": 1.35,
        "open": 74000,
        "high": 75500,
        "low": 73500,
        "volume": 1250000,
        "value": 93750000000,
        "reference_price": 74000,
        "ceiling": 79180,
        "floor": 68820,
        "foreign_buy_vol": 50000,
        "foreign_sell_vol": 30000,
        "foreign_room_pct": 42.3,
        "timestamp": "2026-03-30T10:30:00"
    }
    """

def get_stock_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    period: "1m", "3m", "6m", "1y", "2y", "5y"
    Columns: date, open, high, low, close, volume
    Index: DatetimeIndex
    """

def get_financial_report(symbol: str, period: int = 4) -> dict:
    """
    period: số quý gần nhất (4 = 1 năm)
    Trả về: {
        "income_statement": [...],
        "balance_sheet": [...],
        "cash_flow": [...],
        "ratios": {
            "pe": x, "pb": x, "roe": x, "roa": x,
            "net_margin": x, "debt_equity": x,
            "eps": x, "bvps": x
        }
    }
    """

def get_market_overview() -> dict:
    """
    Trả về snapshot thị trường:
    {
        "vn_index": {"value": 1782.5, "change": -3.2, "pct": -0.18},
        "hnx_index": {...},
        "upcom_index": {...},
        "total_volume": 850000000,
        "total_value_bn_vnd": 23500,
        "advance": 245,
        "decline": 198,
        "unchanged": 57,
        "ceiling": 12,
        "floor": 8,
        "foreign_buy_bn": 156.3,
        "foreign_sell_bn": 203.7,
        "foreign_net_bn": -47.4
    }
    """

def get_top_movers(n: int = 10) -> dict:
    """Top gainers, losers, volume leaders"""

def get_sector_peers(symbol: str) -> list[str]:
    """Danh sách mã cùng ngành ICB sub-sector"""
```

**Caching strategy (SQLite):**
```python
# mcp-server/cache/cache.py
class SQLiteCache:
    DB_PATH = "mcp-server/cache/vn_stock.db"
    TTL = {
        "price": 900,          # 15 phút
        "history": 3600,       # 1 giờ
        "financial": 86400,    # 1 ngày
        "market": 300,         # 5 phút
        "news": 600,           # 10 phút
    }
```

**Rate limiting:**
```python
# Tự động throttle nếu liên tục gọi vnstock
# Max 20 requests/phút (Guest tier) — dùng token bucket
from asyncio import Semaphore
RATE_LIMITER = asyncio.Semaphore(3)  # max 3 concurrent requests
```

**Dependencies:** P0-2
**Effort:** M (6-8 giờ)

**Acceptance Criteria:**
- [ ] `get_stock_price("VNM")` trả về dict với đầy đủ fields
- [ ] `get_stock_history("VNM", "1y")` trả về DataFrame 250+ rows, columns = [date, open, high, low, close, volume]
- [ ] `get_financial_report("VNM", 4)` trả về 4 quý gần nhất với ratios
- [ ] `get_market_overview()` trả về VN-Index và breadth
- [ ] Cache hoạt động: gọi lần 2 trong 15 phút không tạo request mới (verify bằng mock)
- [ ] Không crash khi symbol không tồn tại — trả về `{"error": "Symbol not found"}`
- [ ] Test: `mcp-server/tests/test_vnstock_client.py` với pytest, dùng mock, không gọi API thật

---

### Task P1-2: Implement `vietstock_client.py`

**Mô tả:** Crawler lấy dữ liệu từ Vietstock.vn — tập trung vào financial ratios, báo cáo tài chính, và thông tin ngành. Dùng `httpx` async + `BeautifulSoup`.

**File:** `mcp-server/data_sources/vietstock_client.py`

**Trang cần crawl và data cần lấy:**

| URL | Data | Cache TTL |
|-----|------|-----------|
| `https://finance.vietstock.vn/[SYMBOL]/tai-chinh.htm` | P/E, P/B, ROE, EPS, BVPS, Debt/Equity theo quý | 1 ngày |
| `https://finance.vietstock.vn/[SYMBOL]/bao-cao-tai-chinh.htm` | Income statement, Balance sheet, Cash flow | 1 ngày |
| `https://finance.vietstock.vn/[SYMBOL]/co-ban.htm` | Thông tin cơ bản: vốn hóa, ngành ICB, cổ đông lớn | 6 giờ |
| `https://vietstock.vn/[SYMBOL]/tin-tuc.htm` | Tin tức theo mã (50 tin gần nhất) | 30 phút |
| `https://finance.vietstock.vn/data/financeinfo?Code=[SYMBOL]` | JSON endpoint (nếu có) | 1 giờ |

**Functions:**

```python
async def get_financial_ratios(symbol: str) -> dict:
    """PE, PB, ROE, ROA, EPS, BVPS theo quý — từ bảng HTML Vietstock"""

async def get_income_statement(symbol: str, num_quarters: int = 8) -> list[dict]:
    """Doanh thu, lãi gộp, lãi ròng theo quý"""

async def get_balance_sheet(symbol: str, num_quarters: int = 4) -> list[dict]:
    """Tổng tài sản, nợ, vốn chủ sở hữu"""

async def get_company_info(symbol: str) -> dict:
    """Tên công ty, ngành ICB, sàn, vốn điều lệ, website"""

async def get_stock_news(symbol: str, limit: int = 20) -> list[dict]:
    """
    [{"title": "...", "url": "...", "date": "...", "source": "vietstock"}]
    """
```

**Anti-blocking headers:**
```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Referer": "https://vietstock.vn/",
}
REQUEST_DELAY_RANGE = (1.0, 2.5)  # random delay giữa các request
```

**Dependencies:** P0-2, P1-1 (dùng chung SQLiteCache)
**Effort:** M (8-10 giờ)

**Acceptance Criteria:**
- [ ] `get_financial_ratios("VNM")` trả về dict với pe, pb, roe >= 1 quý
- [ ] `get_income_statement("VNM", 4)` trả về 4 quý với doanh thu và lãi ròng
- [ ] `get_company_info("VNM")` trả về tên công ty + ngành ICB đúng
- [ ] Không crash khi Vietstock đổi cấu trúc HTML — có fallback `None` cho từng field
- [ ] Tuân thủ delay 1-2s giữa các request (test bằng mock timer)
- [ ] Test: mock HTTP responses bằng `responses` library

---

### Task P1-3: Implement `news_scraper.py`

**Mô tả:** Scraper tin tức thị trường từ CafeF và Vietstock — không phụ thuộc vào mã cổ phiếu cụ thể, lấy tin thị trường chung.

**File:** `mcp-server/data_sources/news_scraper.py`

**Nguồn tin:**

| Nguồn | URL | Loại |
|-------|-----|------|
| CafeF | `https://cafef.vn/thi-truong-chung-khoan.chn` | Tin thị trường TTCK |
| CafeF | `https://cafef.vn/doanh-nghiep.chn` | Tin doanh nghiệp |
| Vietstock | `https://vietstock.vn/thi-truong/tin-thi-truong.htm` | Tin phân tích |
| VNExpress | `https://vnexpress.net/kinh-doanh/chung-khoan` | Tin kinh doanh |

**Functions:**

```python
async def get_market_news(limit: int = 30) -> list[dict]:
    """
    [
      {
        "title": "VN-Index tăng mạnh nhờ dòng tiền...",
        "url": "https://cafef.vn/...",
        "summary": "...",
        "published_at": "2026-03-30T08:15:00",
        "source": "cafef",
        "symbols_mentioned": ["VNM", "HPG"],  # extract từ title/summary
        "category": "market|company|macro"
      }
    ]
    """

async def get_news_by_symbol(symbol: str, limit: int = 10) -> list[dict]:
    """Lọc tin có nhắc đến symbol từ tất cả nguồn"""

def extract_symbols_from_text(text: str) -> list[str]:
    """
    NLP đơn giản: tìm mã chứng khoán trong text
    - Regex: 3-4 ký tự viết hoa (VNM, HPG, ACB...)
    - Lọc false positive (VND, GDP, USD, P/E, ROE...)
    """
```

**Dependencies:** P0-2, P1-1 (SQLiteCache)
**Effort:** M (6-8 giờ)

**Acceptance Criteria:**
- [ ] `get_market_news(10)` trả về 10 tin với đầy đủ title, url, published_at
- [ ] `extract_symbols_from_text("HPG tăng mạnh, NKG cũng tích cực")` → `["HPG", "NKG"]`
- [ ] Không gọi false positive: "VND", "GDP", "USD", "P/E", "ROE" không xuất hiện trong kết quả
- [ ] Cache 30 phút hoạt động đúng

---

### Task P1-4: Implement `ta_calculator.py` (Technical Analysis helper)

**Mô tả:** Wrapper tính các chỉ báo kỹ thuật từ OHLCV DataFrame dùng `pandas-ta`.

**File:** `mcp-server/data_sources/ta_calculator.py`

**Functions:**

```python
def calculate_indicators(df: pd.DataFrame) -> dict:
    """
    Input: DataFrame với columns [open, high, low, close, volume], DatetimeIndex
    Output: {
        "ma20": 74500.0,
        "ma50": 72000.0,
        "ma200": 68000.0,
        "rsi14": 58.3,
        "macd": {"macd": 500, "signal": 420, "histogram": 80},
        "bb": {"upper": 78000, "middle": 74500, "lower": 71000},
        "atr14": 1200.0,
        "volume_ma20": 1100000.0,
        "volume_ratio": 1.35,   # volume hôm nay / volume_ma20
    }
    """

def find_support_resistance(df: pd.DataFrame, lookback: int = 120) -> dict:
    """
    Tìm vùng support/resistance từ 120 phiên gần nhất
    Dùng local min/max + cluster analysis
    """

def detect_patterns(df: pd.DataFrame) -> list[str]:
    """
    Phát hiện patterns:
    - "golden_cross" (MA20 cắt lên MA50 trong 3 phiên)
    - "death_cross" (MA20 cắt xuống MA50 trong 3 phiên)
    - "oversold_bounce" (RSI < 30 + giá tăng)
    - "volume_breakout" (volume > 2x + giá tăng > 2%)
    """

def get_trend(df: pd.DataFrame) -> dict:
    """
    {
        "short_term": "UPTREND",    # MA20 trend
        "medium_term": "SIDEWAYS",  # MA50 trend
        "long_term": "UPTREND",     # MA200 trend
        "strength": "STRONG"        # STRONG / MODERATE / WEAK
    }
    """
```

**Dependencies:** P0-2
**Effort:** S (3-4 giờ)

**Acceptance Criteria:**
- [ ] `calculate_indicators(df)` với 250 rows → không có NaN trong output (ngoại trừ MA200 khi data < 200 ngày)
- [ ] Graceful handling khi data < min_periods → trả về `None` cho chỉ báo đó
- [ ] `detect_patterns` hoạt động đúng với test case kiểm tra golden cross

---

## Phase 2 — MCP Server Core

### MVP Deliverable
MCP server chạy được, kết nối Claude Code với dữ liệu thị trường. Claude có thể gọi `get_stock_price`, `get_market_overview`, `get_stock_history`, `get_financial_report`, `get_news`, `get_portfolio`.

### Demo Scenario
> "Sau Phase 2, trader gõ vào Claude Code: 'Giá VNM hiện tại là bao nhiêu?' → Claude gọi MCP tool → trả về giá thực."

### Tech Risks & Mitigations
| Rủi ro | Xác suất | Mitigation |
|--------|----------|-----------|
| MCP protocol version mismatch | Thấp | Pin `mcp>=1.0.0`, test với `mcp dev` tool |
| Timeout khi vnstock chậm | Trung | Set `httpx.timeout=10s`, retry 2 lần |

---

### Task P2-1: Implement `server.py` — MCP Entry Point

**Mô tả:** File entry point của MCP server — đăng ký tất cả tools, cấu hình transport (stdio), xử lý khởi động.

**File:** `mcp-server/server.py`

```python
"""
VN Stock MCP Server
Entry point: uv run python mcp-server/server.py
"""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from tools.market import register_market_tools
from tools.history import register_history_tools
from tools.financials import register_financial_tools
from tools.news import register_news_tools
from tools.portfolio import register_portfolio_tools
from tools.screener import register_screener_tools

app = Server("vn-stock-mcp")

# Đăng ký tools từ các module
register_market_tools(app)
register_history_tools(app)
register_financial_tools(app)
register_news_tools(app)
register_portfolio_tools(app)
register_screener_tools(app)

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

**Dependencies:** Phase 1 hoàn thành
**Effort:** S (2 giờ)

**Acceptance Criteria:**
- [ ] `uv run python mcp-server/server.py` khởi động không crash
- [ ] `mcp dev mcp-server/server.py` hiển thị danh sách tools
- [ ] Server phản hồi `tools/list` request với đúng tool schemas

---

### Task P2-2: Implement `tools/market.py`

**Mô tả:** Hai MCP tools cốt lõi: lấy snapshot thị trường và giá cổ phiếu.

**File:** `mcp-server/tools/market.py`

**MCP Tools:**

```python
@app.tool()
async def get_market_overview() -> str:
    """
    Lấy snapshot tổng quan thị trường chứng khoán Việt Nam:
    VN-Index, HNX-Index, UPCOM-Index, breadth (số mã tăng/giảm),
    thanh khoản, khối ngoại mua/bán ròng.
    """

@app.tool()
async def get_stock_price(symbol: str) -> str:
    """
    Lấy thông tin giá hiện tại của một mã cổ phiếu Việt Nam.
    symbol: Mã cổ phiếu (VD: "VNM", "HPG", "ACB", "VCB")
    Trả về: giá, % thay đổi, volume, giá tham chiếu, trần/sàn, foreign room.
    Lưu ý: Dữ liệu delay ~15 phút (không phải realtime).
    """

@app.tool()
async def get_top_movers(exchange: str = "HOSE", n: int = 10) -> str:
    """
    Top mã tăng/giảm mạnh nhất và volume cao nhất.
    exchange: "HOSE", "HNX", "UPCOM", hoặc "ALL"
    n: số mã mỗi danh sách (mặc định 10)
    """
```

**Output format:** Markdown string (không phải JSON raw), đã format sẵn để Claude đọc và tóm tắt.

**Dependencies:** P2-1, P1-1
**Effort:** S (2-3 giờ)

**Acceptance Criteria:**
- [ ] Tool schema xuất hiện đúng trong `mcp dev`
- [ ] `get_stock_price("VNM")` trả về markdown string với đủ fields
- [ ] `get_market_overview()` trả về index + breadth + foreign flow
- [ ] Error handling: symbol không hợp lệ → trả về error message bằng tiếng Việt

---

### Task P2-3: Implement `tools/history.py`

**Mô tả:** MCP tool lấy lịch sử giá và tính chỉ báo kỹ thuật.

**File:** `mcp-server/tools/history.py`

```python
@app.tool()
async def get_stock_history(
    symbol: str,
    period: str = "1y",
    include_indicators: bool = True
) -> str:
    """
    Lịch sử giá OHLCV và các chỉ báo kỹ thuật đã tính sẵn.
    symbol: Mã cổ phiếu
    period: "1m", "3m", "6m", "1y", "2y"
    include_indicators: True = tính sẵn MA, RSI, MACD, BB, ATR
    """
```

**Output:** JSON string với OHLCV + indicators + patterns + trend + support_resistance

**Dependencies:** P2-1, P1-1, P1-4
**Effort:** S (2 giờ)

**Acceptance Criteria:**
- [ ] Tool trả về OHLCV + indicators cho 1 năm
- [ ] `include_indicators=True` → có đủ ma20, ma50, ma200, rsi14, macd, bb
- [ ] `detect_patterns` được gọi và patterns được trả về

---

### Task P2-4: Implement `tools/financials.py`

**Mô tả:** MCP tool lấy báo cáo tài chính và chỉ số định giá.

**File:** `mcp-server/tools/financials.py`

```python
@app.tool()
async def get_financial_report(
    symbol: str,
    num_quarters: int = 4,
    report_type: str = "all"
) -> str:
    """
    Báo cáo tài chính và chỉ số định giá của doanh nghiệp.
    symbol: Mã cổ phiếu
    num_quarters: Số quý gần nhất (mặc định 4)
    report_type: "income" | "balance" | "cashflow" | "ratios" | "all"
    """

@app.tool()
async def get_sector_peers(symbol: str) -> str:
    """
    Danh sách cổ phiếu cùng ngành ICB và metrics so sánh.
    Dùng để phân tích peer comparison.
    """
```

**Dependencies:** P2-1, P1-1, P1-2
**Effort:** S (2-3 giờ)

**Acceptance Criteria:**
- [ ] `get_financial_report("VNM", 4)` trả về 4 quý income statement + ratios
- [ ] `get_sector_peers("VNM")` trả về list cổ phiếu ngành FMCG với P/E, P/B, ROE
- [ ] Dữ liệu được merge từ cả vnstock_client và vietstock_client

---

### Task P2-5: Implement `tools/news.py`

**Mô tả:** MCP tool lấy tin tức thị trường và theo mã cổ phiếu.

**File:** `mcp-server/tools/news.py`

```python
@app.tool()
async def get_news(
    symbol: str = "",
    category: str = "market",
    limit: int = 10
) -> str:
    """
    Tin tức thị trường chứng khoán Việt Nam.
    symbol: Mã cổ phiếu (để trống = tin thị trường chung)
    category: "market" | "company" | "macro"
    limit: Số tin (tối đa 30)
    """
```

**Dependencies:** P2-1, P1-3
**Effort:** S (1-2 giờ)

**Acceptance Criteria:**
- [ ] `get_news("")` trả về 10 tin thị trường chung
- [ ] `get_news("VNM")` trả về tin có nhắc đến VNM
- [ ] Mỗi tin có title, summary, url, published_at, source

---

### Task P2-6: Implement `tools/portfolio.py`

**Mô tả:** MCP tool đọc/ghi portfolio local từ `data/portfolio.json`.

**File:** `mcp-server/tools/portfolio.py`

```python
@app.tool()
async def get_portfolio() -> str:
    """
    Đọc danh mục đầu tư từ data/portfolio.json,
    cập nhật giá hiện tại, tính P&L.
    """

@app.tool()
async def update_portfolio(
    action: str,
    symbol: str,
    qty: int,
    price: float,
    notes: str = ""
) -> str:
    """
    Cập nhật danh mục.
    action: "buy" | "sell" | "remove"
    """
```

**Dependencies:** P2-1, P1-1, P0-3
**Effort:** S (2 giờ)

**Acceptance Criteria:**
- [ ] `get_portfolio()` đọc portfolio.json, tính P&L theo giá hiện tại
- [ ] `update_portfolio("buy", "VNM", 500, 75000)` thêm position vào file
- [ ] T+2 cash flow được tính đúng

---

### Task P2-7: Cấu hình Claude Code `.claude/settings.json` — MCP registration

**Mô tả:** Đăng ký MCP server với Claude Code để có thể gọi tools.

**File:** `.claude/settings.json`

```json
{
  "mcpServers": {
    "vn-stock-mcp": {
      "command": "uv",
      "args": ["run", "python", "mcp-server/server.py"],
      "cwd": "/Users/hieutran/projects/vn-stock-trader"
    }
  },
  "hooks": {}
}
```

**Dependencies:** P2-1 đến P2-6
**Effort:** S (30 phút)

**Acceptance Criteria:**
- [ ] Claude Code hiển thị `vn-stock-mcp` trong danh sách MCP servers
- [ ] Trong chat, có thể hỏi "Giá VNM?" và Claude gọi `get_stock_price` thành công

---

## Phase 3 — Skills TA & FA

### MVP Deliverable
2 skill files đầu tiên hoàn chỉnh: `technical-analysis.md` và `fundamental-analysis.md`. Khi trader nhắc đến "TA", "phân tích kỹ thuật", v.v. — Claude tự động load đúng workflow.

### Demo Scenario
> "Sau Phase 3, trader gõ: '/analyze VNM TA' → Claude load skill technical-analysis → gọi MCP tools get_stock_price + get_stock_history → tính indicators → xuất output đúng format markdown có xu hướng, chỉ báo, gợi ý giao dịch."

### Tech Risks & Mitigations
| Rủi ro | Xác suất | Mitigation |
|--------|----------|-----------|
| Claude không load đúng skill | Thấp | Test trigger keywords; viết rõ trong skill frontmatter |
| Output format không nhất quán | Trung | Cố định template trong skill file |

---

### Task P3-1: Viết `.claude/skills/technical-analysis.md`

**Mô tả:** Skill file hướng dẫn Claude thực hiện phân tích kỹ thuật hoàn chỉnh theo workflow 5 bước đã thiết kế.

**File:** `.claude/skills/technical-analysis.md`

**Nội dung theo PLUGIN_DESIGN.md §2.1:**
- Frontmatter với triggers: "phân tích kỹ thuật", "TA", "chart", "xu hướng giá"
- Workflow 5 bước: Thu thập → Tính indicators → Xác định trend → Đánh giá tín hiệu → Điểm vào/ra
- Output template cố định (markdown)
- Lưu ý đặc thù VN: biên độ ±7%/±10%/±15%, T+2, khối ngoại, ATO/ATC

**Bổ sung so với thiết kế:**
- Thêm phần "Biên độ giá còn lại hôm nay" (tính từ giá hiện tại đến trần/sàn)
- Thêm so sánh volume với TB20 cùng khung giờ (morning/afternoon session)

**Dependencies:** P2-2, P2-3
**Effort:** S (2-3 giờ)

**Acceptance Criteria:**
- [ ] Skill file hợp lệ theo Claude skill format (frontmatter đúng)
- [ ] Triggers hoạt động: "phân tích kỹ thuật VNM" kích hoạt skill
- [ ] Output theo đúng template — có đủ: trend 3 timeframe, bảng chỉ báo, vùng S/R, tín hiệu tổng hợp, gợi ý giao dịch
- [ ] Thông tin T+2 và biên độ giá VN được đề cập

---

### Task P3-2: Viết `.claude/skills/fundamental-analysis.md`

**Mô tả:** Skill phân tích cơ bản 5 nhóm chỉ tiêu + định giá fair value.

**File:** `.claude/skills/fundamental-analysis.md`

**Nội dung theo PLUGIN_DESIGN.md §2.2:**
- Workflow 4 bước: Thu thập → Phân tích 5 nhóm → So sánh ngành → Định giá
- 5 nhóm chỉ tiêu: Growth, Profitability, Valuation, Financial Health, Efficiency
- Output template: bảng tăng trưởng, sinh lời, định giá, sức khỏe tài chính
- Lưu ý đặc thù: ngân hàng (P/B, NIM, NPL), BĐS (NAV), thép (HRC price)

**Bổ sung:**
- Thêm ngưỡng benchmark theo ngành (Banking, Real Estate, Consumer)
- Thêm phần "Catalyst sắp tới" (mùa BCTC, cổ tức, phát hành)

**Dependencies:** P2-4
**Effort:** S (2-3 giờ)

**Acceptance Criteria:**
- [ ] Triggers: "phân tích cơ bản", "FA", "BCTC", "định giá", "P/E"
- [ ] Output có Fair Value range với 2 phương pháp (P/E target + P/B target)
- [ ] Đề cập lưu ý đặc thù ngân hàng và BĐS
- [ ] Kết luận rõ ràng: CÓ THỂ MUA / TRUNG LẬP / TRÁNH

---

## Phase 4 — Commands

### MVP Deliverable
4 slash commands cốt lõi hoạt động: `/analyze`, `/screen`, `/portfolio`, `/news`.

### Demo Scenario
> "Sau Phase 4, trader gõ `/analyze VNM` → Claude phân tích đầy đủ TA + FA + tin tức gần nhất của VNM trong một response."
> "Trader gõ `/screen P/E<15 ROE>15% ngân hàng` → Claude tìm được danh sách cổ phiếu ngân hàng đáp ứng tiêu chí."

---

### Task P4-1: Viết `.claude/commands/analyze.md`

**Mô tả:** Command `/analyze [SYMBOL] [mode]` — phân tích tổng hợp hoặc theo mode cụ thể.

**File:** `.claude/commands/analyze.md`

**Syntax:**
```
/analyze VNM          → Phân tích đầy đủ (TA + FA + News)
/analyze VNM TA       → Chỉ Technical Analysis
/analyze VNM FA       → Chỉ Fundamental Analysis
/analyze VNM news     → Chỉ tin tức gần nhất
/analyze VNM sector   → So sánh ngành
```

**Workflow command:**
1. Parse symbol và mode từ arguments
2. Gọi MCP tools cần thiết theo mode
3. Kích hoạt skill tương ứng
4. Ghép output từ nhiều skill nếu cần (mode "all")

**Dependencies:** P3-1, P3-2, P2-2, P2-3, P2-4, P2-5
**Effort:** S (2 giờ)

**Acceptance Criteria:**
- [ ] `/analyze VNM` chạy được và xuất đầy đủ TA + FA + tin tức
- [ ] `/analyze VNM TA` chỉ xuất phần kỹ thuật
- [ ] Error khi symbol không tồn tại: "Không tìm thấy mã [X] trên thị trường VN"
- [ ] Command file có usage examples rõ ràng

---

### Task P4-2: Implement `tools/screener.py` + Task P4-3: Viết `.claude/commands/screen.md`

**Mô tả (P4-2):** MCP tool chạy stock screener dựa trên tiêu chí.

**File:** `mcp-server/tools/screener.py`

```python
@app.tool()
async def screen_stocks(
    exchange: str = "ALL",
    sector: str = "",
    pe_max: float = None,
    pb_max: float = None,
    roe_min: float = None,
    volume_min_bn: float = 0.5,
    price_min: float = None,
    price_max: float = None,
    rsi_max: float = None,
    rsi_min: float = None,
    eps_growth_min: float = None,
    preset: str = "",
    limit: int = 20
) -> str:
    """
    Lọc cổ phiếu theo tiêu chí định lượng.
    preset: "value" | "growth" | "breakout" | "oversold" | "ftse_play"
    """
```

**Logic screener:**
- Fetch danh sách tất cả cổ phiếu từ vnstock (lấy từ cache, update hàng ngày)
- Apply filters theo thứ tự: thanh khoản (loại mã < 200tr/ngày) → exchange → sector → FA filters → TA filters
- Tính composite score cho từng mã
- Trả về top `limit` mã kèm key metrics

**Mô tả (P4-3):** Command `/screen` với natural language parsing.

**Syntax:**
```
/screen value                           → Preset: Value Screen
/screen growth                          → Preset: Growth Screen
/screen P/E<15 ROE>15% ngân hàng       → Custom screen
/screen RSI<30 volume>2x               → Oversold breakout
/screen FTSE                            → FTSE upgrade play
```

**Dependencies:** P1-1, P1-2, P2-1
**Effort:** M (6-8 giờ cho cả P4-2 và P4-3)

**Acceptance Criteria:**
- [ ] `screen_stocks(preset="value")` trả về danh sách cổ phiếu value
- [ ] `screen_stocks(sector="Banking", pb_max=1.5)` lọc đúng ngành ngân hàng với P/B < 1.5
- [ ] `/screen value` cho ra kết quả dạng bảng markdown
- [ ] Natural language `/screen ngân hàng P/B dưới 1.5 ROE trên 15%` được parse đúng
- [ ] Kết quả không bao gồm mã thanh khoản < 200tr/ngày

---

### Task P4-4: Viết `.claude/commands/portfolio.md`

**Mô tả:** Command `/portfolio` cho phân tích và quản lý danh mục.

**File:** `.claude/commands/portfolio.md`

**Syntax:**
```
/portfolio                      → Xem tổng quan danh mục
/portfolio risk                 → Phân tích rủi ro chi tiết (VaR, beta, correlation)
/portfolio buy VNM 1000 75000   → Thêm giao dịch mua
/portfolio sell VNM 500 80000   → Thêm giao dịch bán
/portfolio t2                   → Xem T+2 cash flow
/portfolio rebalance            → Gợi ý tái cơ cấu
```

**Dependencies:** P2-6 (get_portfolio tool), P1-1, P1-4
**Effort:** S (2 giờ)

**Acceptance Criteria:**
- [ ] `/portfolio` xuất tổng P&L và bảng vị thế
- [ ] `/portfolio risk` tính VaR 95% và beta
- [ ] `/portfolio buy VNM 1000 75000` update portfolio.json
- [ ] `/portfolio t2` hiển thị cash flow đúng

---

### Task P4-5: Viết `.claude/commands/news.md`

**Mô tả:** Command `/news` cho tin tức thị trường và theo dõi mã cụ thể.

**File:** `.claude/commands/news.md`

**Syntax:**
```
/news                           → Digest tin tức hôm nay (10 tin)
/news VNM                       → Tin về VNM 7 ngày gần nhất
/news banking                   → Tin ngành ngân hàng
/news macro                     → Tin kinh tế vĩ mô
/news portfolio                 → Tin liên quan đến danh mục cá nhân
```

**Dependencies:** P2-5, P2-6
**Effort:** S (1-2 giờ)

**Acceptance Criteria:**
- [ ] `/news` trả về digest 10 tin quan trọng nhất hôm nay
- [ ] `/news portfolio` lọc tin liên quan đến mã trong portfolio.json
- [ ] Mỗi tin có nhận định ngắn về chiều hướng tác động

---

## Phase 5 — Skills Bổ sung

### MVP Deliverable
4 skills còn lại: `news-impact.md`, `stock-screener.md`, `sector-compare.md`, `portfolio-review.md`.

### Demo Scenario
> "Sau Phase 5, trader gõ '/compare VNM sector' → Claude so sánh VNM với tất cả cổ phiếu ngành FMCG, hiển thị ranking và định giá tương đối."

---

### Task P5-1: Viết `.claude/skills/news-impact.md`

**Nội dung theo PLUGIN_DESIGN.md §2.3:** Phân loại tin → Mapping tin → cổ phiếu → Lịch sử phản ứng → Dự báo T+0 đến T+3.

**Dependencies:** P2-5
**Effort:** S (2 giờ)

---

### Task P5-2: Viết `.claude/skills/stock-screener.md`

**Nội dung theo PLUGIN_DESIGN.md §2.4:** Preset screens (value, growth, breakout, oversold, FTSE), natural language parsing, format output bảng.

**Dependencies:** P4-2
**Effort:** S (1-2 giờ)

---

### Task P5-3: Viết `.claude/skills/sector-compare.md`

**Nội dung theo PLUGIN_DESIGN.md §2.5:** Peer group → metrics collection → relative ranking → valuation gap analysis.

**Dependencies:** P2-4
**Effort:** S (2 giờ)

---

### Task P5-4: Viết `.claude/skills/portfolio-review.md`

**Nội dung theo PLUGIN_DESIGN.md §2.6:** P&L tracking, allocation, VaR, T+2 cash flow, gợi ý tái cơ cấu.

**Dependencies:** P2-6, P1-4
**Effort:** S (2 giờ)

---

### Task P5-5: Viết `.claude/commands/compare.md` và `.claude/commands/report.md`

**compare.md syntax:**
```
/compare VNM sector             → So sánh cùng ngành
/compare VNM vs MWG vs FPT      → So sánh trực tiếp 2-3 mã
```

**report.md syntax:**
```
/report VNM Q4/2025             → Tóm tắt BCTC quý Q4/2025 của VNM
/report VNM annual 2025         → Tóm tắt BCTC năm 2025
```

**Dependencies:** P5-3, P2-4
**Effort:** S (2 giờ)

---

## Phase 6 — Subagents

### MVP Deliverable
4 subagent files trong `.claude/agents/`. Trader có thể spawn agent market-watcher trong phiên giao dịch để nhận cảnh báo tự động.

### Demo Scenario
> "Sau Phase 6, trader gõ 'Hãy theo dõi danh mục của tôi trong phiên chiều và cảnh báo nếu có gì bất thường' → Claude spawn market-watcher agent → agent poll data mỗi 5 phút → alert khi HPG giảm >3%."

---

### Task P6-1: Viết `.claude/agents/market-watcher.md`

**Nội dung theo PLUGIN_DESIGN.md §3.1:**
- Tools: get_market_overview, get_stock_price, get_news
- Logic: Monitor VN-Index breadth + watchlist + price band alerts
- Alert format: 🚨 CAO/TRUNG/THẤP
- Phiên giao dịch awareness: ATO, liên tục sáng, nghỉ trưa, liên tục chiều, ATC

**Dependencies:** P2-2, P2-5
**Effort:** S (2-3 giờ)

---

### Task P6-2: Viết `.claude/agents/news-analyst.md`

**Nội dung theo PLUGIN_DESIGN.md §3.2:**
- Tools: get_news, get_stock_price, get_portfolio, WebSearch, WebFetch
- Schedule: 5:30 (quốc tế), 8:00 (buổi sáng), 11:30 (giữa phiên), 15:00 (sau ATC)
- Cá nhân hóa theo danh mục

**Dependencies:** P2-5, P2-6
**Effort:** S (2 giờ)

---

### Task P6-3: Viết `.claude/agents/portfolio-manager.md`

**Nội dung theo PLUGIN_DESIGN.md §3.3:**
- Daily P&L tracking, risk management, T+2 cash flow
- Position sizing formula: `Max risk per trade = 2% × tổng danh mục`
- Concentration check, correlation monitor

**Dependencies:** P2-6, P1-4
**Effort:** S (2 giờ)

---

### Task P6-4: Viết `.claude/agents/research-agent.md`

**Mô tả:** Agent nghiên cứu chuyên sâu — kết hợp data từ nhiều nguồn để tạo báo cáo đầy đủ về một doanh nghiệp.

**File:** `.claude/agents/research-agent.md`

**Tools:** get_financial_report, get_stock_history, get_news, get_sector_peers, WebFetch
**Output:** Báo cáo nghiên cứu 3-5 trang bằng tiếng Việt: tổng quan, BCTC, TA, so sánh ngành, rủi ro, định giá

**Dependencies:** P2-3, P2-4, P2-5
**Effort:** S (2 giờ)

---

## Phase 7 — Hooks & Automation Scripts

### MVP Deliverable
3 scripts tự động: `morning_brief.py` (8:30), `session_summary.py` (14:50), `portfolio_monitor.py` (mỗi 5 phút trong phiên). Hooks trong settings.json cấu hình để script chạy tự động.

### Demo Scenario
> "Sau Phase 7, lúc 8:30 sáng mỗi ngày, Claude tự động tạo morning brief: tóm tắt thị trường châu Á qua đêm, tin tức quan trọng, danh sách mã cần theo dõi hôm nay."

### Tech Risks & Mitigations
| Rủi ro | Xác suất | Mitigation |
|--------|----------|-----------|
| Script chạy ngoài giờ giao dịch | Trung | Check trading calendar trước khi chạy |
| Script crash không báo lỗi | Thấp | Try/except + log file + alert tới terminal |

---

### Task P7-1: Implement `scripts/morning_brief.py`

**Mô tả:** Script chạy lúc 8:30 — tổng hợp thông tin trước phiên giao dịch.

**Logic:**
```python
async def morning_brief():
    # 1. Kiểm tra ngày giao dịch (bỏ qua cuối tuần/lễ)
    if not is_trading_day(today):
        return

    # 2. Thu thập data
    market = await get_market_overview()          # VN-Index hôm qua
    world_markets = await fetch_world_markets()   # Dow, S&P, Nikkei, CSI300
    news = await get_market_news(limit=15)        # Tin qua đêm
    portfolio = await get_portfolio()             # Trạng thái danh mục

    # 3. Tạo brief bằng Claude API
    brief = await claude_summarize(
        template="morning_brief",
        data={market, world_markets, news, portfolio}
    )

    # 4. In ra terminal (hoặc gửi notification)
    print(brief)
    save_to_file(f"data/briefs/{today}.md")
```

**Dependencies:** Phase 1-4 hoàn thành
**Effort:** M (4-6 giờ)

**Acceptance Criteria:**
- [ ] Script chạy thành công vào sáng ngày giao dịch
- [ ] Bỏ qua thứ 7, chủ nhật
- [ ] Output gồm: thị trường châu Á, tin quan trọng, watchlist hôm nay, danh mục alert
- [ ] Lưu file brief vào `data/briefs/YYYY-MM-DD.md`

---

### Task P7-2: Implement `scripts/session_summary.py`

**Mô tả:** Script chạy lúc 14:50 (sau ATC) — tóm tắt phiên giao dịch.

**Output:**
- VN-Index close + breadth + thanh khoản so với trung bình
- Top 5 mã tăng/giảm mạnh nhất
- P&L danh mục trong ngày
- Tin tức quan trọng trong phiên
- Kế hoạch cho ngày mai

**Dependencies:** P7-1 (dùng lại helper functions)
**Effort:** S (3 giờ)

---

### Task P7-3: Implement `scripts/portfolio_monitor.py`

**Mô tả:** Script chạy mỗi 5 phút trong phiên — theo dõi danh mục và alert bất thường.

**Alert conditions:**
- Mã trong portfolio thay đổi >3% so với tham chiếu
- Volume bất thường >3× TB20 phiên
- Mã đạt price target hoặc stoploss
- VN-Index thay đổi >1% trong 30 phút

**Cách chạy:**
```bash
python scripts/portfolio_monitor.py --interval 300 --portfolio data/portfolio.json
```

**Dependencies:** P7-1, P2-2, P2-6
**Effort:** M (4-5 giờ)

**Acceptance Criteria:**
- [ ] Script chạy liên tục trong phiên (9:00-14:45 VN time)
- [ ] Alert được print ra terminal với timestamp
- [ ] Dừng tự động sau ATC

---

### Task P7-4: Cấu hình hooks trong `.claude/settings.json`

**Mô tả:** Thêm hooks để tự động hóa theo sự kiện trong Claude Code session.

```json
{
  "mcpServers": { ... },
  "hooks": {
    "PostSessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/session_summary.py --quick"
          }
        ]
      }
    ]
  }
}
```

**Dependencies:** P7-1, P7-2
**Effort:** S (1 giờ)

**Acceptance Criteria:**
- [ ] Hook PostSessionEnd chạy session_summary khi kết thúc Claude session
- [ ] Không crash nếu không phải ngày giao dịch

---

## Phase 8 — Polish & Testing

### MVP Deliverable
Test coverage >80% cho MCP server, error handling hoàn chỉnh, README đầy đủ, demo video script.

### Demo Scenario
> "Sau Phase 8, dự án sẵn sàng chia sẻ với trader khác — có thể cài đặt trong 10 phút với `uv sync` + cấu hình Claude Code."

---

### Task P8-1: Unit tests cho data_sources

**Files:**
- `mcp-server/tests/test_vnstock_client.py` — mock vnstock API, test tất cả functions
- `mcp-server/tests/test_vietstock_client.py` — mock HTTP, test HTML parsing
- `mcp-server/tests/test_ta_calculator.py` — test với synthetic OHLCV data
- `mcp-server/tests/test_cache.py` — test SQLite cache TTL

**Effort:** M (6-8 giờ)

**Acceptance Criteria:**
- [ ] `uv run pytest` pass tất cả tests
- [ ] Coverage >80% cho data_sources/
- [ ] Không có network calls thật trong unit tests (tất cả mock)

---

### Task P8-2: Integration tests cho MCP tools

**File:** `mcp-server/tests/test_integration.py`

**Test scenarios:**
- Full flow: `get_stock_price("VNM")` → cache miss → vnstock call → format → return
- Cache hit flow: gọi lần 2 trong TTL → không call vnstock
- Error flow: symbol không tồn tại → error message bằng tiếng Việt
- Screener flow: `screen_stocks(preset="value")` trả về kết quả hợp lệ

**Effort:** M (4-6 giờ)

---

### Task P8-3: Error handling & logging

**Mô tả:** Thêm proper logging và error handling cho tất cả modules.

**Logging:**
```python
import logging
logger = logging.getLogger("vn-stock-mcp")
# Log file: mcp-server/logs/vn_stock_mcp.log
# Format: [timestamp] [level] [module] message
```

**Error messages cần chuẩn hóa (tiếng Việt):**
- Symbol không tồn tại: "Mã cổ phiếu '{symbol}' không tồn tại trên thị trường VN."
- Vietstock không phản hồi: "Vietstock.vn tạm thời không phản hồi. Dữ liệu từ cache (cập nhật lần cuối: {time})."
- vnstock rate limit: "Đang bị rate limit. Vui lòng đợi {n} giây."
- Thị trường đóng cửa: "Thị trường đóng cửa. Dữ liệu giá là từ phiên giao dịch ngày {date}."

**Effort:** S (3-4 giờ)

---

### Task P8-4: README và documentation

**File:** `README.md`

**Nội dung:**
1. Giới thiệu project
2. Yêu cầu: Python 3.11+, uv, Claude Code
3. Cài đặt (3 bước)
4. Cấu hình Claude Code MCP
5. Danh sách commands có thể dùng
6. Ví dụ demo
7. Giới hạn (delay 15 phút, không dành cho day trading)

**Effort:** S (2 giờ)

---

## Chiến lược Testing cho Toàn dự án

### Nguyên tắc chung

| Layer | Test Type | Tools | Network? |
|-------|-----------|-------|---------|
| data_sources/ | Unit tests | pytest + responses | ❌ Mock hoàn toàn |
| tools/ | Unit + Integration | pytest + pytest-asyncio | ❌ Mock data_sources |
| MCP server | Integration | `mcp dev` + manual | ✅ Real (staging) |
| Skills/Commands | Manual | Claude Code chat | ✅ Real |

### Test Data
- Tạo `mcp-server/tests/fixtures/` với sample JSON responses từ vnstock và Vietstock
- Fixtures được cập nhật định kỳ (mỗi tuần) để test vẫn sát thực tế

### CI/CD
```yaml
# .github/workflows/test.yml
- Run: uv run pytest --cov=mcp-server --cov-report=term-missing
- Run: uv run ruff check .
- On push to main only
```

### Smoke tests (chạy thủ công mỗi ngày giao dịch)
```bash
python scripts/smoke_test.py
# Kiểm tra: vnstock API alive, Vietstock accessible, cache writable
```

---

## Chi tiết Data Layer

### SQLite Schema

```sql
CREATE TABLE cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    cached_at INTEGER NOT NULL,
    ttl INTEGER NOT NULL
);

CREATE TABLE trade_calendar (
    date TEXT PRIMARY KEY,
    is_trading_day INTEGER NOT NULL
);

CREATE TABLE stock_list (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    exchange TEXT,
    sector TEXT,
    sub_sector TEXT,
    market_cap_bn REAL,
    updated_at INTEGER
);
```

### Cache invalidation strategy

- **Giá real-time:** TTL 15 phút (vnstock delay thực tế)
- **Lịch sử giá:** TTL 1 giờ (update cuối phiên)
- **Tài chính:** TTL 24 giờ (update hàng ngày)
- **Tin tức:** TTL 30 phút
- **Market overview:** TTL 5 phút
- **Stock list:** TTL 7 ngày

### Rate limiting strategy

```
vnstock (Guest tier): 20 req/phút
→ Token bucket: refill 20 tokens/60s
→ Mỗi API call consume 1 token
→ Wait nếu bucket empty

Vietstock crawl:
→ Fixed delay: random(1.0, 2.5) giây giữa requests
→ Exponential backoff khi gặp 429/503: 5s, 15s, 60s
→ Circuit breaker: dừng crawl sau 5 lỗi liên tiếp, retry sau 10 phút
```

### Vietstock crawl — chi tiết kỹ thuật

**Session management:**
```python
# Vietstock dùng cookie-based session
async def get_session() -> httpx.AsyncClient:
    client = httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=10.0,
    )
    # Khởi tạo session bằng cách load homepage trước
    await client.get("https://vietstock.vn/")
    return client
```

**HTML parsing strategy:**
- Dùng CSS selectors thay vì XPath (dễ maintain hơn khi Vietstock đổi layout)
- Mỗi parser có version number — khi HTML thay đổi, bump version và log warning
- Fallback: nếu parser fail, return `None` và log error (không crash toàn bộ tool)

---

## Cấu trúc Project Cuối cùng (Phase 8 xong)

```
vn-stock-trader/
│
├── CLAUDE.md
├── MARKET_ANALYSIS.md
├── PLUGIN_DESIGN.md
├── IMPLEMENTATION_PLAN.md            ← File này
├── README.md
├── pyproject.toml
├── .python-version                   (3.11)
├── .gitignore
│
├── mcp-server/
│   ├── pyproject.toml
│   ├── server.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── market.py                 ✅ get_market_overview, get_stock_price, get_top_movers
│   │   ├── history.py                ✅ get_stock_history (with TA indicators)
│   │   ├── financials.py             ✅ get_financial_report, get_sector_peers
│   │   ├── news.py                   ✅ get_news
│   │   ├── screener.py               ✅ screen_stocks (5 presets + custom)
│   │   ├── portfolio.py              ✅ get_portfolio, update_portfolio
│   │   └── insider.py                (Phase 2 / P2 — dữ liệu giao dịch nội bộ)
│   ├── data_sources/
│   │   ├── __init__.py
│   │   ├── vnstock_client.py         ✅ Wrapper vnstock + TCBS
│   │   ├── vietstock_client.py       ✅ Crawl Vietstock (FA ratios, BCTC)
│   │   ├── news_scraper.py           ✅ CafeF + Vietstock news
│   │   └── ta_calculator.py          ✅ pandas-ta wrapper
│   ├── cache/
│   │   ├── cache.py                  ✅ SQLiteCache class
│   │   └── vn_stock.db               (generated, gitignored)
│   ├── logs/
│   │   └── .gitkeep
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── fixtures/                 (sample JSON responses)
│       ├── test_vnstock_client.py
│       ├── test_vietstock_client.py
│       ├── test_ta_calculator.py
│       ├── test_cache.py
│       ├── test_market.py
│       ├── test_screener.py
│       ├── test_portfolio.py
│       └── test_integration.py
│
├── .claude/
│   ├── settings.json                 ✅ MCP registration + hooks
│   ├── skills/
│   │   ├── technical-analysis.md     ✅
│   │   ├── fundamental-analysis.md   ✅
│   │   ├── news-impact.md            ✅
│   │   ├── stock-screener.md         ✅
│   │   ├── sector-compare.md         ✅
│   │   └── portfolio-review.md       ✅
│   ├── agents/
│   │   ├── market-watcher.md         ✅
│   │   ├── news-analyst.md           ✅
│   │   ├── portfolio-manager.md      ✅
│   │   └── research-agent.md         ✅
│   └── commands/
│       ├── analyze.md                ✅
│       ├── screen.md                 ✅
│       ├── portfolio.md              ✅
│       ├── news.md                   ✅
│       ├── compare.md                ✅
│       ├── report.md                 ✅
│       └── alert.md                  (Phase 2 / P2)
│
├── scripts/
│   ├── morning_brief.py              ✅
│   ├── session_summary.py            ✅
│   ├── portfolio_monitor.py          ✅
│   └── smoke_test.py                 ✅
│
└── data/
    ├── portfolio.json                ✅ (user-managed)
    ├── watchlist.json                ✅ (user-managed)
    └── briefs/                       (generated daily)
```

---

## Summary bảng task theo Phase

| Phase | Tasks | Effort tổng | Blocker? |
|-------|-------|-------------|---------|
| 0 | P0-1, P0-2, P0-3 | ~1 ngày | Không |
| 1 | P1-1, P1-2, P1-3, P1-4 | ~4 ngày | Cần internet để kiểm tra Vietstock HTML |
| 2 | P2-1 đến P2-7 | ~4 ngày | Phase 1 phải xong |
| 3 | P3-1, P3-2 | ~1.5 ngày | Phase 2 phải xong |
| 4 | P4-1 đến P4-5 | ~3 ngày | Phase 3 phải xong |
| 5 | P5-1 đến P5-5 | ~2 ngày | Phase 4 và tools phải xong |
| 6 | P6-1 đến P6-4 | ~2 ngày | Phase 2 phải xong |
| 7 | P7-1 đến P7-4 | ~3 ngày | Phase 1-4 phải xong |
| 8 | P8-1 đến P8-4 | ~3 ngày | Tất cả phases xong |

**Critical path:** P0 → P1-1 → P2-1 → P2-2 → P3-1 → P4-1

---

## Định nghĩa "Done" cho toàn bộ project

Dự án được coi là hoàn thành khi trader có thể:

1. ✅ Gõ `/analyze VNM` và nhận phân tích TA + FA đầy đủ
2. ✅ Gõ `/screen value` và nhận danh sách cổ phiếu giá trị
3. ✅ Gõ `/portfolio` và thấy P&L cập nhật theo giá hiện tại
4. ✅ Gõ `/news portfolio` và nhận tin tức liên quan đến danh mục cá nhân
5. ✅ Nhận morning brief tự động lúc 8:30 sáng mỗi ngày giao dịch
6. ✅ Nhận alert khi mã trong danh mục biến động >3%
7. ✅ `uv run pytest` pass với coverage >80%

---

*Kế hoạch được tạo 2026-03-30 dựa trên MARKET_ANALYSIS.md và PLUGIN_DESIGN.md*
*Cập nhật khi có thay đổi về tech stack hoặc scope*

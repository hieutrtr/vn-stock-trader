# Thiết kế Bộ Claude Plugin cho Trader Chứng khoán Việt Nam

**Ngày thiết kế:** 2026-03-29
**Căn cứ:** MARKET_ANALYSIS.md — nghiên cứu thị trường tháng 3/2026
**Mục tiêu:** Bộ plugin hoàn chỉnh, chi tiết đủ để bắt tay implement ngay

---

## Tổng quan Kiến trúc

```
Claude Code (giao diện chính của trader)
        │
        ├── Skills        → Hướng dẫn Claude làm từng loại phân tích
        ├── Subagents     → Agent chuyên biệt chạy độc lập
        ├── Commands      → Slash commands /analyze, /screen, /portfolio...
        ├── Hooks         → Tự động hóa theo sự kiện & lịch cố định
        └── MCP Server    → Tools lấy dữ liệu thực từ vnstock / SSI API
```

**Data flow:**
```
Trader gõ lệnh
     → Claude Code nhận
     → Gọi MCP tools (get_stock_price, get_financial_report...)
     → MCP server fetch vnstock/TCBS (delay ~15p) + Vietstock crawl
     → Data trả về Claude
     → Claude chạy Skill tương ứng (TA tính local bằng ta-lib)
     → Output phân tích tiếng Việt cho trader
```

> ⚠️ **Lưu ý về data stack:** Hệ thống dùng dữ liệu delay ~15 phút — phù hợp với **swing trader** (nắm giữ nhiều ngày), **KHÔNG phù hợp** với day trader hoặc scalper cần giá realtime. Chi phí data: **$0** (miễn phí, không cần tài khoản broker).

---

## 1. CẤU TRÚC THƯ MỤC

```
vn-stock-trader/
│
├── CLAUDE.md
├── MARKET_ANALYSIS.md
├── PLUGIN_DESIGN.md                     ← File này
│
├── .claude/
│   ├── settings.json                    ← Hooks cấu hình
│   ├── skills/                          ← 6 skill files
│   │   ├── technical-analysis.md
│   │   ├── fundamental-analysis.md
│   │   ├── news-impact.md
│   │   ├── stock-screener.md
│   │   ├── sector-compare.md
│   │   └── portfolio-review.md
│   ├── agents/                          ← 4 subagent files
│   │   ├── market-watcher.md
│   │   ├── news-analyst.md
│   │   ├── portfolio-manager.md
│   │   └── research-agent.md
│   └── commands/                        ← 7 slash command files
│       ├── analyze.md
│       ├── screen.md
│       ├── portfolio.md
│       ├── news.md
│       ├── compare.md
│       ├── report.md
│       └── alert.md
│
├── mcp-server/                          ← MCP server Python
│   ├── pyproject.toml
│   ├── README.md
│   ├── server.py                        ← Entry point
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── market.py                    ← get_market_overview, get_stock_price
│   │   ├── history.py                   ← get_stock_history
│   │   ├── financials.py                ← get_financial_report
│   │   ├── news.py                      ← get_news
│   │   ├── screener.py                  ← screen_stocks
│   │   ├── portfolio.py                 ← get_portfolio (local JSON)
│   │   └── insider.py                   ← get_insider_trades
│   ├── data_sources/
│   │   ├── __init__.py
│   │   ├── vnstock_client.py            ← vnstock wrapper (TCBS, delay ~15p)
│   │   ├── vietstock_client.py          ← Vietstock crawl (tin tức, BCTC, chỉ số TC)
│   │   └── news_scraper.py              ← Vietstock / CafeF scraper
│   └── tests/
│       ├── test_market.py
│       ├── test_screener.py
│       └── test_portfolio.py
│
└── scripts/
    ├── morning_brief.py                 ← Chạy lúc 8:30
    ├── session_summary.py               ← Chạy lúc 14:50
    └── portfolio_monitor.py             ← Chạy mỗi 5 phút trong phiên
```

---

## 2. SKILLS (`.claude/skills/`)

> Skills là file markdown hướng dẫn Claude cách thực hiện một loại phân tích cụ thể. Claude sẽ load skill khi trader gọi hoặc khi command tương ứng kích hoạt.

---

### 2.1 `technical-analysis.md`

```markdown
---
name: technical-analysis
description: Phân tích kỹ thuật một mã cổ phiếu Việt Nam
triggers:
  - "phân tích kỹ thuật"
  - "TA"
  - "chart"
  - "xu hướng giá"
---

# Skill: Phân tích Kỹ thuật (Technical Analysis)

## Mục tiêu
Phân tích xu hướng giá, momentum, và tín hiệu mua/bán dựa trên dữ liệu giá lịch sử.

## Quy trình thực hiện

### Bước 1 — Thu thập dữ liệu
Gọi MCP tools:
- `get_stock_price(symbol)` → giá hiện tại, volume, giá tham chiếu
- `get_stock_history(symbol, period="1y")` → OHLCV 1 năm gần nhất

### Bước 2 — Tính các chỉ báo kỹ thuật
Từ dữ liệu OHLCV, tính:

| Chỉ báo | Tham số | Ý nghĩa |
|---------|---------|---------|
| MA20 | 20 phiên | Xu hướng ngắn hạn |
| MA50 | 50 phiên | Xu hướng trung hạn |
| MA200 | 200 phiên | Xu hướng dài hạn |
| RSI | 14 phiên | Quá mua (>70) / quá bán (<30) |
| MACD | 12/26/9 | Momentum, divergence |
| Bollinger Bands | 20/2σ | Biến động, breakout |
| Volume MA | 20 phiên | So sánh volume hiện tại |
| ATR | 14 phiên | Biến động thực bình quân |

### Bước 3 — Xác định xu hướng
1. **Trend**: So sánh giá hiện tại với MA20, MA50, MA200
   - Giá > MA20 > MA50 > MA200 → Uptrend mạnh
   - Giá < MA20 < MA50 < MA200 → Downtrend mạnh
   - Không đồng đều → Sideways hoặc chuyển trend
2. **Support/Resistance**: Xác định vùng giá quan trọng từ 6 tháng gần nhất
3. **Pattern**: Tìm các pattern phổ biến (Golden Cross, Death Cross, breakout)

### Bước 4 — Đánh giá tín hiệu
Tổng hợp tín hiệu từ nhiều chỉ báo:
- 🟢 **MUA** khi: ≥4/6 chỉ báo tích cực, volume xác nhận
- 🟡 **CHỜ** khi: tín hiệu hỗn hợp, thiếu xác nhận
- 🔴 **BÁN/TRÁNH** khi: ≥4/6 chỉ báo tiêu cực

### Bước 5 — Xác định điểm vào/ra
- **Điểm mua lý tưởng**: Gần support, RSI <40, volume tăng
- **Stoploss gợi ý**: Dưới support gần nhất hoặc 1.5×ATR
- **Target**: Resistance gần nhất hoặc 2:1 reward/risk

## Định dạng Output

```
## 📊 Phân tích Kỹ thuật: [SYMBOL] — [Ngày]

**Giá hiện tại:** [giá] VND ([+/-]% so với tham chiếu)
**Volume:** [volume] cp ([+/-]% so với TB20 phiên)

### Xu hướng
- Ngắn hạn (MA20): [TĂNG/GIẢM/NGANG]
- Trung hạn (MA50): [TĂNG/GIẢM/NGANG]
- Dài hạn (MA200): [TĂNG/GIẢM/NGANG]

### Chỉ báo
| Chỉ báo | Giá trị | Tín hiệu |
|---------|---------|---------|
| RSI(14) | [x] | [Quá mua/Bình thường/Quá bán] |
| MACD | [x] | [Tích cực/Tiêu cực] |
| BB | Giá [trong/trên/dưới] band | [...] |

### Vùng giá quan trọng
- **Kháng cự:** [giá1], [giá2]
- **Hỗ trợ:** [giá1], [giá2]

### Tín hiệu tổng hợp: 🟢 MUA / 🟡 CHỜ / 🔴 BÁN

### Gợi ý giao dịch
- Vào lệnh: [vùng giá]
- Stoploss: [giá] (-[%])
- Target 1: [giá] (+[%])
- Target 2: [giá] (+[%])
- R:R ratio: [x:1]

### ⚠️ Lưu ý
[Rủi ro đặc thù, sự kiện sắp tới, volume cảnh báo, v.v.]
```

## Lưu ý thị trường Việt Nam
- **Biên độ giá:** ±7% HOSE, ±10% HNX, ±15% UPCOM — stoploss cần tính đến
- **ATO (9:00-9:15) và ATC (14:30-14:45):** Volume/giá có thể bất thường
- **T+2:** Cổ phiếu mua hôm nay chỉ bán được sau 2 phiên → ảnh hưởng chiến lược
- **Khối ngoại:** Kiểm tra foreign room còn lại khi mua cổ phiếu blue-chip
- **Thanh khoản:** Cổ phiếu dưới 1 tỷ VND/ngày — cẩn thận kẹt hàng
```

---

### 2.2 `fundamental-analysis.md`

```markdown
---
name: fundamental-analysis
description: Phân tích cơ bản từ báo cáo tài chính
triggers:
  - "phân tích cơ bản"
  - "FA"
  - "BCTC"
  - "định giá"
  - "P/E"
---

# Skill: Phân tích Cơ bản (Fundamental Analysis)

## Mục tiêu
Đánh giá sức khỏe tài chính và định giá hợp lý của doanh nghiệp.

## Quy trình thực hiện

### Bước 1 — Thu thập dữ liệu tài chính
Gọi MCP tools:
- `get_financial_report(symbol, period="4q")` → 4 quý gần nhất
- `get_stock_price(symbol)` → giá thị trường hiện tại

### Bước 2 — Phân tích theo 5 nhóm chỉ tiêu

#### Nhóm 1: Tăng trưởng (Growth)
- Tăng trưởng doanh thu YoY, QoQ
- Tăng trưởng lợi nhuận ròng YoY, QoQ
- CAGR 3 năm (nếu có đủ data)
- **Ngưỡng tốt:** Tăng trưởng >15%/năm bền vững

#### Nhóm 2: Sinh lời (Profitability)
- ROE (Return on Equity) — so sánh với TB ngành
- ROA (Return on Assets)
- Net Profit Margin — xu hướng mở rộng hay thu hẹp?
- EBITDA Margin
- **Ngưỡng tốt:** ROE >15%, NPM >10% (tùy ngành)

#### Nhóm 3: Định giá (Valuation)
- P/E (Price/Earnings) — so TB ngành và lịch sử
- P/B (Price/Book) — đặc biệt quan trọng với ngân hàng
- EV/EBITDA
- PEG = P/E ÷ EPS Growth
- **Phương pháp DCF đơn giản:** FCF × (1+g)/(r-g)

#### Nhóm 4: Thanh khoản & Đòn bẩy (Financial Health)
- Current Ratio (Thanh khoản hiện hành) — nên >1.5
- Quick Ratio — nên >1.0
- Debt/Equity — tùy ngành (ngân hàng cao là bình thường)
- Interest Coverage Ratio — nên >3×
- Net Debt/EBITDA

#### Nhóm 5: Hiệu quả Hoạt động (Efficiency)
- Asset Turnover
- Inventory Turnover (với sản xuất, bán lẻ)
- Days Sales Outstanding (DSO) — phải thu bao lâu?
- Cash Conversion Cycle

### Bước 3 — So sánh ngành
Gọi `get_sector_peers(symbol)` → lấy danh sách cổ phiếu cùng ngành ICB
So sánh P/E, ROE, tăng trưởng với median ngành

### Bước 4 — Tổng hợp & Định giá hợp lý
- Phương pháp 1: P/E target × EPS dự báo
- Phương pháp 2: P/B target × BVPS
- Fair value range: trung bình 2 phương pháp ± 15%

## Định dạng Output

```
## 💼 Phân tích Cơ bản: [SYMBOL] — [Ngày]

**Ngành:** [ICB sector/sub-sector]
**Giá hiện tại:** [x] VND | **Market Cap:** [x] tỷ VND

### Tăng trưởng
| Chỉ tiêu | Q[n]/Q[n-1] | YoY | TB 3 năm |
|----------|-------------|-----|---------|
| Doanh thu | +/-x% | +/-x% | +x% |
| Lợi nhuận ròng | +/-x% | +/-x% | +x% |
| EPS | [x] VND | | |

### Sinh lời
| Chỉ tiêu | Hiện tại | TB ngành | Đánh giá |
|----------|----------|----------|---------|
| ROE | x% | x% | ✅/⚠️/❌ |
| Net Margin | x% | x% | ✅/⚠️/❌ |

### Định giá
| Chỉ tiêu | Hiện tại | TB ngành | Lịch sử 5Y |
|----------|----------|----------|-----------|
| P/E | x | x | x |
| P/B | x | x | x |
| EV/EBITDA | x | x | x |

**Fair Value ước tính:** [x] – [y] VND
**So với giá hiện tại:** [CHIẾT KHẤU x% / PHÍ TRỘI x%]

### Sức khỏe Tài chính
- Nợ/Vốn chủ: [x] — [Thấp/Trung bình/Cao]
- Interest Coverage: [x]× — [An toàn/Cần theo dõi/Rủi ro]
- Tiền & tương đương: [x] tỷ VND

### 🔍 Điểm nổi bật
[3-5 điểm quan trọng nhất từ phân tích]

### ⚠️ Rủi ro cần theo dõi
[Các rủi ro đặc thù: nợ cao, margin thu hẹp, dòng tiền yếu...]

### Kết luận: ✅ CÓ THỂ MUA / ⚠️ TRUNG LẬP / ❌ TRÁNH
**Lý do ngắn gọn:** [2-3 câu]
```

## Lưu ý đặc thù VN
- **Ngân hàng:** Dùng P/B, NIM, NPL ratio thay vì các chỉ tiêu thông thường
- **BĐS:** FCF thường âm, dùng NAV và backlog
- **Thép (HPG, HSG, NKG):** Theo dõi giá HRC, coal và tỷ giá USD/VND
- **Năm tài chính:** Hầu hết kết thúc 31/12; một số doanh nghiệp có năm tài chính lệch
- **BCTC hợp nhất vs. riêng lẻ:** Luôn ưu tiên hợp nhất
```

---

### 2.3 `news-impact.md`

```markdown
---
name: news-impact
description: Phân tích tác động tin tức lên giá cổ phiếu
triggers:
  - "tin tức"
  - "news"
  - "tác động"
  - "ảnh hưởng"
---

# Skill: Phân tích Tác động Tin tức

## Mục tiêu
Đọc tin tức → xác định cổ phiếu bị ảnh hưởng → dự đoán chiều hướng và mức độ tác động.

## Quy trình thực hiện

### Bước 1 — Thu thập tin tức
Gọi `get_news(symbol?)`:
- Nếu có symbol: lấy tin liên quan trực tiếp
- Nếu không có symbol: lấy tin thị trường chung (macro, ngành)

### Bước 2 — Phân loại tin tức

#### Theo mức độ tác động
| Loại | Ví dụ | Thời gian tác động |
|------|-------|-------------------|
| 🔴 **Đột biến** | Kết quả kinh doanh, thay đổi lãnh đạo, M&A | 1-3 phiên |
| 🟠 **Quan trọng** | Chính sách ngành, tin macro VN/thế giới | 3-10 phiên |
| 🟡 **Bình thường** | Tin kinh doanh thông thường, phân tích analyst | Dài hạn |

#### Theo chiều hướng
- **Tích cực:** Lợi nhuận vượt kỳ vọng, hợp đồng lớn, nới room ngoại, chính sách hỗ trợ
- **Tiêu cực:** Lỗ, nợ xấu tăng, điều tra, lãnh đạo bị bắt, dự án đình trệ
- **Hỗn hợp:** Cần đọc kỹ context

### Bước 3 — Mapping "tin → cổ phiếu"
Xác định các mã bị ảnh hưởng:
- **Trực tiếp:** Mã được nhắc trong tin
- **Gián tiếp:** Công ty cùng ngành, đối thủ cạnh tranh, supplier/customer
- **Vĩ mô:** Nhóm cổ phiếu nhạy cảm với lãi suất, tỷ giá, giá hàng hóa

### Bước 4 — Lịch sử phản ứng
Với mỗi mã bị ảnh hưởng:
- Tin tương tự trong quá khứ → giá phản ứng thế nào?
- Consensus kỳ vọng thị trường vs. tin thực tế (beat/miss)

### Bước 5 — Dự báo ngắn hạn
- T+0: Kỳ vọng giá mở cửa/ATO
- T+1 đến T+3: Diễn biến có thể sau khi hấp thụ tin

## Định dạng Output

```
## 📰 Phân tích Tin tức — [Ngày]

### Tin nổi bật
1. **[Tiêu đề tin]** — [Nguồn] — [Giờ đăng]
   - Tóm tắt: [2-3 câu]
   - Mức độ quan trọng: 🔴/🟠/🟡

### Cổ phiếu bị ảnh hưởng
| Mã | Chiều | Mức độ | Lý do |
|----|-------|--------|-------|
| [SYMBOL] | 📈/📉 | Cao/TB/Thấp | [giải thích] |

### Nhận định ngắn hạn
[Phân tích tổng hợp: thị trường sẽ phản ứng thế nào?]

### Cổ phiếu cần theo dõi hôm nay
- **Mua quan sát:** [danh sách mã + lý do]
- **Cẩn thận:** [danh sách mã + rủi ro]
```

## Nguồn tin ưu tiên
1. HNX.vn / HOSE.vn — thông báo chính thức
2. CafeF.vn — tin tức tài chính nhanh
3. VNExpress Kinh doanh — macro
4. Vietstock.vn — phân tích cổ phiếu
5. NDH.vn / TheSaigonTimes — tin doanh nghiệp
```

---

### 2.4 `stock-screener.md`

```markdown
---
name: stock-screener
description: Lọc cổ phiếu theo tiêu chí định lượng
triggers:
  - "lọc cổ phiếu"
  - "screen"
  - "tìm cổ phiếu"
  - "tiêu chí"
---

# Skill: Lọc Cổ phiếu (Stock Screener)

## Mục tiêu
Tìm cổ phiếu thỏa mãn bộ tiêu chí định lượng của trader trong ~1.600 mã VN.

## Các bộ lọc có sẵn

### Bộ lọc Cơ bản
| Tiêu chí | Ký hiệu | Ví dụ |
|----------|---------|-------|
| Sàn niêm yết | exchange | HOSE, HNX, UPCOM |
| Ngành ICB | sector | Banking, Real Estate, Steel |
| Vốn hóa | market_cap | >1000 tỷ, <500 tỷ |
| Giá hiện tại | price | 10.000-50.000 VND |
| Thanh khoản | avg_volume_20d | >1 tỷ VND/ngày |
| % thay đổi giá | price_change | >5% (1 tuần), <-10% (1 tháng) |

### Bộ lọc Kỹ thuật
| Tiêu chí | Ký hiệu | Ví dụ |
|----------|---------|-------|
| Giá vs MA20 | price_vs_ma20 | Trên, Dưới, Vừa cắt qua |
| RSI | rsi | <30 (quá bán), >70 (quá mua) |
| Volume bất thường | volume_spike | >2× TB20 phiên |
| Gần trần/sàn | near_ceiling_floor | Trong biên 2% |
| Golden/Death Cross | ma_cross | MA20 cắt MA50 (3 phiên gần nhất) |

### Bộ lọc Cơ bản
| Tiêu chí | Ký hiệu | Ví dụ |
|----------|---------|-------|
| P/E | pe | <15, 10-20 |
| P/B | pb | <1.5 |
| ROE | roe | >15% |
| Tăng trưởng EPS | eps_growth | >20% YoY |
| Debt/Equity | de_ratio | <1.0 |
| Dividend Yield | div_yield | >3% |

### Preset Screens phổ biến

#### "Cổ phiếu giá trị" (Value Screen)
```
P/E < 12 AND P/B < 1.5 AND ROE > 12% AND Debt/Equity < 0.8
AND avg_volume_20d > 500 triệu VND/ngày
```

#### "Tăng trưởng mạnh" (Growth Screen)
```
EPS_growth_YoY > 25% AND Revenue_growth_YoY > 20%
AND ROE > 18% AND avg_volume_20d > 1 tỷ VND/ngày
```

#### "Breakout Volume" (Momentum Screen)
```
volume_today > 2× avg_volume_20d AND price_change_today > 2%
AND price > MA20 AND RSI(14) giữa 40-70
```

#### "Cổ phiếu bị bán quá" (Oversold Bounce)
```
RSI(14) < 30 AND price > MA200 (uptrend dài hạn vẫn còn)
AND avg_volume_20d > 500 triệu VND AND price_change_5d < -8%
```

#### "FTSE Upgrade Play"
```
foreign_room_pct > 20% (còn nhiều room) AND market_cap > 5.000 tỷ VND
AND trong danh sách VN100 hoặc VN30
```

## Quy trình thực hiện

### Bước 1 — Parse tiêu chí từ user
Hiểu yêu cầu tự nhiên → convert sang filter parameters
Ví dụ: "tìm cổ phiếu ngân hàng P/B dưới 1.5, ROE trên 15%" →
```json
{"sector": "Banking", "pb": "<1.5", "roe": ">15"}
```

### Bước 2 — Gọi MCP tool
`screen_stocks(criteria)` → danh sách mã thỏa tiêu chí

### Bước 3 — Sắp xếp và lọc kết quả
- Sắp xếp theo tiêu chí quan trọng nhất
- Loại bỏ mã thanh khoản quá thấp (<200 triệu VND/ngày)
- Tối đa hiển thị 20 mã

### Bước 4 — Phân tích nhanh top 5
Với 5 mã đầu, cung cấp thêm context ngắn

## Định dạng Output

```
## 🔍 Kết quả Lọc Cổ phiếu

**Tiêu chí:** [mô tả bộ lọc]
**Tìm thấy:** [n] mã | **Hiển thị:** top [m]

| # | Mã | Giá | P/E | P/B | ROE | Volume/ngày | Điểm |
|---|----|----|-----|-----|-----|-------------|------|
| 1 | VNM | 75.000 | 18 | 4.2 | 28% | 35 tỷ | ⭐⭐⭐⭐ |
...

### Top 3 đáng chú ý nhất
**1. [SYMBOL]** — [lý do nổi bật 1-2 câu]
**2. [SYMBOL]** — [lý do nổi bật 1-2 câu]
**3. [SYMBOL]** — [lý do nổi bật 1-2 câu]

💡 Gợi ý: Dùng /analyze [SYMBOL] để phân tích chi tiết từng mã
```
```

---

### 2.5 `sector-compare.md`

```markdown
---
name: sector-compare
description: So sánh cổ phiếu cùng ngành
triggers:
  - "so sánh ngành"
  - "so sánh cùng ngành"
  - "peer comparison"
  - "compare sector"
---

# Skill: So sánh Cổ phiếu cùng Ngành

## Mục tiêu
Đặt một mã vào context ngành, xác định mã nào là leader/laggard.

## Quy trình

### Bước 1 — Xác định peer group
Từ symbol đầu vào → tìm ngành ICB → lấy tất cả mã cùng sub-sector
- Ngân hàng: VCB, BID, CTG, MBB, TCB, ACB, VPB, STB, HDB, TPB, MSB...
- Thép: HPG, HSG, NKG, TLH, VGS, SMC...
- BĐS: VHM, NLG, KDH, DXG, PDR, BCM, VRE...
- Dầu khí: GAS, PVD, PVS, BSR, OIL...
- Bán lẻ: MWG, FRT, PNJ, DGW...
- Hàng tiêu dùng: VNM, MSN, SAB, QNS...

### Bước 2 — Thu thập metrics cho tất cả peers
Với mỗi mã trong peer group, lấy:
- Giá hiện tại, % YTD
- P/E, P/B, EV/EBITDA
- ROE, ROA, Net Margin
- Tăng trưởng EPS TTM
- Market Cap
- Dividend Yield

### Bước 3 — Tính relative ranking
- Ranking từng tiêu chí trong ngành
- Composite score = trung bình weighted ranking

### Bước 4 — Phân tích khoảng cách định giá
- Mã nào đang discount/premium so với trung vị ngành?
- Phí trội có hợp lý không (chất lượng cao hơn, tăng trưởng nhanh hơn)?

## Định dạng Output

```
## 🏭 So sánh Ngành: [Tên ngành] — [Ngày]

**Cổ phiếu focus:** [SYMBOL]
**Số peers:** [n] mã

### Bảng so sánh tổng quan
| Mã | Giá | YTD | P/E | P/B | ROE | EPS growth | Mức độ |
|----|-----|-----|-----|-----|-----|------------|--------|
| **[SYMBOL]** | ... | ... | ... | ... | ... | ... | **Focus** |
| VCB | ... | ... | ... | ... | ... | ... | Leader |
| ... | | | | | | | |

**Trung vị ngành:** P/E=[x], P/B=[x], ROE=[x]%

### Định giá tương đối
- [SYMBOL] đang giao dịch ở **P/E premium/discount [x]%** so với trung vị ngành
- Justify được vì: [ROE cao hơn x%, tăng trưởng nhanh hơn x%...]
- Hoặc: Khó justify vì [...]

### Ranking [SYMBOL] trong ngành
- Định giá (rẻ → đắt): Hạng [x]/[n]
- Chất lượng (ROE, margin): Hạng [x]/[n]
- Tăng trưởng (EPS growth): Hạng [x]/[n]
- **Tổng hợp: Hạng [x]/[n]**

### Kết luận
[2-3 câu: [SYMBOL] là leader/laggard/fair trong ngành? Mã nào hấp dẫn hơn?]
```
```

---

### 2.6 `portfolio-review.md`

```markdown
---
name: portfolio-review
description: Đánh giá toàn diện danh mục đầu tư
triggers:
  - "danh mục"
  - "portfolio"
  - "đánh giá danh mục"
  - "rủi ro danh mục"
---

# Skill: Đánh giá Danh mục Đầu tư

## Mục tiêu
Phân tích rủi ro, hiệu suất, và đề xuất tối ưu hóa danh mục hiện tại.

## Quy trình

### Bước 1 — Thu thập dữ liệu danh mục
Gọi `get_portfolio()` → list positions:
```json
[
  {"symbol": "VNM", "qty": 1000, "avg_cost": 72000, "current_price": 75000},
  ...
]
```

### Bước 2 — Tính toán metrics danh mục

#### Hiệu suất
- P&L từng mã (VND và %)
- P&L tổng danh mục
- So sánh với VN-Index (alpha)
- Drawdown từ đỉnh

#### Phân bổ (Allocation)
- % theo từng mã (concentration risk)
- % theo ngành
- % theo sàn (HOSE vs HNX vs UPCOM)
- % theo vốn hóa (large/mid/small cap)

#### Rủi ro
- VaR 95% (1 ngày) — dùng historical simulation
- Beta danh mục so với VN-Index
- Correlation matrix các cặp mã
- Maximum Drawdown tiềm năng

#### T+2 Cash Flow
- Tiền khả dụng hiện tại
- Tiền sẽ về T+1, T+2
- Sức mua thực sự hôm nay

### Bước 3 — Xác định vấn đề
- Mã nào chiếm >20% danh mục? → Concentration risk
- Ngành nào chiếm >30%? → Sector concentration
- Correlation cao (>0.8) giữa các cặp → Not truly diversified
- Mã nào lỗ >15%? → Review stoploss
- Mã nào chưa tăng sau 3 tháng? → Opportunity cost

### Bước 4 — Đề xuất tái cơ cấu

## Định dạng Output

```
## 💼 Tổng quan Danh mục — [Ngày]

**Giá trị hiện tại:** [x] triệu VND
**Vốn đầu tư:** [x] triệu VND
**Lãi/Lỗ:** [+/-x] triệu VND ([+/-x]%)
**So với VN-Index (YTD):** [outperform/underperform x%]

### Bảng vị thế
| Mã | SL | Giá TB | Giá HT | P&L | % DM | Ngành |
|----|----|----|----|----|------|-------|
| VNM | 1.000 | 72.000 | 75.000 | +4,2% | 18% | FMCG |
...

### Phân bổ Ngành
[Biểu đồ text/bảng % theo ngành]

### Đánh giá Rủi ro
- **VaR (95%, 1 ngày):** -[x]% / -[x] triệu VND
- **Beta DM:** [x] (so VN-Index)
- **Max Drawdown tiềm năng:** -[x]%

### Cảnh báo ⚠️
[Các vấn đề cần xử lý: concentration, lỗ sâu, correlation cao]

### T+2 Cash Flow
- Tiền mặt khả dụng: [x] triệu VND
- Về T+1: [x] triệu VND
- Về T+2: [x] triệu VND
- Sức mua thực hôm nay: [x] triệu VND

### Gợi ý Tái cơ cấu
1. [Đề xuất cụ thể + lý do]
2. [Đề xuất cụ thể + lý do]
```
```

---

## 3. SUBAGENTS (`.claude/agents/`)

> Subagents là các agent chuyên biệt chạy độc lập với context riêng. Mỗi agent tập trung vào một nhiệm vụ dài hơi.

---

### 3.1 `market-watcher.md`

```markdown
---
name: market-watcher
description: Theo dõi thị trường realtime, cảnh báo biến động bất thường
model: claude-sonnet-4-5
tools:
  - mcp__vn-stock-mcp__get_market_overview
  - mcp__vn-stock-mcp__get_stock_price
  - mcp__vn-stock-mcp__get_news
---

# Agent: Market Watcher

## Mục đích
Theo dõi liên tục thị trường trong phiên giao dịch, phát hiện và cảnh báo sớm các biến động bất thường trước khi trader kịp nhận ra.

## Nhiệm vụ cốt lõi

### 1. Monitor Thị trường chung
Mỗi chu kỳ kiểm tra:
- VN-Index / HNX-Index / UPCOM so với tham chiếu
- Breadth (số mã tăng/giảm/đứng)
- Thanh khoản hiện tại vs. TB30 phiên cùng giờ
- Khối ngoại mua/bán ròng rolling

### 2. Phát hiện Bất thường
Alert ngay khi phát hiện:
- Mã tăng/giảm đột biến >5% trong 15 phút
- Volume spike >3× TB20 phiên
- VN-Index thay đổi >1% trong 30 phút
- Mã trong watchlist đạt giá mục tiêu / stoploss
- Nhiều mã cùng ngành cùng giảm mạnh (sector sell-off)

### 3. Theo dõi Price Band
- Cảnh báo mã sắp chạm trần/sàn (còn 1%)
- Alert khi mã chạm trần (circuit breaker potential)
- Theo dõi ATC queue (14:30-14:45)

## Cách chạy
```bash
# Khởi động market watcher trong phiên
python scripts/market_watcher.py --watchlist portfolio.json --interval 60
```

## Prompt Template khi gọi
```
Bạn là Market Watcher Agent, theo dõi TTCK Việt Nam.
Phiên giao dịch hiện tại: [ATO/Liên tục sáng/Nghỉ trưa/Liên tục chiều/ATC/Đóng cửa]
Thời gian: [HH:MM]

Dữ liệu vừa lấy:
[market_data_json]

Watchlist của trader:
[watchlist_json]

Nhiệm vụ:
1. Xác định các bất thường (nếu có)
2. Tạo alert cho trader nếu cần hành động
3. Tóm tắt diễn biến ngắn gọn (3-5 dòng)

Format alert:
🚨 [MỨC ĐỘ: CAO/TRUNG/THẤP] — [MÃ]: [MÔ TẢ NGẮN]
→ Đề xuất: [HÀNH ĐỘNG GỢI Ý]
```

## Output mẫu
```
🚨 CAO — HPG: Giảm 4.8% trong 20 phút, volume 2.8× TB
→ Đề xuất: Kiểm tra tin tức HPG, cân nhắc stoploss nếu chưa đặt

📊 Thị trường 10:30:
VN-Index: 1.782 (-0.12%) | Tăng: 156 | Giảm: 203 | Đứng: 41
Thanh khoản: 4.200 tỷ VND (38% target ngày)
Khối ngoại: Bán ròng 124 tỷ VND
```
```

---

### 3.2 `news-analyst.md`

```markdown
---
name: news-analyst
description: Đọc và phân tích tin tức tài chính, xác định tác động đến danh mục
model: claude-sonnet-4-5
tools:
  - mcp__vn-stock-mcp__get_news
  - mcp__vn-stock-mcp__get_stock_price
  - mcp__vn-stock-mcp__get_portfolio
  - WebSearch
  - WebFetch
---

# Agent: News Analyst

## Mục đích
Liên tục scan tin tức từ nhiều nguồn, phân tích tác động và tạo digest cá nhân hóa theo danh mục của trader.

## Nhiệm vụ

### 1. Nguồn tin cần theo dõi
Ưu tiên theo thứ tự:
1. **HOSE.vn / HNX.vn** — thông báo công bố thông tin chính thức
2. **CafeF.vn** — tin tức doanh nghiệp realtime
3. **VNExpress Kinh doanh** — macro, chính sách
4. **Vietstock.vn** — phân tích, khuyến nghị
5. **NDH.vn** — tin doanh nghiệp chuyên sâu
6. **Bloomberg / Reuters** (VN section) — góc nhìn quốc tế

### 2. Phân loại và ưu tiên tin

#### Ưu tiên tối cao (alert ngay)
- Kết quả kinh doanh quý/năm (beat/miss kỳ vọng)
- Lãnh đạo bị bắt/từ chức
- Cổ phiếu bị đình chỉ giao dịch
- M&A announcement
- Thay đổi chính sách lớn của NHNN/Bộ Tài chính

#### Ưu tiên cao (digest sáng)
- Kế hoạch kinh doanh năm mới
- Phát hành thêm cổ phiếu, trái phiếu
- Cổ tức, chia thưởng
- Kết quả đấu thầu dự án lớn
- Thay đổi cơ cấu cổ đông lớn

#### Ưu tiên trung bình (digest chiều)
- Nhận xét analyst, báo cáo phân tích
- Tin kinh tế vĩ mô VN
- Diễn biến thị trường quốc tế liên quan

### 3. Cá nhân hóa theo danh mục
- Ưu tiên tin về mã trong portfolio
- Tin về đối thủ, supplier, customer của mã trong portfolio
- Tin về ngành có exposure lớn

## Prompt Template
```
Bạn là News Analyst Agent chuyên về TTCK Việt Nam.

Tin tức vừa thu thập (24 giờ gần nhất):
[news_list_json]

Danh mục trader:
[portfolio_json]

Nhiệm vụ:
1. Tóm tắt 5 tin quan trọng nhất
2. Với mỗi tin: xác định mã bị ảnh hưởng + chiều hướng + mức độ
3. Highlight tin liên quan trực tiếp đến danh mục
4. Nhận định ngắn về sentiment thị trường hôm nay

Viết bằng tiếng Việt, súc tích, actionable.
```

## Lịch chạy
- **5:30 sáng:** Scan tin quốc tế qua đêm
- **8:00 sáng:** Digest buổi sáng trước phiên
- **11:30:** Digest giữa phiên
- **15:00:** Digest sau ATC
- **Real-time:** Alert khi có tin quan trọng (webhook/poll 5 phút)
```

---

### 3.3 `portfolio-manager.md`

```markdown
---
name: portfolio-manager
description: Quản lý danh mục, tính toán risk, gợi ý tái cơ cấu
model: claude-sonnet-4-5
tools:
  - mcp__vn-stock-mcp__get_portfolio
  - mcp__vn-stock-mcp__get_stock_price
  - mcp__vn-stock-mcp__get_stock_history
  - mcp__vn-stock-mcp__get_financial_report
---

# Agent: Portfolio Manager

## Mục đích
Quản lý và tối ưu hóa danh mục theo nguyên tắc quản lý rủi ro chuyên nghiệp.

## Nhiệm vụ thường xuyên

### 1. Daily P&L Tracking
Mỗi cuối phiên:
- Tính P&L ngày, tuần, tháng, YTD
- So sánh với VN-Index (tracking error)
- Cập nhật drawdown từ đỉnh

### 2. Risk Management
- **Position Sizing:** Khuyến nghị size cho trade mới
  ```
  Max risk per trade = 2% tổng danh mục
  Position size = Max risk ÷ (Entry - Stoploss)
  ```
- **Concentration Check:** Cảnh báo nếu 1 mã >20% hoặc 1 ngành >35%
- **Correlation Monitor:** Phát hiện danh mục thực ra không diversified
- **VaR Daily:** Ước tính thua lỗ tối đa 95% confidence

### 3. T+2 Cash Flow Management
Tracking:
- Cash hiện tại (sau đặt lệnh chờ khớp)
- Tiền về T+1: từ bán D-1
- Tiền về T+2: từ bán D-2
- Margin available (nếu có)
- Lệnh mua đang chờ khớp

### 4. Stoploss & Take-Profit Monitoring
Với mỗi vị thế:
- Stoploss hiện tại: [giá] / [%]
- Distance to stoploss: còn bao xa?
- Trailing stoploss khuyến nghị

### 5. Rebalancing Suggestions
Định kỳ đề xuất:
- Mã nào nên chốt lời (valuation stretched)
- Mã nào nên cắt lỗ (thesis broken)
- Mã nào nên tăng vị thế (conviction, giá hấp dẫn hơn)

## Nguyên tắc Quản lý Rủi ro áp dụng
1. **Kelly Criterion (fractional):** f = (bp - q) / b, dùng 1/4 Kelly
2. **Never >5% trong 1 mã** với danh mục <500 triệu VND
3. **Sector exposure:** Max 30% 1 ngành
4. **Cash buffer:** Luôn giữ 10-20% tiền mặt
5. **Correlation constraint:** Không quá 3 mã correlation >0.7 trong DM

## Prompt Template
```
Bạn là Portfolio Manager Agent.
Vai trò: quản lý rủi ro và tối ưu hóa danh mục theo nguyên tắc chuyên nghiệp.

Danh mục hiện tại:
[portfolio_json]

Giá thị trường hiện tại:
[prices_json]

Yêu cầu: [analyze_risk / suggest_rebalance / calculate_position_size / t2_cashflow]

Tham số risk tolerance: [conservative/moderate/aggressive]

Trả lời bằng tiếng Việt, số liệu cụ thể, actionable.
Nếu đề xuất giao dịch, luôn confirm với trader trước khi thực hiện.
```
```

---

### 3.4 `research-agent.md`

```markdown
---
name: research-agent
description: Nghiên cứu deep-dive một cổ phiếu hoặc ngành
model: claude-opus-4-5
tools:
  - mcp__vn-stock-mcp__get_stock_price
  - mcp__vn-stock-mcp__get_stock_history
  - mcp__vn-stock-mcp__get_financial_report
  - mcp__vn-stock-mcp__get_news
  - mcp__vn-stock-mcp__get_insider_trades
  - mcp__vn-stock-mcp__screen_stocks
  - WebSearch
  - WebFetch
---

# Agent: Research Agent

## Mục đích
Thực hiện nghiên cứu sâu (deep-dive research) cho một mã cổ phiếu hoặc ngành, tương đương báo cáo analyst chuyên nghiệp.

## Các loại research

### Type 1: Company Deep Dive
**Thời gian:** 10-15 phút
**Output:** Báo cáo ~1.500 từ

Cấu trúc báo cáo:
1. **Tóm tắt điều hành** (Executive Summary) — Buy/Hold/Sell + target price
2. **Mô hình kinh doanh** — doanh thu từ đâu, lợi thế cạnh tranh
3. **Phân tích tài chính** — 4-8 quý, trend, so ngành
4. **Định giá** — DCF đơn giản + relative valuation
5. **Catalyst** — điều gì sẽ đẩy giá lên trong 6-12 tháng?
6. **Rủi ro** — top 3-5 rủi ro với probability + impact
7. **Kết luận** + mức giá mục tiêu 12 tháng

### Type 2: Sector Overview
**Thời gian:** 15-20 phút
**Output:** Báo cáo ~2.000 từ

Cấu trúc:
1. Tổng quan ngành (quy mô, tăng trưởng, cấu trúc)
2. Động lực ngành (tailwind/headwind)
3. Landscape cạnh tranh + thị phần
4. Các mã đáng chú ý trong ngành (top 5)
5. Timing — bây giờ có phải thời điểm tốt để đầu tư ngành?

### Type 3: Event Analysis
**Thời gian:** 5-10 phút
**Output:** Phân tích tác động một sự kiện cụ thể

Ví dụ:
- "Phân tích tác động của việc Fed cắt lãi suất đến ngân hàng VN"
- "FTSE upgrade tác động đến mã nào nhiều nhất?"
- "Kết quả kinh doanh Q4/2025 của VNM có ý nghĩa gì?"

## Prompt Template
```
Bạn là Senior Research Analyst chuyên về TTCK Việt Nam.
Kinh nghiệm: 10 năm, CFA Level 3.

Yêu cầu research: [company_deepdive / sector_overview / event_analysis]
Subject: [SYMBOL hoặc sector hoặc event]

Dữ liệu có sẵn:
[all_available_data]

Hướng dẫn:
- Viết bằng tiếng Việt, chuyên nghiệp nhưng dễ hiểu
- Số liệu cụ thể, trích dẫn nguồn
- Nêu rõ assumptions trong định giá
- Phân biệt fact vs. opinion
- Kết luận actionable: nên mua/giữ/bán ở giá nào?
- Nêu rõ rủi ro để trader tự phán xét

Quan trọng: Đây là thông tin tham khảo, không phải khuyến nghị đầu tư.
```
```

---

## 4. HOOKS (`.claude/settings.json`)

> Claude Code hooks là event-driven. Với các trigger theo giờ, dùng cron jobs gọi script → script notify Claude.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__vn-stock-mcp__.*",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/log_mcp_call.py --tool '$TOOL_NAME' --timestamp $(date +%s)",
            "timeout": 5000
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/notify.py --message '$NOTIFICATION_MESSAGE'",
            "timeout": 5000
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/session_end_hook.py",
            "timeout": 10000
          }
        ]
      }
    ]
  }
}
```

### Hooks theo giờ — Cron Jobs

**File: `scripts/cron_setup.sh`** — chạy một lần để setup:
```bash
#!/bin/bash
# Setup cron jobs cho VN Stock Trader

# 8:30 sáng thứ 2-6: Morning brief
(crontab -l 2>/dev/null; echo "30 8 * * 1-5 cd /path/to/vn-stock-trader && python scripts/morning_brief.py >> logs/morning.log 2>&1") | crontab -

# 14:50 thứ 2-6: Session summary sau ATC
(crontab -l 2>/dev/null; echo "50 14 * * 1-5 cd /path/to/vn-stock-trader && python scripts/session_summary.py >> logs/session.log 2>&1") | crontab -

# Mỗi 5 phút, thứ 2-6, 9:00-15:00: Portfolio monitor
(crontab -l 2>/dev/null; echo "*/5 9-14 * * 1-5 cd /path/to/vn-stock-trader && python scripts/portfolio_monitor.py >> logs/monitor.log 2>&1") | crontab -

# 8:00 sáng thứ 2-6: Fetch tin tức qua đêm
(crontab -l 2>/dev/null; echo "0 8 * * 1-5 cd /path/to/vn-stock-trader && python scripts/news_digest.py >> logs/news.log 2>&1") | crontab -

echo "✅ Cron jobs configured"
```

### `scripts/morning_brief.py` — Tóm tắt buổi sáng

```python
"""
Chạy lúc 8:30 sáng thứ 2-6
Tự động pull data và tạo morning brief
"""
import subprocess
import json
from datetime import date

def run_morning_brief():
    brief = {
        "date": str(date.today()),
        "type": "morning_brief",
        "sections": [
            "overnight_world_markets",    # Asia/US close
            "vn_market_preview",          # Dự báo phiên hôm nay
            "portfolio_positions",         # Danh mục qua đêm
            "news_overnight",             # Tin tức qua đêm
            "key_events_today",           # Sự kiện quan trọng hôm nay
            "watchlist_alerts",           # Cảnh báo mã đang theo dõi
        ]
    }

    # Trigger Claude Code với morning brief prompt
    prompt = f"""
    Chạy morning brief cho ngày {date.today()}.

    1. Gọi get_market_overview() để xem tổng quan
    2. Gọi get_news() để lấy tin tức qua đêm
    3. Gọi get_portfolio() để xem danh mục
    4. Phân tích và tạo morning brief theo skill portfolio-review
    5. Highlight 3 điều quan trọng nhất trader cần biết hôm nay

    Format gọn, có thể đọc trong 2 phút.
    """

    result = subprocess.run(
        ["claude", "-p", prompt, "--model", "claude-sonnet-4-5"],
        capture_output=True, text=True
    )

    # Lưu kết quả và notify
    with open(f"logs/morning_brief_{date.today()}.md", "w") as f:
        f.write(result.stdout)

    # Desktop notification
    subprocess.run(["osascript", "-e",
        f'display notification "Morning brief ready" with title "VN Stock Trader"'])

if __name__ == "__main__":
    run_morning_brief()
```

### `scripts/portfolio_monitor.py` — Monitor danh mục

```python
"""
Chạy mỗi 5 phút trong phiên giao dịch
Kiểm tra biến động bất thường, cảnh báo nếu cần
"""
import json
import subprocess
from pathlib import Path

ALERT_THRESHOLDS = {
    "position_loss_pct": -7.0,      # Cảnh báo khi 1 mã lỗ > 7%
    "portfolio_loss_pct": -3.0,     # Cảnh báo khi DM lỗ > 3%
    "volume_spike_multiplier": 2.5, # Cảnh báo volume > 2.5× TB
    "price_change_pct": 5.0,        # Cảnh báo thay đổi > 5% trong 30 phút
}

def check_alerts():
    # Gọi MCP để lấy dữ liệu hiện tại
    # So sánh với ngưỡng
    # Gửi alert nếu vượt ngưỡng
    ...

if __name__ == "__main__":
    check_alerts()
```

---

## 5. COMMANDS (`.claude/commands/`)

> Slash commands cho phép trader gọi nhanh các workflow thường dùng.

---

### 5.1 `analyze.md` — `/analyze <mã>`

```markdown
---
description: Phân tích nhanh một mã cổ phiếu (TA + FA + News)
usage: /analyze <SYMBOL> [--mode ta|fa|full]
examples:
  - /analyze VNM
  - /analyze HPG --mode ta
  - /analyze ACB --mode full
---

Phân tích cổ phiếu $ARGUMENTS.

**Quy trình:**
1. Parse symbol từ arguments (VD: "VNM" hoặc "vnm" → normalize uppercase)
2. Xác định mode: mặc định là "full" (cả TA lẫn FA)
3. Thu thập dữ liệu:
   - Gọi `get_stock_price($SYMBOL)`
   - Gọi `get_stock_history($SYMBOL, period="6m")`
   - Gọi `get_financial_report($SYMBOL, period="4q")`
   - Gọi `get_news($SYMBOL)`
4. Chạy skill `technical-analysis` nếu mode là "ta" hoặc "full"
5. Chạy skill `fundamental-analysis` nếu mode là "fa" hoặc "full"
6. Chạy skill `news-impact` với tin tức của symbol
7. Tổng hợp kết luận cuối: 🟢 MUA / 🟡 CHỜ / 🔴 TRÁNH

**Lưu ý:**
- Nếu mã không tìm thấy → gợi ý các mã tương tự
- Nếu thanh khoản <100 triệu VND/ngày → cảnh báo kẹt hàng
- Cuối output: gợi ý `/compare $SYMBOL <peer>` để so sánh ngành
```

---

### 5.2 `screen.md` — `/screen <tiêu chí>`

```markdown
---
description: Lọc cổ phiếu theo tiêu chí
usage: /screen <tiêu chí tự nhiên hoặc preset>
examples:
  - /screen ngân hàng P/B dưới 1.5 ROE trên 15%
  - /screen --preset value
  - /screen --preset breakout
  - /screen vốn hóa lớn tăng trưởng mạnh thanh khoản cao
---

Lọc cổ phiếu theo yêu cầu: $ARGUMENTS

**Quy trình:**
1. Parse tiêu chí từ arguments:
   - Nếu có `--preset <name>`: dùng preset screen đã định nghĩa trong skill `stock-screener`
   - Nếu là tiếng tự nhiên: convert sang filter parameters
2. Gọi `screen_stocks(criteria_json)`
3. Chạy skill `stock-screener` để format và phân tích kết quả
4. Hiển thị top 20 kết quả có thể

**Preset available:**
- `--preset value` — Cổ phiếu giá trị (P/E thấp, ROE cao)
- `--preset growth` — Tăng trưởng mạnh
- `--preset breakout` — Breakout volume
- `--preset oversold` — Quá bán, cơ hội bounce
- `--preset ftse` — Cổ phiếu hưởng lợi FTSE upgrade

**Cuối output:** Gợi ý `/analyze <mã>` cho top 3 kết quả
```

---

### 5.3 `portfolio.md` — `/portfolio`

```markdown
---
description: Xem tổng quan danh mục đầu tư
usage: /portfolio [--detail | --risk | --cashflow]
examples:
  - /portfolio
  - /portfolio --detail
  - /portfolio --risk
  - /portfolio --cashflow
---

Hiển thị tổng quan danh mục: $ARGUMENTS

**Quy trình:**
1. Gọi `get_portfolio()` → danh sách vị thế
2. Gọi `get_stock_price()` cho tất cả symbol trong portfolio
3. Chạy skill `portfolio-review`:
   - Default: bảng P&L + phân bổ ngành
   - `--detail`: thêm metrics kỹ thuật từng mã
   - `--risk`: tập trung VaR, beta, concentration risk
   - `--cashflow`: tập trung T+2 flow, margin available
4. Highlight cảnh báo nếu có (lỗ sâu, concentration, v.v.)

**Cuối output:**
- Gợi ý `/analyze <mã_lỗ_nhất>` để review thesis
- Gợi ý hành động nếu có vấn đề rõ ràng
```

---

### 5.4 `news.md` — `/news`

```markdown
---
description: Tin tức mới nhất ảnh hưởng danh mục
usage: /news [--symbol <MÃ> | --macro | --all]
examples:
  - /news
  - /news --symbol VNM
  - /news --macro
  - /news --all
---

Lấy và phân tích tin tức: $ARGUMENTS

**Quy trình:**
1. Xác định scope:
   - Default: tin liên quan danh mục (gọi `get_portfolio()` trước)
   - `--symbol <MÃ>`: chỉ tin về 1 mã cụ thể
   - `--macro`: chỉ tin vĩ mô (không filter theo danh mục)
   - `--all`: tất cả tin quan trọng hôm nay
2. Gọi `get_news(symbol?)` với scope tương ứng
3. Chạy skill `news-impact` để phân tích
4. Sắp xếp theo: Mức độ quan trọng → Liên quan danh mục → Thời gian

**Định dạng:** Mỗi tin: tiêu đề + tóm tắt 1 câu + mã bị ảnh hưởng + chiều hướng
**Giới hạn:** Top 10 tin quan trọng nhất; có thể gọi lại với `--all` để xem hết
```

---

### 5.5 `compare.md` — `/compare <mã1> <mã2>`

```markdown
---
description: So sánh chi tiết 2 cổ phiếu
usage: /compare <SYMBOL1> <SYMBOL2>
examples:
  - /compare VCB BID
  - /compare HPG HSG
  - /compare VNM MSN
---

So sánh 2 cổ phiếu: $ARGUMENTS

**Quy trình:**
1. Parse 2 symbols từ arguments
2. Thu thập dữ liệu cho cả 2 mã:
   - `get_stock_price()` × 2
   - `get_stock_history(period="1y")` × 2
   - `get_financial_report(period="4q")` × 2
3. Chạy skill `sector-compare` với focus cả 2 mã
4. So sánh trực tiếp:
   - Bảng metrics song song (giá, P/E, P/B, ROE, growth, momentum)
   - Performance chart text (% return 1M, 3M, 6M, 1Y)
   - Ai đang đắt/rẻ hơn một cách tương đối?
5. Kết luận: Nên chọn mã nào? Trong trường hợp nào?

**Format:** Bảng so sánh 2 cột rõ ràng, kết luận 3-5 câu cuối
```

---

### 5.6 `report.md` — `/report`

```markdown
---
description: Báo cáo tổng kết cuối ngày
usage: /report [--date YYYY-MM-DD]
examples:
  - /report
  - /report --date 2026-03-28
---

Tạo báo cáo tổng kết phiên giao dịch: $ARGUMENTS

**Quy trình:**
1. Xác định ngày (default: hôm nay)
2. Thu thập:
   - `get_market_overview()` → diễn biến thị trường
   - `get_portfolio()` → P&L trong ngày
   - `get_news()` → tin tức trong ngày
3. Tổng hợp báo cáo:

### Cấu trúc báo cáo cuối ngày:
```
## 📈 Báo cáo Phiên Giao dịch — [Ngày]

### Thị trường
- VN-Index: [điểm] ([+/-]%) | Volume: [x] tỷ VND
- Top tăng: [mã1 +x%], [mã2 +x%], [mã3 +x%]
- Top giảm: [mã1 -x%], [mã2 -x%], [mã3 -x%]
- Khối ngoại: Mua [x] tỷ / Bán [x] tỷ = Ròng [+/-x] tỷ

### Danh mục hôm nay
- P&L ngày: [+/-x] triệu VND ([+/-x]%)
- Hiệu suất vs VN-Index: [Outperform/Underperform x%]
- Mã tốt nhất: [SYMBOL +x%]
- Mã tệ nhất: [SYMBOL -x%]

### Tin tức quan trọng
[Top 3 tin]

### Điểm cần lưu ý cho phiên mai
[3-5 điểm actionable]

### Kế hoạch phiên mai
[Gợi ý dựa trên phân tích]
```
```

---

### 5.7 `alert.md` — `/alert <mã> <điều kiện>`

```markdown
---
description: Đặt cảnh báo giá hoặc điều kiện cho cổ phiếu
usage: /alert <SYMBOL> <điều kiện>
examples:
  - /alert VNM giá > 80000
  - /alert HPG giá < 25000
  - /alert ACB volume > 2x tb20
  - /alert VIC RSI < 30
  - /alert list
  - /alert clear VNM
---

Quản lý cảnh báo: $ARGUMENTS

**Quy trình:**
1. Parse command:
   - `list`: hiển thị tất cả alerts đang active
   - `clear <SYMBOL>`: xóa alerts của mã đó
   - `<SYMBOL> <điều kiện>`: tạo alert mới
2. Lưu alert vào `alerts.json`
3. Confirm với trader: "✅ Alert đặt: [SYMBOL] sẽ thông báo khi [điều kiện]"

**Các điều kiện hỗ trợ:**
- `giá > X` hoặc `giá < X` — price alert
- `volume > Nx tb20` — volume spike alert
- `RSI > X` hoặc `RSI < X` — RSI alert
- `ma20 cắt ma50` — golden/death cross alert
- `biên độ > X%` — intraday move alert

**Cơ chế kiểm tra:**
Script `portfolio_monitor.py` kiểm tra alerts.json mỗi 5 phút trong phiên
Khi điều kiện thỏa → notify + gọi `/analyze <SYMBOL>` tự động
```

---

## 6. MCP SERVER (`mcp-server/`)

### 6.1 Cấu hình Server

**`mcp-server/pyproject.toml`:**
```toml
[project]
name = "vn-stock-mcp"
version = "1.0.0"
description = "MCP Server cho dữ liệu chứng khoán Việt Nam"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "vnstock>=3.4.0",
    "pandas>=2.0.0",
    "httpx>=0.27.0",
    "ta-lib>=0.4.0",           # TA indicators tính local
    "ta>=0.11.0",               # Fallback nếu ta-lib khó cài
    "beautifulsoup4>=4.12.0",  # Vietstock crawl
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "ruff>=0.4.0"]

[tool.ruff]
line-length = 88
target-version = "py311"
```

**`mcp-server/.env.example`:**
```bash
# vnstock — Community tier (miễn phí, đăng ký tại vnstock.site)
# Không cần: không điền vẫn hoạt động ở Guest tier (20 req/phút)
VNSTOCK_TOKEN=your_community_token

# Vietstock — crawl tin tức, BCTC, chỉ số tài chính (không cần tài khoản)
# Không có config thêm — crawl public endpoints

# Portfolio file (quản lý local, không kết nối broker)
PORTFOLIO_FILE=./data/portfolio.json

# Alert file
ALERTS_FILE=./data/alerts.json
```

---

### 6.2 Entry Point — `mcp-server/server.py`

```python
"""
VN Stock MCP Server
Cung cấp tools cho Claude để truy cập dữ liệu TTCK Việt Nam
"""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from tools.market import get_market_overview, get_stock_price
from tools.history import get_stock_history
from tools.financials import get_financial_report
from tools.news import get_news
from tools.screener import screen_stocks
from tools.portfolio import get_portfolio
from tools.insider import get_insider_trades

app = Server("vn-stock-mcp")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_market_overview",
            description="Lấy tổng quan thị trường: VN-Index, HNX-Index, top movers, thanh khoản, khối ngoại",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cần lấy (YYYY-MM-DD). Mặc định: hôm nay",
                        "default": "today"
                    }
                }
            }
        ),
        types.Tool(
            name="get_stock_price",
            description="Lấy giá (delay ~15 phút qua vnstock/TCBS) và thông tin giao dịch của một cổ phiếu",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Mã cổ phiếu (VD: VNM, HPG, VCB)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_stock_history",
            description="Lấy lịch sử giá OHLCV của cổ phiếu",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Mã cổ phiếu"},
                    "period": {
                        "type": "string",
                        "description": "Khoảng thời gian: 1m, 3m, 6m, 1y, 3y, 5y",
                        "default": "1y"
                    },
                    "interval": {
                        "type": "string",
                        "description": "Khung thời gian: 1D, 1W, 1M",
                        "default": "1D"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_financial_report",
            description="Lấy báo cáo tài chính: kết quả kinh doanh, bảng cân đối, lưu chuyển tiền tệ",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "period": {
                        "type": "string",
                        "description": "Số kỳ cần lấy: 4q (4 quý), 8q (8 quý), annual",
                        "default": "4q"
                    },
                    "report_type": {
                        "type": "string",
                        "enum": ["income_statement", "balance_sheet", "cash_flow", "ratios", "all"],
                        "default": "all"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_market_overview",
            description="Tổng quan thị trường realtime",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_news",
            description="Lấy tin tức tài chính. Nếu có symbol → tin về mã đó. Không có → tin thị trường chung",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Mã cổ phiếu (tùy chọn)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số tin cần lấy",
                        "default": 20
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Số ngày nhìn lại",
                        "default": 7
                    }
                }
            }
        ),
        types.Tool(
            name="screen_stocks",
            description="Lọc cổ phiếu theo tiêu chí định lượng",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria": {
                        "type": "object",
                        "description": "Bộ tiêu chí lọc",
                        "properties": {
                            "exchange": {"type": "string", "enum": ["HOSE", "HNX", "UPCOM", "all"]},
                            "sector": {"type": "string"},
                            "min_market_cap": {"type": "number", "description": "Tỷ VND"},
                            "max_market_cap": {"type": "number"},
                            "min_pe": {"type": "number"},
                            "max_pe": {"type": "number"},
                            "min_pb": {"type": "number"},
                            "max_pb": {"type": "number"},
                            "min_roe": {"type": "number", "description": "Phần trăm (VD: 15 = 15%)"},
                            "min_avg_volume_value": {"type": "number", "description": "Tỷ VND/ngày"},
                            "min_price": {"type": "number"},
                            "max_price": {"type": "number"},
                            "min_eps_growth": {"type": "number"},
                            "max_debt_equity": {"type": "number"},
                            "min_rsi": {"type": "number"},
                            "max_rsi": {"type": "number"},
                            "volume_spike": {"type": "number", "description": "Bội số so TB20 (VD: 2 = gấp 2×)"},
                            "price_above_ma20": {"type": "boolean"},
                            "price_above_ma50": {"type": "boolean"},
                            "min_dividend_yield": {"type": "number"}
                        }
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sắp xếp theo tiêu chí (pe, roe, market_cap, volume)",
                        "default": "market_cap"
                    },
                    "limit": {"type": "integer", "default": 50}
                },
                "required": ["criteria"]
            }
        ),
        types.Tool(
            name="get_portfolio",
            description="Lấy danh mục đầu tư hiện tại từ file portfolio.json (quản lý local, không kết nối broker)",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_insider_trades",
            description="Lấy giao dịch nội bộ và dòng tiền tổ chức/quỹ của một mã",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "days_back": {"type": "integer", "default": 90}
                },
                "required": ["symbol"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handlers = {
        "get_market_overview": get_market_overview,
        "get_stock_price": get_stock_price,
        "get_stock_history": get_stock_history,
        "get_financial_report": get_financial_report,
        "get_news": get_news,
        "screen_stocks": screen_stocks,
        "get_portfolio": get_portfolio,
        "get_insider_trades": get_insider_trades,
    }

    handler = handlers.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")

    result = await handler(**arguments)
    return [types.TextContent(type="text", text=str(result))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 6.3 Implementation Tool Chính — `tools/market.py`

```python
"""
Tool: get_market_overview, get_stock_price
Data source: vnstock/TCBS (delay ~15 phút, miễn phí, không cần tài khoản broker)
"""
import json
from datetime import date
from typing import Optional
from vnstock import Vnstock, Market

async def get_market_overview(date_str: str = "today") -> dict:
    """
    Output:
    {
        "timestamp": "2026-03-29T10:30:00",
        "indices": {
            "VN-Index": {"value": 1784.5, "change": -2.3, "change_pct": -0.13},
            "HNX-Index": {"value": 248.7, "change": 0.5, "change_pct": 0.20},
            "UPCOM-Index": {"value": 95.2, "change": -0.1, "change_pct": -0.10}
        },
        "breadth": {
            "advancing": 156, "declining": 203, "unchanged": 41,
            "ceiling_hits": 12, "floor_hits": 8
        },
        "liquidity": {
            "total_value_bn_vnd": 18500,
            "hose_value_bn_vnd": 15200,
            "hnx_value_bn_vnd": 1800,
            "upcom_value_bn_vnd": 1500
        },
        "foreign_flow": {
            "buy_value_bn_vnd": 450,
            "sell_value_bn_vnd": 620,
            "net_bn_vnd": -170
        },
        "top_movers": {
            "top_gainers": [{"symbol": "ABC", "change_pct": 6.8}, ...],
            "top_losers": [{"symbol": "XYZ", "change_pct": -6.5}, ...],
            "top_volume": [{"symbol": "VNM", "volume": 5200000}, ...]
        }
    }
    """
    stock = Vnstock().stock(symbol="VNINDEX", source="VCI")

    # VN-Index
    vnindex = stock.quote.history(
        start=str(date.today()), end=str(date.today()), interval="1D"
    )

    # Breadth data
    market = Market(source="VCI")
    # ... fetch breadth, foreign flow, top movers

    return {
        "indices": {...},
        "breadth": {...},
        "liquidity": {...},
        "foreign_flow": {...},
        "top_movers": {...}
    }

async def get_stock_price(symbol: str) -> dict:
    """
    Output:
    {
        "symbol": "VNM",
        "exchange": "HOSE",
        "price": {
            "current": 75000,
            "reference": 74500,
            "ceiling": 79700,  # +7%
            "floor": 69300,    # -7%
            "open": 74800,
            "high": 75500,
            "low": 74200,
            "change": 500,
            "change_pct": 0.67
        },
        "volume": {
            "today": 2850000,
            "avg_20d": 2100000,
            "vs_avg_pct": 35.7
        },
        "bid_ask": {
            "best_bid": 74900,
            "best_ask": 75000,
            "bid_volume": 150000,
            "ask_volume": 200000
        },
        "foreign": {
            "room_remaining_pct": 12.5,
            "foreign_bought_today": 150000,
            "foreign_sold_today": 230000
        },
        "session": "continuous_afternoon"  # ato/morning/lunch/afternoon/atc/closed
    }
    """
    stock = Vnstock().stock(symbol=symbol.upper(), source="VCI")

    # Giá realtime
    price_board = stock.quote.price_board()

    # Foreign room
    # ...

    return {...}
```

---

### 6.4 `tools/screener.py`

```python
"""
Tool: screen_stocks
Lọc cổ phiếu theo tiêu chí từ ~1.600 mã VN
Data source: vnstock/TCBS (giá, FA ratios), ta-lib (TA indicators tính local)
"""
import pandas as pd
from vnstock import Vnstock

async def screen_stocks(criteria: dict, sort_by: str = "market_cap", limit: int = 50) -> dict:
    """
    Lấy toàn bộ danh sách cổ phiếu → filter → return kết quả

    Chiến lược:
    1. Fetch listing với basic metrics từ vnstock
    2. Nếu cần TA (RSI, MA): lấy history cho filtered subset
    3. Nếu cần FA (P/E, ROE): lấy từ financial ratios endpoint
    """
    stock = Vnstock()

    # Bước 1: Lấy danh sách niêm yết + basic metrics
    listing = stock.stock(symbol="VNM", source="VCI").listing.symbols_by_exchange()

    # Bước 2: Lấy financial ratios nếu cần FA filter
    if any(k in criteria for k in ["min_pe", "max_pe", "min_pb", "max_pb", "min_roe"]):
        ratios = _fetch_all_ratios()  # Batch fetch, cache 1h

    # Bước 3: Apply filters
    df = pd.DataFrame(listing)
    df = _apply_filters(df, criteria)

    # Bước 4: Tính TA nếu cần (chỉ cho subset đã filter)
    if "min_rsi" in criteria or "max_rsi" in criteria or "volume_spike" in criteria:
        for symbol in df["symbol"].head(100):  # Giới hạn để tránh rate limit
            df = _add_ta_metrics(df, symbol)

    # Bước 5: Sort và return
    df = df.sort_values(sort_by, ascending=False).head(limit)

    return {
        "total_found": len(df),
        "criteria": criteria,
        "results": df.to_dict(orient="records")
    }

def _apply_filters(df: pd.DataFrame, criteria: dict) -> pd.DataFrame:
    if "exchange" in criteria and criteria["exchange"] != "all":
        df = df[df["exchange"] == criteria["exchange"]]

    if "min_pe" in criteria:
        df = df[df["pe"] >= criteria["min_pe"]]
    if "max_pe" in criteria:
        df = df[df["pe"] <= criteria["max_pe"]]

    if "min_roe" in criteria:
        df = df[df["roe"] >= criteria["min_roe"] / 100]

    if "min_avg_volume_value" in criteria:
        # Thanh khoản tối thiểu (tỷ VND/ngày)
        df = df[df["avg_volume_20d_value"] >= criteria["min_avg_volume_value"] * 1e9]

    # ... các filter khác
    return df
```

---

### 6.5 `tools/portfolio.py`

```python
"""
Tool: get_portfolio
Quản lý danh mục local (portfolio.json) — không kết nối broker, không đặt lệnh tự động.
Trader tự nhập vị thế vào portfolio.json sau khi khớp lệnh thủ công trên app broker.
"""
import json
import os
from pathlib import Path
from datetime import date

PORTFOLIO_FILE = os.getenv("PORTFOLIO_FILE", "./data/portfolio.json")

async def get_portfolio() -> dict:
    """
    Đọc danh mục từ file portfolio.json
    Tính toán P&L dựa trên giá hiện tại

    Portfolio format (portfolio.json):
    {
        "account_id": "SSI_XXXXXX",
        "positions": [
            {
                "symbol": "VNM",
                "quantity": 1000,
                "avg_cost": 72000,
                "purchase_date": "2025-12-15"
            }
        ],
        "cash": 150000000,
        "t1_cash": 50000000,
        "t2_cash": 0
    }
    """
    with open(PORTFOLIO_FILE) as f:
        portfolio = json.load(f)

    # Fetch giá hiện tại cho tất cả mã
    from tools.market import get_stock_price

    for pos in portfolio["positions"]:
        price_data = await get_stock_price(pos["symbol"])
        current_price = price_data["price"]["current"]

        pos["current_price"] = current_price
        pos["market_value"] = current_price * pos["quantity"]
        pos["cost_value"] = pos["avg_cost"] * pos["quantity"]
        pos["unrealized_pnl"] = pos["market_value"] - pos["cost_value"]
        pos["unrealized_pnl_pct"] = (pos["unrealized_pnl"] / pos["cost_value"]) * 100

    # Tính tổng
    total_market_value = sum(p["market_value"] for p in portfolio["positions"])
    total_cost = sum(p["cost_value"] for p in portfolio["positions"])

    portfolio["summary"] = {
        "total_market_value": total_market_value,
        "total_cost": total_cost,
        "total_pnl": total_market_value - total_cost,
        "total_pnl_pct": ((total_market_value - total_cost) / total_cost) * 100,
        "cash_available": portfolio["cash"],
        "total_assets": total_market_value + portfolio["cash"] +
                        portfolio.get("t1_cash", 0) + portfolio.get("t2_cash", 0)
    }

    return portfolio

```

---

## 7. CẤU HÌNH MCP TRONG CLAUDE CODE

**Thêm vào `~/.claude/settings.json` hoặc `.claude/settings.json` của project:**

```json
{
  "mcpServers": {
    "vn-stock-mcp": {
      "command": "python",
      "args": ["/path/to/vn-stock-trader/mcp-server/server.py"],
      "env": {
        "VNSTOCK_TOKEN": "${VNSTOCK_TOKEN}",
        "PORTFOLIO_FILE": "/path/to/vn-stock-trader/data/portfolio.json"
      }
    }
  }
}
```

> **Lưu ý:** Không cần SSI credentials — hệ thống chỉ dùng vnstock (miễn phí) và Vietstock crawl. `VNSTOCK_TOKEN` cũng tùy chọn (Guest tier hoạt động không cần token).

---

## 8. WORKFLOW MẪU

### Workflow 1: Buổi sáng trước phiên (8:30 – 9:00)

```
8:30 → Cron kích hoạt morning_brief.py
         ↓
     Claude gọi: get_market_overview() + get_news() + get_portfolio()
         ↓
     Chạy skill: news-impact + portfolio-review
         ↓
     Output: Morning Brief 2 phút
       • Thị trường thế giới qua đêm
       • Top 3 tin ảnh hưởng danh mục hôm nay
       • Danh mục: P&L hiện tại, cảnh báo nếu có
       • Kế hoạch: mã nào cần theo dõi, ở đâu cần hành động
         ↓
     Trader đọc brief → quyết định trong 8:45-9:00

Lệnh trader có thể gõ:
  /news --macro          → Xem thêm tin vĩ mô
  /analyze VNM           → Deep-dive mã đang quan tâm
  /portfolio --cashflow  → Kiểm tra sức mua hôm nay
```

---

### Workflow 2: Phân tích mã mới

```
Trader: /analyze HPG

Claude thực hiện:
  1. get_stock_price("HPG")
     → Giá: 27.500, +1.2%, Volume: 15M cp (1.8× TB)

  2. get_stock_history("HPG", period="1y")
     → OHLCV 250 phiên

  3. Skill technical-analysis:
     → MA20=26.800, MA50=25.500, MA200=22.100 → Uptrend mạnh
     → RSI(14)=58 → Bình thường, chưa quá mua
     → MACD: Positive, histogram tăng
     → Volume: Xác nhận đà tăng
     → Kháng cự: 28.500 (đỉnh cũ), 30.000
     → Hỗ trợ: 26.500 (MA20), 25.000 (đỉnh cũ)
     → Tín hiệu: 🟢 MUA

  4. get_financial_report("HPG", period="4q")
     → Doanh thu Q4/2025: +18% YoY, LN ròng +35% YoY

  5. Skill fundamental-analysis:
     → P/E: 12.5 (ngành: 14.2) → Rẻ hơn ngành 12%
     → ROE: 18.5% → Trên TB ngành (15.8%)
     → Tín hiệu: ✅ CÓ THỂ MUA

  6. get_news("HPG")
     → Tin: Giá HRC tăng Q1/2026, hưởng lợi cho HPG

  7. Tổng hợp:
     📊 HPG: 🟢 MUA
     - TA: Uptrend rõ, volume xác nhận, RSI an toàn
     - FA: Định giá hấp dẫn, tăng trưởng LN mạnh
     - News: Tailwind từ giá HRC
     - Vào: 27.000-27.500 | SL: 25.800 (-5.1%) | T1: 30.000 (+9%)
     - R:R = 1:1.8

Trader: /compare HPG HSG
  → Claude so sánh: HPG vs HSG cùng ngành thép
  → Kết luận: HPG tốt hơn về margin và tăng trưởng; HSG rẻ hơn về P/B
```

---

### Workflow 3: Theo dõi danh mục trong phiên

```
9:00 → Phiên mở cửa (ATO)
     portfolio_monitor.py chạy mỗi 5 phút
         ↓
     Kiểm tra alerts.json
     Gọi get_stock_price() cho tất cả mã trong DM
         ↓
     So sánh với ngưỡng:
       • HPG giảm -3.5% → Chưa đến SL, chưa alert
       • VNM tăng +4.2% → Gần target, alert trader
       • VIC volume spike 3.5× TB → Alert bất thường
         ↓
     10:15: Alert đến trader:
       📈 VNM +4.2% — Gần target 75.000 VND
       → Gợi ý: /analyze VNM để quyết định chốt hay giữ

       🔔 VIC: Volume 3.5× bất thường lúc 10:05
       → Gợi ý: /news --symbol VIC để kiểm tra có tin gì

Trader: /analyze VNM --mode ta
  → Claude xem TA nhanh
  → "VNM đang test kháng cự 75.500. Nếu break qua với volume cao → tiếp tục tăng.
     Nếu không break → có thể điều chỉnh về 73.000."
  → Trader quyết định: giữ thêm

14:30 → ATC bắt đầu
portfolio_monitor.py: alert trader về mã nào đang chạy ATC bất thường

14:50 → session_summary.py tự động chạy
  → Tổng kết phiên, gửi notification
  → Trader gõ /report để xem chi tiết
```

---

### Workflow 4: Cuối ngày tổng kết & chuẩn bị phiên mai

```
15:00 → Trader gõ /report
         ↓
     Claude gọi: get_market_overview() + get_portfolio() + get_news()
         ↓
     Output báo cáo cuối ngày:
       📈 VN-Index: 1.786 (+0.11%) — Sideways, thanh khoản thấp
       💼 DM hôm nay: +1.8% (outperform VN-Index +1.7 pp)
       📰 Tin quan trọng: [3 tin]
       ⚠️ Cần làm ngày mai: review VIC (volume bất thường chưa rõ lý do)
         ↓
     Trader: /screen --preset breakout
       → Tìm mã có breakout volume hôm nay
       → Thêm vào watchlist cho phiên mai
         ↓
     Trader: /alert VIC giá < 45000
       → Đặt stoploss alert cho VIC
         ↓
     Trader: /analyze VIC
       → Deep-dive VIC sau volume bất thường
       → Tìm ra: VIC có tin nội bộ về dự án Vinhomes Ocean Park 3
       → Quyết định: giữ, chờ confirm tin chính thức
```

---

### Workflow 5: Phân tích BCTC quý mới

```
Kịch bản: VNM vừa công bố BCTC Q1/2026

Trader: /analyze VNM --mode fa

Claude:
  1. get_financial_report("VNM", period="5q")
     → Q1/2026: Doanh thu 16.200 tỷ (+8% YoY), LN ròng 2.100 tỷ (-3% YoY)

  2. Skill fundamental-analysis:
     → Revenue tăng nhưng margin thu hẹp (13% vs 15% Q1/2025)
     → Chi phí nguyên liệu tăng (giá sữa thô tăng 12%)
     → ROE: 26.5% (vẫn tốt, giảm nhẹ từ 28.2%)
     → P/E hiện tại 22.5× — hơi cao so với EPS growth chậm lại

  3. Skill news-impact:
     → Market đang kỳ vọng EPS growth 8%, thực tế -3% → miss
     → Lịch sử: khi miss kỳ vọng, VNM thường giảm 3-5% trong 2-3 phiên

  4. Kết luận:
     ⚠️ VNM: TRUNG LẬP → có thể GIẢM ngắn hạn
     - FA: Kết quả miss kỳ vọng, margin thu hẹp
     - TA: Giá đang vùng kháng cự 75.500
     - Risk: Có thể về test MA50=71.000 trong 5-10 phiên
     - Hành động: Cân nhắc chốt một phần (30-50%) tại vùng hiện tại
                  Nếu muốn giữ: stoploss tại 71.500
```

---

## 9. HƯỚNG DẪN TRIỂN KHAI

### Bước 1: Setup cơ bản (Ngày 1)
```bash
# 1. Clone và cài dependencies
cd vn-stock-trader
cd mcp-server
pip install -e ".[dev]"

# 2. Config credentials (tùy chọn — hoạt động không cần token)
cp .env.example .env
# Điền VNSTOCK_TOKEN để nâng lên Community tier (60 req/phút, 8 kỳ tài chính)
# Không cần SSI credentials — dùng vnstock + Vietstock crawl miễn phí

# 3. Tạo portfolio mẫu
mkdir -p data
echo '{"account_id": "demo", "positions": [], "cash": 1000000000, "t1_cash": 0, "t2_cash": 0}' > data/portfolio.json

# 4. Test MCP server
python server.py

# 5. Test tool cơ bản
python -c "import asyncio; from tools.market import get_market_overview; print(asyncio.run(get_market_overview()))"
```

### Bước 2: Tích hợp Claude Code (Ngày 1-2)
```bash
# 1. Thêm MCP server vào Claude Code settings
# Edit ~/.claude/settings.json hoặc .claude/settings.json

# 2. Copy skill files vào .claude/skills/
# Copy agent files vào .claude/agents/
# Copy command files vào .claude/commands/

# 3. Test slash commands
# Trong Claude Code session:
# /analyze VNM
# /screen --preset value
# /portfolio
```

### Bước 3: Setup automation (Ngày 3)
```bash
# 1. Setup cron jobs
chmod +x scripts/cron_setup.sh
./scripts/cron_setup.sh

# 2. Test morning brief
python scripts/morning_brief.py

# 3. Setup alerts
# /alert VNM giá > 80000
```

### Bước 4: Kiểm tra Vietstock crawl
```bash
# Test Vietstock client
python -c "
from data_sources.vietstock_client import VietstockClient
import asyncio
client = VietstockClient()
# Lấy thử tin tức VNM
news = asyncio.run(client.get_news('VNM', limit=5))
print(news)
"

# Test financial data từ Vietstock
python -c "
from data_sources.vietstock_client import VietstockClient
import asyncio
client = VietstockClient()
ratios = asyncio.run(client.get_financial_ratios('VNM'))
print(ratios)
"
```

---

## 10. DEPENDENCY MAP

```
Trader
  └── Claude Code (UI layer)
        ├── Commands → Slash commands kích hoạt workflows
        ├── Skills → Instructions cho Claude phân tích
        ├── Agents → Chạy độc lập, tự động
        └── MCP Server (vn-stock-mcp)
              ├── vnstock/TCBS (giá & giao dịch — delay ~15p, free, không cần TK)
              │     ├── Giá OHLCV lịch sử + snapshot hiện tại
              │     ├── Danh sách mã HOSE/HNX/UPCOM
              │     ├── Foreign room, breadth, top movers
              │     └── Dữ liệu phái sinh (VN30F, VN100F)
              ├── Vietstock crawl (tin tức, BCTC, chỉ số tài chính — free)
              │     ├── Tin tức doanh nghiệp
              │     ├── Báo cáo tài chính (BCTC quý/năm)
              │     └── Chỉ số tài chính (P/E, P/B, ROE, EPS...)
              ├── ta-lib (TA indicators tính local — no API call)
              │     ├── MA, RSI, MACD, Bollinger Bands, ATR
              │     └── Volume indicators, momentum
              └── CafeF / HOSE.vn scrapers (tin tức bổ sung)
```

> **Chi phí data: $0** | Không cần tài khoản broker | Delay ~15 phút (phù hợp swing trader)

---

*Thiết kế bởi VN Stock Trader Agent — 2026-03-29*
*Cập nhật data stack — 2026-03-30: vnstock/TCBS + Vietstock crawl + ta-lib local*
*Căn cứ: MARKET_ANALYSIS.md*

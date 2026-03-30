# Phân tích Thị trường Chứng khoán Việt Nam & Nhu cầu Trader
**Ngày nghiên cứu:** 2026-03-29
**Mục tiêu:** Xây dựng bộ Claude plugin/skill phù hợp với trader chứng khoán Việt Nam

---

## 1. Tổng quan Thị trường Chứng khoán Việt Nam

### 1.1 Quy mô và Hiệu suất

| Chỉ số | Giá trị (cuối 2025) |
|--------|---------------------|
| **VN-Index** | **1.784,49 điểm** (+40,8% so với 2024 — kỷ lục lịch sử) |
| **HNX-Index** | 248,77 điểm (+9,4%) |
| **Vốn hóa HOSE** | ~219 tỷ USD |
| **Vốn hóa HNX** | ~15,1 tỷ USD |
| **Vốn hóa UPCOM** | ~59,8 tỷ USD |
| **Tổng vốn hóa** | 9.975 nghìn tỷ VND (~77,9% GDP) |
| **Thanh khoản bình quân** | 772 triệu cp/ngày; 23.627 tỷ VND/ngày (~900 triệu USD) |

### 1.2 Số lượng Nhà đầu tư

- **11,6 triệu tài khoản** cuối 2025 (tăng 2,3 triệu so với cuối 2024)
- Đã **vượt mục tiêu chiến lược 2030** trước hạn 5 năm
- Nhà đầu tư nước ngoài chiếm ~12,83% giá trị giao dịch tháng 12/2025
- Nước ngoài bán ròng kỷ lục **136 nghìn tỷ VND (~5,2 tỷ USD)** trong 2025

### 1.3 Cấu trúc Sàn

| Sàn | Số chứng khoán | Đặc điểm |
|-----|----------------|-----------|
| **HOSE** | 400 cổ phiếu + 18 ETF + 4 CCQ + 259 chứng quyền | Sàn chính, big-cap |
| **HNX** | 329 công ty niêm yết | Mid-cap, trái phiếu Chính phủ |
| **UPCOM** | 860 công ty | Giao dịch phi tập trung, small-cap |

### 1.4 Xu hướng & Sự kiện Lớn 2025-2026

| Sự kiện | Thời điểm | Tác động |
|---------|-----------|----------|
| **FTSE Russell nâng hạng** — từ Cận biên lên Mới nổi Thứ cấp | Chính thức 21/09/2026 | Dự kiến 3,4–10,4 tỷ USD dòng vốn ETF thụ động/chủ động đổ vào |
| **Hệ thống KRX** ra mắt | 05/05/2025 | Nền tảng giao dịch/thanh toán mới; hỗ trợ T+0, bán khống, CCP (Q1/2027) |
| **VN100 Futures** ra mắt | 10/10/2025 | Hợp đồng tương lai chỉ số mới bên cạnh VN30F |
| **Công bố thông tin bằng tiếng Anh** | VN30 từ 01/2025; toàn bộ ~2.000 công ty từ cuối 2026 | Thu hút thêm nhà đầu tư ngoại |
| **Bỏ ký quỹ trước (pre-funding)** | 2025 | Giảm ma sát giao dịch cho nhà đầu tư nước ngoài |
| **Pilot tài sản token hóa** | 9/2025, chương trình 5 năm | Mở cửa cho tài sản số |

**Intraday ATH:** 1.805,93 điểm (25/12/2025)

---

## 2. Các Công ty Chứng khoán Hàng đầu

### 2.1 Thị phần Môi giới HOSE 2025

| Hạng | Công ty | Thị phần 2025 | Ghi chú |
|------|---------|---------------|---------|
| 1 | **VPS** (Vietnam Prosperity Securities) | **15,95%** | Dẫn đầu nhiều năm liên tiếp |
| 2 | **SSI** | **11,53%** | Tăng mạnh từ 9,18% năm 2024 |
| 3 | **TCBS** (Techcom Securities) | ~10% | Mạnh về TP, quỹ mở |
| 4 | **HSC** (Ho Chi Minh City Securities) | Top 4 | Tăng 1 bậc |
| 5 | **Vietcap** | Top 5 | |
| 6 | **VNDirect** | Top 6 | |
| 7 | **MBS** (MB Securities) | Top 7 | |
| 8 | **KIS Việt Nam** | Top 8 | Tăng lên từ hạng 9 |
| 9 | **VCBS** | Top 9 | |
| 10 | **VPBankS** | 3,21% | **Tân binh** vào top 10 |

> Top 10 nắm giữ **>68% thị phần môi giới HOSE**.
> FPTS bị loại khỏi top 10. Mirae Asset giảm từ 4,67% → 2,82%.

### 2.2 So sánh Chi tiết Các Sàn

#### VPS (Dẫn đầu #1)
- **App:** SmartOne (all-in-one), SmartPro (phái sinh), SmartEasy (mô phỏng phái sinh)
- **API:** Chưa công bố chính thức (đầu 2026)
- **Phí:** Cạnh tranh; nổi tiếng về margin rate thấp
- **Điểm mạnh:** Tech-first, UX mượt, copy trading phái sinh

#### SSI (Hạng 2)
- **App:** iSSI / SSI iBoard
- **API:** ✅ **SSI FastConnect API** (chính thức, công khai)
  - **FC Data:** streaming dữ liệu thị trường
  - **FC Trading:** đặt/hủy lệnh
  - **Auth:** ConsumerID + ConsumerSecret + RSA/SHA256
  - **SDK:** Python, Node.js, Java, .NET
  - **Validity:** 1 năm/lần gia hạn
  - **Phí:** Miễn phí cho tài khoản SSI
  - **Docs:** guide.ssi.com.vn/ssi-products
- **Phí giao dịch:** 0,05%–0,1%
- **Điểm mạnh:** API tốt nhất hiện tại, uy tín lâu đời

#### TCBS (Hạng 3)
- **App:** TCInvest (cổ phiếu, trái phiếu, quỹ, phái sinh, tối ưu hóa danh mục Markowitz)
- **API:** Tài liệu PDF tại static.tcbs.com.vn/oneclick/API.pdf (bán chính thức; vnstock dùng)
- **Phí:** 0,1%
- **Điểm mạnh:** Tích hợp ecosystem Techcombank, phân tích 1.350+ cổ phiếu

#### VNDirect (Hạng 6)
- **App:** DNSE / Dstock
- **API:** REST, được cộng đồng document (không chính thức)
- **Phí:** 0,15%–0,35%

#### BSC & DNSE (Algo-friendly)
- **BSC:** Tiên phong trong open API; phù hợp algo trader mới bắt đầu
- **DNSE (Dragon Capital Securities):** Hỗ trợ hạ tầng algo trading; được recommend cho trader muốn tối ưu chi phí

---

## 3. Nhu cầu Thực tế của Trader Việt Nam

### 3.1 Nhà đầu tư Cá nhân (Retail — Đại đa số 11,6M tài khoản)

**Đặc điểm hành vi:**
- Mobile-first; quen dùng app broker + FireAnt
- Nặng về cộng đồng/xã hội (tin vào "sóng" theo herd)
- Giao dịch theo tin tức, sentiment, và recommendation từ group Telegram/Zalo
- Ít dùng phân tích định lượng

**Nhu cầu cốt lõi:**
| Nhu cầu | Mức độ ưu tiên |
|---------|----------------|
| Khớp lệnh nhanh, ổn định giờ cao điểm (ATO/ATC) | 🔴 Rất cao |
| Cảnh báo giá, volume bất thường | 🔴 Rất cao |
| Tin tức realtime ảnh hưởng cổ phiếu | 🔴 Rất cao |
| Phân tích cơ bản đơn giản (P/E, P/B, EPS) | 🟠 Cao |
| Lọc cổ phiếu theo tiêu chí | 🟠 Cao |
| Quản lý danh mục, theo dõi lãi/lỗ | 🟠 Cao |
| Phân tích kỹ thuật (đường MA, RSI, MACD) | 🟡 Trung bình |
| Học đầu tư, giải thích khái niệm | 🟡 Trung bình |
| Lập kế hoạch dòng tiền T+2 | 🟡 Trung bình |

### 3.2 Trader Chuyên nghiệp / Quỹ

**Đặc điểm:**
- Dùng AmiBroker + FireAnt Metakit, Python (vnstock, SSI API)
- Theo dõi dữ liệu khối ngoại, dòng tiền quỹ
- Quan tâm FTSE upgrade inflows và foreign room

**Nhu cầu cốt lõi:**
| Nhu cầu | Mức độ ưu tiên |
|---------|----------------|
| Backtesting chiến lược | 🔴 Rất cao |
| API data tốc độ cao, ổn định | 🔴 Rất cao |
| Phái sinh (VN30F, VN100F) | 🔴 Rất cao |
| Risk management, VaR | 🟠 Cao |
| Algo order routing | 🟠 Cao |
| Portfolio optimization | 🟠 Cao |
| Dữ liệu tổ chức/insider flows | 🟠 Cao |
| Phân tích đa tài sản (cổ phiếu + TP + FX) | 🟡 Trung bình |

---

## 4. Các Tool / Platform Trader Đang Dùng

### 4.1 FireAnt — Cộng đồng Trader #1

- **1,3+ triệu MAU** — platform cộng đồng trader lớn nhất Việt Nam
- Tính năng: dữ liệu realtime, social feed, AI Copilot, tin tức thị trường
- **FireAnt Metakit:** plugin data feed cho AmiBroker & MetaStock
  - Dữ liệu HOSE/HNX/UPCOM: giá, khối ngoại, cung/cầu (depth), tick/phút
  - Chỉ số ngành ICB, custom index danh mục
  - Có phí
- Shinhan Securities (Hàn Quốc) mua cổ phần chiến lược năm 2025

### 4.2 Simplize — Phân tích Cơ bản

- Phân tích định giá, báo cáo cổ phiếu, theo dõi insider trading
- Dòng tiền quỹ, chỉ số chu kỳ thị trường (Market Cycle Index)
- Chỉ số cấu trúc thị trường (cảnh báo khủng hoảng sớm)
- Quản lý danh mục tích hợp AI, 1.600+ cổ phiếu
- Top 10 tool định giá Việt Nam 2025

### 4.3 TradingView

- Dùng để charting; tích hợp ticker VN (HOSE:VNINDEX, etc.)
- Không có tính năng đặt lệnh VN; chủ yếu làm overlay phân tích kỹ thuật

### 4.4 AmiBroker

- Ưa thích bởi trader kỹ thuật/quant để backtesting
- Ngôn ngữ AFL (AmiBroker Formula Language) để code chiến lược
- Data qua FireAnt Metakit (có phí)

### 4.5 MetaStock

- Đang suy giảm ở VN; MetaStock DataLink ngừng từ giữa 2025
- FireAnt Metakit vẫn hỗ trợ import data

### 4.6 Nguồn dữ liệu / Tin tức

| Nguồn | Loại dữ liệu |
|-------|-------------|
| CafeF (cafef.vn) | Tin tức kinh tế, tài chính doanh nghiệp |
| Vietstock (vietstock.vn) | Dữ liệu cổ phiếu, phân tích kỹ thuật |
| VNExpress Kinh doanh | Tin tức vĩ mô, doanh nghiệp |
| Người Lao Động / Tuổi Trẻ Kinh Tế | Tin tức thị trường |
| HNX.vn / HOSE.vn | Thông báo chính thức, BCTC |
| Telegram/Zalo groups | Tin tức nóng, khuyến nghị cộng đồng |

---

## 5. Gap Analysis — Claude Plugin Có Thể Giải Quyết Gì?

### 5.1 Pain Points Hiện tại

#### 🔴 Pain Point #1: Phân mảnh Dữ liệu
- Không có nguồn dữ liệu đơn lẻ đáng tin, giá hợp lý, realtime
- vnstock miễn phí nhưng bị rate limit và phụ thuộc nguồn không chính thức (TCBS API đứt năm 2024-2025)
- Cần tích hợp nhiều nguồn: giá từ SSI/TCBS, tin từ CafeF, BCTC từ VNDirect...

#### 🔴 Pain Point #2: Ứng dụng Sập Giờ Cao điểm
- Apps broker crash/lag trong phiên ATO (09:00-09:15) và ATC (14:30-14:45)
- Đây là thời điểm quan trọng nhất trong ngày với trader

#### 🟠 Pain Point #3: Phân tích BCTC Khó & Tốn Thời gian
- Báo cáo tài chính dày, nhiều thuật ngữ kế toán
- Cần đọc thuyết minh, so sánh qua các quý, tính toán ratio thủ công
- Chưa có tool AI tốt giải thích BCTC bằng tiếng Việt

#### 🟠 Pain Point #4: Hệ sinh thái Algo Trading Kém Phát triển
- Chỉ SSI, BSC, DNSE có API public; VPS, VNDirect chưa
- Polling cycle ~2 giây — quá chậm cho nhiều chiến lược
- Không có backtesting platform nativeVN; phải dùng AmiBroker + data patch

#### 🟠 Pain Point #5: Thiếu Context khi Đọc Tin
- Tin tức nhiều nhưng trader không biết tác động thực sự đến cổ phiếu nào
- Không có tool tự động map "tin → cổ phiếu bị ảnh hưởng → lịch sử phản ứng"

#### 🟡 Pain Point #6: Quản lý Rủi ro Kém
- Đa số retail không tính VaR, max drawdown, position sizing
- Không có tool nhắc nhở về ngưỡng ký quỹ, T+2 cash flow

#### 🟡 Pain Point #7: Khoảng cách Trình độ
- 11,6M tài khoản mà đa số mới, thiếu kiến thức tài chính
- Nhu cầu giải thích AI thân thiện bằng tiếng Việt rất cao

### 5.2 Những Workflow AI Có Thể Tự Động Hóa

| Workflow hiện tại | Thời gian thủ công | AI Plugin giải quyết |
|-------------------|-------------------|----------------------|
| Đọc BCTC quý/năm | 2-4 giờ/cổ phiếu | Tóm tắt BCTC tự động |
| So sánh P/E với ngành | 30-60 phút | Screener + so sánh ngành ngay lập tức |
| Theo dõi tin tức liên quan | Cả ngày liên tục | Digest tin tức theo danh mục cá nhân |
| Tính position size/risk | 15-30 phút/giao dịch | Risk calculator tự động |
| Lập danh sách watch list | Thủ công, rải rác | Stock screener theo tiêu chí AI |
| Phân tích insider trading | Tra nhiều nguồn | Aggregator + alert tự động |

---

## 6. Dữ liệu / API Có sẵn

### 6.1 vnstock — Thư viện Python Chính

```bash
pip install vnstock
```

| Thuộc tính | Giá trị |
|------------|---------|
| **GitHub** | github.com/thinh-vu/vnstock |
| **Version** | 3.4.0 (16/01/2026) |
| **Data sources** | TCBS (primary), VCI |
| **Coverage** | Giá lịch sử/RT, tài chính, chỉ số VN, CQW, VN30F, ETF, trái phiếu, FX, crypto, tin tức |

**Rate Limits:**

| Tier | Giới hạn | Số kỳ tài chính |
|------|----------|-----------------|
| Guest (miễn phí) | 20 req/phút | 4 kỳ |
| Community (đăng ký miễn phí) | 60 req/phút | 8 kỳ |
| Sponsor (có phí) | 3-5x cao hơn | Đầy đủ |

> ⏱ **Độ trễ dữ liệu:** ~15 phút (không phải realtime). Phù hợp **swing trader** (nắm giữ nhiều ngày). Không phù hợp day trader cần giá realtime.

### 6.2 SSI FastConnect API (Chính thức — ❌ Không sử dụng)

- **FC Data:** streaming thị trường
- **FC Trading:** đặt/hủy lệnh
- **Auth:** RSA + SHA256 + ConsumerID/Secret; hết hạn 1 năm
- **SDK:** Python, Node.js, Java, .NET
- **Miễn phí** cho tài khoản SSI
- **Docs:** guide.ssi.com.vn/ssi-products

> **Quyết định:** ❌ **Không tích hợp SSI FastConnect API** — yêu cầu mở tài khoản môi giới SSI, tạo rào cản cho người dùng. Thay thế bằng vnstock (giá, delay 15p) + Vietstock crawl (tin tức, BCTC) — hoàn toàn miễn phí, không cần tài khoản.

### 6.3 Các nguồn khác

| Nguồn | Loại | Ghi chú |
|-------|------|---------|
| VNDirect API | Cộng đồng document | REST endpoints; không chính thức |
| TCBS API | Bán chính thức PDF | Thay đổi nhiều 2024-2025 |
| DNSE API | Chính thức | Cho algo trading khách hàng |
| vietfin | Python lib | github.com/vietfin/vietfin |
| vnquant | Python lib (cũ) | github.com/phamdinhkhanh/vnquant |
| **VN Stock API MCP Server** | MCP | LobeHub; LLM-integrated stock queries |

### 6.5 ✅ Data Stack Chính thức (Đã chốt)

| Mục đích | Nguồn | Chi phí | Ghi chú |
|----------|-------|---------|---------|
| **Giá & giao dịch** | vnstock / TCBS | Miễn phí | Delay ~15 phút; không cần TK broker |
| **Tin tức** | Vietstock crawl | Miễn phí | Tin tức doanh nghiệp, thị trường |
| **BCTC** | Vietstock crawl | Miễn phí | Báo cáo tài chính quý/năm |
| **Chỉ số tài chính** | Vietstock crawl | Miễn phí | P/E, P/B, ROE, EPS, Debt/Equity |
| **TA indicators** | ta-lib (local) | Miễn phí | MA, RSI, MACD, BB, ATR — tính từ OHLCV |
| **Tổng chi phí** | — | **$0** | — |

**Phù hợp với:** Swing trader, position trader, nhà đầu tư cơ bản
**Không phù hợp với:** Day trader, scalper (cần giá realtime)

### 6.4 Giới hạn Hạ tầng

- **API polling cycle: ~2 giây** (thị trường phát triển: mili-giây)
- Không có CCP đến Q1/2027
- Không có HFT infrastructure công khai cho retail/semi-pro

---

## 7. Đề xuất Bộ Plugin Ban đầu

### Ưu tiên theo Ma trận Giá trị × Khả thi

| Plugin | Mô tả | Giá trị | Khả thi | Priority |
|--------|-------|---------|---------|----------|
| **1. Market Dashboard** | Snapshot thị trường realtime: VN-Index, top mover, thanh khoản, khối ngoại | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🔴 P0 |
| **2. Stock Analyzer** | Phân tích nhanh 1 mã: giá, kỹ thuật, cơ bản, tin tức gần nhất | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🔴 P0 |
| **3. Financial Report Summarizer** | Tóm tắt BCTC bằng tiếng Việt, highlight điểm quan trọng | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🔴 P0 |
| **4. Stock Screener** | Lọc cổ phiếu theo P/E, P/B, ROE, volume bất thường, price band... | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟠 P1 |
| **5. News Impact Analyzer** | Đọc tin tức → xác định cổ phiếu bị ảnh hưởng → dự đoán chiều hướng | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🟠 P1 |
| **6. Portfolio Risk Manager** | Tính VaR, position size, T+2 cash flow, cảnh báo margin | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟠 P1 |
| **7. Sector Comparator** | So sánh cổ phiếu trong cùng ngành (Banking, Real Estate, Steel...) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟠 P1 |
| **8. Insider & Fund Flow Tracker** | Theo dõi giao dịch nội bộ, dòng tiền quỹ, khối ngoại | ⭐⭐⭐⭐ | ⭐⭐⭐ | 🟡 P2 |
| **9. FTSE Upgrade Impact Tracker** | Foreign room, ước tính inflow ETF cho từng cổ phiếu | ⭐⭐⭐⭐ | ⭐⭐⭐ | 🟡 P2 |
| **10. Watchlist & Alert Manager** | Theo dõi watchlist cá nhân, cảnh báo giá/volume/RSI tùy điều kiện | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🟡 P2 |

### 7.1 Chi tiết Plugin P0 (Ưu tiên Cao nhất)

#### Plugin 1: Market Dashboard
```
Công dụng: Snapshot thị trường buổi sáng/chiều
Input: Không (hoặc ngày cụ thể)
Output:
  - VN-Index / HNX-Index / UPCOM-Index hiện tại vs hôm qua
  - Top 5 tăng/giảm mạnh nhất
  - Thanh khoản tổng thị trường
  - Khối ngoại mua/bán ròng
  - Breadth (số mã tăng/giảm/đứng giá)
  - Price band hits (mã đạt trần/sàn)
Data: vnstock (Community tier)
```

#### Plugin 2: Stock Analyzer
```
Công dụng: Phân tích nhanh một mã cổ phiếu
Input: Mã cổ phiếu (VD: "VNM", "HPG", "ACB")
Output:
  - Thông tin cơ bản: giá, volume, % thay đổi
  - Kỹ thuật: MA20/50/200, RSI, MACD, Bollinger Bands
  - Cơ bản: P/E, P/B, EPS, ROE, Debt/Equity
  - Tin tức gần nhất 7 ngày
  - So sánh với trung bình ngành
  - Nhận xét ngắn bằng tiếng Việt
Data: vnstock + CafeF
```

#### Plugin 3: Financial Report Summarizer
```
Công dụng: Tóm tắt BCTC quý/năm của doanh nghiệp
Input: Mã cổ phiếu + quý/năm
Output:
  - Doanh thu, lợi nhuận ròng vs kỳ trước (%)
  - Các điểm bất thường trong BCTC
  - Chỉ tiêu thanh khoản, hiệu quả, đòn bẩy
  - Highlights thuyết minh quan trọng
  - Đánh giá ngắn: tích cực/tiêu cực/trung lập
Data: vnstock financial data
```

### 7.2 Tech Stack Gợi ý

```
Language:      Python 3.11+
Data:          vnstock/TCBS (giá, delay ~15p, free) + Vietstock crawl (tin tức, BCTC, chỉ số)
TA:            ta-lib (tính local từ OHLCV — không cần API)
Framework:     MCP Server + Claude skills/plugins + slash commands
LLM:           Claude API (claude-sonnet-4-5)
Formatting:    ruff (lint/format)
Testing:       pytest
Dependencies:  vnstock, pandas, ta-lib, beautifulsoup4, httpx, mcp
Chi phí data:  $0 (không cần tài khoản broker)
```

---

## 8. Roadmap Gợi ý

### Phase 1 — Foundation (Tháng 1-2)
- [ ] Set up Python project với vnstock
- [ ] Build Plugin 1: Market Dashboard
- [ ] Build Plugin 2: Stock Analyzer (TA + FA cơ bản)
- [ ] Build Plugin 3: Financial Report Summarizer

### Phase 2 — Screener & News (Tháng 3-4)
- [ ] Build Plugin 4: Stock Screener
- [ ] Build Plugin 5: News Impact Analyzer
- [ ] Build Plugin 6: Portfolio Risk Manager

### Phase 3 — Advanced (Tháng 5-6)
- [ ] Build Plugin 7: Sector Comparator
- [ ] Build Plugin 8: Insider & Fund Flow Tracker
- [ ] Build Plugin 9: FTSE Upgrade Impact Tracker
- [ ] Tối ưu Vietstock crawl (caching, rate limit handling)

### Phase 4 — Polish & Automation (Tháng 7+)
- [ ] Build Plugin 10: Watchlist & Alert Manager (cảnh báo giá/volume/RSI)
- [ ] Backtesting framework (dùng data lịch sử vnstock)
- [ ] Tự động hóa morning brief + session summary (cron + Claude headless)

---

## 9. Nguồn Tham khảo

1. [Dấu ấn TTCK Việt Nam 2025 - Tạp chí Ngân hàng](https://tapchinganhang.gov.vn/dau-an-thi-truong-chung-khoan-viet-nam-nam-2025-va-giai-phap-trong-tam-nam-2026-17059.html)
2. [Record highs 2025 - Vietnam News](https://vietnamnews.vn/economy/1732935/record-highs-structural-change-shape-viet-nam-s-stock-market-in-2025.html)
3. [Thị phần môi giới HOSE 2025 - Thời báo Tài chính VN](https://thoibaotaichinhvietnam.vn/thi-phan-moi-gioi-san-hose-nam-2025-top-3-thu-hep-khoang-cach-vps-tiep-tuc-giu-ngoi-vuong-190249.html)
4. [vnstock Python library - GitHub](https://github.com/thinh-vu/vnstock)
5. [SSI FastConnect API Docs](https://guide.ssi.com.vn/ssi-products)
6. [API Vietnam Stock Market - Algotrade Hub](https://hub.algotrade.vn/knowledge-hub/api-in-vietnam-stock-market/)
7. [FireAnt Trading Community](https://fireant.vn/)
8. [FireAnt Metakit](https://metakit.fireant.vn/intro/)
9. [Simplize - Stock Analysis](https://simplize.vn/)
10. [FTSE Russell Vietnam Upgrade - LSEG](https://www.lseg.com/en/media-centre/press-releases/ftse-russell/2025/ftse-russell-country-classification-september-2025)
11. [KRX Trading System Launch - Vietnam Net](https://vietnamnet.vn/en/krx-trading-system-goes-live-marking-turning-point-for-vietnam-s-stock-market-2397688.html)
12. [Pain Points of VN Securities Companies - YouNet Media](https://younetmedia.com/phan-hoi-nguoi-dung-tren-mxh-ve-cac-cong-ty-chung-khoan-trai-nghiem-noi-bat-nhung-pain-point-dang-chu-y/)
13. [Algo & Quant Trading in Vietnam - Algotrade Hub](https://hub.algotrade.vn/knowledge-hub/algorithmic-trading-quant-trading-and-high-frequency-trading/)
14. [VinaCapital FTSE Research Note](https://vinacapital.com/wp-content/uploads/2025/10/VinaCapital-Insights-Vietnams-emerging-market-upgrade-Reclassification-expected-in-September-2026.pdf)

---

*Report được tạo bởi Claude Agent với dữ liệu thực tế từ internet (tháng 3/2026)*
*Cập nhật data stack — 2026-03-30: chốt vnstock/TCBS + Vietstock crawl + ta-lib local; bỏ SSI FastConnect & place_order*

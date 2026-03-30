---
name: sector-compare
description: So sánh ngành và vị thế tương đối của cổ phiếu Việt Nam trong cùng sector — peer analysis
triggers:
  - "so sánh ngành"
  - "sector"
  - "peer"
  - "so sánh"
  - "ngành ngân hàng"
  - "ngành bất động sản"
  - "cùng ngành"
---

# Skill: So sánh Ngành (Sector Comparison)

## Mục tiêu
Đánh giá vị thế tương đối của một cổ phiếu trong ngành — ai dẫn đầu, ai bị định giá thấp, sector outlook.

## Danh sách ngành chính VN

| Ngành | Mã tiêu biểu | Đặc điểm định giá |
|-------|-------------|-------------------|
| Ngân hàng | VCB, BID, CTG, TCB, MBB, VPB, ACB | P/B, NIM, NPL |
| Bất động sản | VHM, VIC, NVL, PDR, KDH, DXG | P/B, NAV discount, presale |
| Chứng khoán | SSI, VND, HCM, VCI | P/B, ROE, market volume |
| Thép | HPG, HSG, NKG, TIS | P/E, EV/EBITDA, HRC price |
| Dầu khí | GAS, PVD, PVT, PLX | EV/EBITDA, oil price beta |
| Công nghệ | FPT, CMG, ELC | P/E, revenue growth |
| Bán lẻ | MWG, PNJ, FRT | P/E, SSSG (same-store sales growth) |
| Thực phẩm | VNM, MSN, SAB, MCH | P/E, biên LN, brand moat |
| Điện | PC1, REE, GEG, BCG | P/E, dividend, capacity expansion |
| Vận tải | ACV, VJC, HVN, GMD | EV/EBITDA, load factor |

## Quy trình thực hiện

### Bước 1 — Xác định peer group
```
get_sector_peers(symbol)           → danh sách 5–10 peers cùng ngành
get_sector_overview(sector)        → tổng quan ngành: growth, outlook
```

### Bước 2 — Thu thập metrics peers
```
for each peer in peers:
    get_financial_ratios(peer)     → P/E, P/B, ROE, EPS growth
    get_stock_price(peer)          → market cap, volume
    get_price_performance(peer)    → YTD, 1M, 3M, 6M, 1Y return
```

### Bước 3 — Bảng so sánh tổng hợp

**Metrics cần so sánh:**

| Metric | Ý nghĩa | Tốt hơn khi |
|--------|---------|-------------|
| P/E relative | Định giá vs peers | Thấp hơn peers cùng ROE |
| P/B relative | Định giá tài sản | Thấp hơn nếu ROE tương đương |
| ROE | Hiệu quả vốn | Cao nhất nhóm |
| EPS growth | Tăng trưởng | Nhanh nhất nhóm |
| Dividend Yield | Thu nhập | Cao nhất nhóm |
| Debt/Equity | Rủi ro | Thấp nhất nhóm |
| Volume/Market cap | Thanh khoản | >0.1% market cap/ngày |

### Bước 4 — Xác định position trong ngành

**Leader:** ROE cao nhất + định giá premium hợp lý
**Challenger:** Tăng trưởng nhanh hơn nhưng định giá thấp hơn leader
**Value play:** Định giá rẻ nhất nhóm với fundamentals OK
**Laggard:** Định giá thấp vì fundamentals yếu

### Bước 5 — Sector outlook

**Bull case:** Vì sao ngành có thể outperform?
**Bear case:** Rủi ro ngành — regulatory, macro, commodity
**Catalyst sắp tới:** Policy, mùa KQKD, sự kiện ngành

## Format đầu ra

```
🏭 SO SÁNH NGÀNH: [SECTOR] — [X mã]
═══════════════════════════════════════

📊 BẢNG SO SÁNH PEERS:
┌────────┬──────┬──────┬───────┬────────┬──────────┬────────┐
│ Mã     │ P/E  │ P/B  │ ROE   │ EPS YoY│ Div Yield│ YTD    │
├────────┼──────┼──────┼───────┼────────┼──────────┼────────┤
│ ★ XXX  │ 12x  │ 2.1x │ 18%   │ +22%   │ 3.2%     │ +15%   │ ← đang phân tích
│ YYY    │ 15x  │ 2.8x │ 20%   │ +18%   │ 2.1%     │ +22%   │
│ ZZZ    │ 9x   │ 1.4x │ 12%   │ +8%    │ 4.5%     │ -3%    │
└────────┴──────┴──────┴───────┴────────┴──────────┴────────┘

📍 VỊ THẾ: [SYMBOL] là [Leader/Challenger/Value Play/Laggard]

🏆 DẪN ĐẦU NGÀNH: [SYMBOL] — [lý do 1 câu]
💎 VALUE NHẤT: [SYMBOL] — [lý do 1 câu]
📈 TĂNG TRƯỞNG NHẤT: [SYMBOL] — [lý do 1 câu]

🌐 OUTLOOK NGÀNH
• Ngắn hạn (3T): [Tích cực/Trung tính/Tiêu cực]
• Dài hạn (12T): [Tích cực/Trung tính/Tiêu cực]
• Catalyst: [list]
• Rủi ro: [list]

📌 KẾT LUẬN
[SYMBOL] so với peers: [đắt/rẻ/hợp lý] với premium/discount [X%]
Lý do nên/không nên ưu tiên: [1–2 câu]
```

## Lưu ý thị trường Việt Nam

- **Ngân hàng:** So sánh NIM (net interest margin) và CASA ratio thay vì chỉ P/E
- **BĐS:** NAV discount quan trọng — nhiều DN BĐS giao dịch discount 30–50% NAV
- **Chứng khoán:** Volume thị trường ảnh hưởng trực tiếp doanh thu → β cao
- **Thép:** Giá HRC (hot-rolled coil) quốc tế là yếu tố lớn nhất → theo dõi LME
- **VN30 vs mid-cap:** Blue chips thường trade premium 20–30% so với mid-cap cùng ngành
- **Foreign ownership limit:** Ngân hàng = 30%, phần lớn ngành = 49%, một số = 100%
- **Sector rotation:** Theo dõi dòng tiền khối ngoại để xác định ngành được ưa chuộng

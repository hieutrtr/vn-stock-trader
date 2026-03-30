---
description: Lấy và phân tích tin tức cổ phiếu/thị trường Việt Nam
---

# /news — Tin tức Cổ phiếu & Thị trường

## Cú pháp
```
/news                        # Tin thị trường tổng hợp hôm nay
/news <SYMBOL>               # Tin về một mã cụ thể
/news <SYMBOL> --days 14     # Tin 14 ngày gần nhất (mặc định: 7)
/news market                 # Tin vĩ mô, chính sách
/news sector <sector>        # Tin ngành cụ thể
/news macro                  # Tin vĩ mô: lãi suất, tỷ giá, GDP
```

## Ví dụ
```
/news VCB
/news HPG --days 14
/news sector banking
/news macro
```

## Nguồn tin tổng hợp

| Nguồn | Loại | Độ tin cậy |
|-------|------|------------|
| CafeF | Tổng hợp | ★★★★★ |
| VietStock | Tổng hợp | ★★★★★ |
| HOSE/HNX website | Chính thức | ★★★★★ |
| SSC (Uỷ ban CK) | Chính thức | ★★★★★ |
| NDH (Nhịp Cầu Đầu Tư) | Phân tích | ★★★★ |
| Báo Đầu Tư | Tổng hợp | ★★★★ |

## Output `/news <SYMBOL>`

```
📰 TIN TỨC: [SYMBOL] — [TÊN CÔNG TY]
7 ngày gần nhất | Cập nhật: DD/MM/YYYY

🔴 TIN QUAN TRỌNG:
• [Ngày] [Tiêu đề] — [Nguồn]
  → Impact: Cao | Sentiment: +4/5
  → Tóm tắt: [1–2 câu nội dung chính]

🟡 TIN VỪA:
• [Ngày] [Tiêu đề] — [Nguồn]

📅 SỰ KIỆN SẮP TỚI:
• [Ngày]: ĐHCĐ — Kỳ vọng: [+/-]
• [Ngày]: Công bố KQKD Q[X]
• [Ngày]: GDKHQ cổ tức [X đ/CP]

📊 TỔNG HỢP SENTIMENT
• Score: X/5 | Xu hướng: Tích cực/Tiêu cực/Trung tính
• Thị trường đã phản ánh: Có/Chưa/Một phần

📌 TÓM TẮT NHANH
[2–3 câu actionable về tin tức ảnh hưởng giá]
```

## Output `/news market`

```
📊 TIN THỊ TRƯỜNG HÔM NAY — [Ngày]
════════════════════════════════════

🏛️ VĨ MÔ:
• [Tin macro quan trọng nhất]

🏭 NGÀNH NÓNG:
• [Ngành được chú ý hôm nay]

💹 GIAO DỊCH ĐÁNG CHÚ Ý:
• [Cổ phiếu đột biến volume/giá]

⚡ SỰ KIỆN SẮP TỚI (7 ngày):
• [List events]
```

## Lưu ý

- Ưu tiên tin từ nguồn chính thức (SSC, sàn) trước tin tổng hợp
- Phân biệt tin đã biết (priced in) và tin bất ngờ (chưa priced in)
- Insider trading phổ biến ở TTCK VN — giá thường move trước tin

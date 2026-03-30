---
description: Tạo báo cáo thị trường chứng khoán Việt Nam — tổng kết phiên, tuần, tháng
---

# /report — Báo cáo Thị trường

## Cú pháp
```
/report                     # Tổng kết phiên giao dịch hôm nay
/report daily               # Báo cáo ngày (mặc định)
/report weekly              # Báo cáo tuần
/report monthly             # Báo cáo tháng
/report <SYMBOL>            # Báo cáo riêng cho một mã
/report portfolio           # Báo cáo hiệu suất danh mục
```

## Output `/report daily`

```
📋 BÁO CÁO PHIÊN GIAO DỊCH — [Thứ X, DD/MM/YYYY]
════════════════════════════════════════════════════

📊 CHỈ SỐ CHÍNH:
┌──────────┬──────────┬──────────┬──────────┐
│ Index    │ Đóng cửa │ Thay đổi │ Volume   │
├──────────┼──────────┼──────────┼──────────┤
│ VN-Index │ 1,XXX.xx │ +/-X.xx  │ XX,XXX tỷ│
│ VN30     │ 1,XXX.xx │ +/-X.xx  │ XX,XXX tỷ│
│ HNX-Index│ XXX.xx   │ +/-X.xx  │ X,XXX tỷ │
│ UPCOM    │ XXX.xx   │ +/-X.xx  │ X,XXX tỷ │
└──────────┴──────────┴──────────┴──────────┘

🌊 THANH KHOẢN
• HOSE: X,XXX tỷ (TB 20 phiên: X,XXX tỷ)
• Khối ngoại: MUA X,XXX tỷ / BÁN X,XXX tỷ → [Mua/Bán] ròng X,XXX tỷ

🏆 TOP TĂNG MẠNH (HOSE):
• XXX: +X.x% | Volume: X,XXX tỷ
• YYY: +X.x% | Volume: X,XXX tỷ

📉 TOP GIẢM MẠNH (HOSE):
• AAA: -X.x% | Volume: X,XXX tỷ

💹 ĐỘT BIẾN VOLUME:
• XXX: +XXX% volume vs TB 20 phiên

🔥 NGÀNH TĂNG MẠNH: [list]
❄️ NGÀNH GIẢM MẠNH: [list]

🌐 TIN TỨC ẢNH HƯỞNG HÔM NAY:
• [Tin quan trọng 1]
• [Tin quan trọng 2]

📌 NHẬN XÉT PHIÊN
[2–3 câu tổng kết xu hướng, dòng tiền, và điểm đáng chú ý]

📅 NGÀY GIAO DỊCH TIẾP THEO: [Ngày]
⚡ SỰ KIỆN CẦN THEO DÕI: [list]
```

## Output `/report weekly`

Thêm:
- Hiệu suất VN-Index 5 phiên
- Ngành dẫn dắt tuần
- Phân tích dòng tiền khối ngoại cả tuần
- Outlook tuần tới

## Output `/report portfolio`

Kết hợp với danh mục đã lưu — so sánh từng mã vs VN-Index trong kỳ báo cáo.

## Lưu ý

- **ATO (9:00–9:15):** Lệnh khớp theo giá ATO — không có trong intraday chart bình thường
- **Nghỉ lễ:** Thị trường nghỉ các ngày lễ VN — kiểm tra lịch giao dịch
- **Phiên chiều (13:00–14:30):** Volume thường thấp hơn phiên sáng
- **ATC (14:30–14:45):** Volume cuối phiên tăng đột biến là bình thường

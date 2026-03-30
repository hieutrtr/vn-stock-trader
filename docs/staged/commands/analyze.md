---
description: Phân tích toàn diện một mã cổ phiếu VN — TA + FA + News kết hợp
---

# /analyze — Phân tích Toàn diện Cổ phiếu

## Cú pháp
```
/analyze <SYMBOL>
/analyze <SYMBOL> --mode ta          # Chỉ Technical Analysis
/analyze <SYMBOL> --mode fa          # Chỉ Fundamental Analysis
/analyze <SYMBOL> --mode full        # TA + FA + News (mặc định)
/analyze <SYMBOL> --timeframe short  # Ngắn hạn (< 1 tháng)
/analyze <SYMBOL> --timeframe mid    # Trung hạn (1–3 tháng)
/analyze <SYMBOL> --timeframe long   # Dài hạn (> 3 tháng)
```

## Ví dụ
```
/analyze VCB
/analyze HPG --mode ta
/analyze FPT --mode full --timeframe long
```

## Quy trình thực thi

1. **Validate symbol** — kiểm tra mã hợp lệ, đang niêm yết
2. **Thu thập dữ liệu** — giá, volume, BCTC, tin tức
3. **Chạy TA skill** — xu hướng, chỉ báo kỹ thuật, tín hiệu
4. **Chạy FA skill** (nếu `--mode fa` hoặc `full`) — định giá, tài chính
5. **Chạy News skill** — tin tức 7 ngày, sự kiện sắp tới
6. **Tổng hợp** — kết luận thống nhất TA + FA + sentiment

## Output

### Quick Summary (mặc định)
```
🎯 [SYMBOL] — [TÊN CÔNG TY]
Giá: XX,XXX đ | Sàn: HOSE/HNX/UPCOM | Ngành: [sector]

📊 KỸ THUẬT: 🟢/🟡/🔴 [MUA/CHỜ/BÁN]
• Xu hướng: [Uptrend/Downtrend/Sideways]
• Tín hiệu: [tóm tắt 1 câu]
• Vào: [price] | SL: [price] | TP1: [price] | TP2: [price]

💰 CƠ BẢN: 🟢/🟡/🔴 [Rẻ/Hợp lý/Đắt]
• P/E: Xx | ROE: X.x% | Target: XX,XXX đ (+X%)

📰 TIN TỨC: 🟢/🟡/🔴
• [1 dòng tóm tắt tin quan trọng nhất]

📌 KHUYẾN NGHỊ: [MUA/GIỮ/BÁN]
```

## Lưu ý quan trọng

- Phân tích **chỉ mang tính tham khảo**, không phải tư vấn đầu tư
- Luôn kiểm tra thanh khoản trước khi quyết định
- T+2: Mua hôm nay bán được sau 2 phiên giao dịch

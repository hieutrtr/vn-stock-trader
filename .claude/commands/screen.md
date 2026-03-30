---
description: Lọc cổ phiếu VN theo tiêu chí — nhanh chóng tìm cơ hội đầu tư
---

# /screen — Stock Screener

## Cú pháp
```
/screen                              # Dùng preset Growth+Quality
/screen <strategy>                   # Dùng preset strategy
/screen <criteria>                   # Tiêu chí tuỳ chỉnh
```

## Preset Strategies
```
/screen growth      # ROE>15%, EPS tăng>15%, D/E<1
/screen value       # P/E<12, P/B<1.5, Dividend>3%
/screen momentum    # Giá>MA20>MA50, RSI 50–65, Volume tăng
/screen dividend    # Dividend>5%, 3+ năm trả cổ tức
/screen recovery    # Giảm>30% từ đỉnh, RSI<40, ROE>10%
```

## Tiêu chí tuỳ chỉnh
```
/screen pe<15 roe>15
/screen pe<12 pb<1.5 market_cap>2000b exchange=HOSE
/screen sector=banking roe>15 npL<2
/screen dividend>4% market_cap>1000b
```

## Parameters hỗ trợ

| Parameter | Ví dụ | Mô tả |
|-----------|-------|-------|
| pe | pe<15 | P/E nhỏ hơn 15 |
| pb | pb<2 | P/B nhỏ hơn 2 |
| roe | roe>15 | ROE lớn hơn 15% |
| eps_growth | eps_growth>20 | EPS YoY tăng >20% |
| dividend | dividend>3 | Cổ tức >3% |
| market_cap | market_cap>1000b | Vốn hoá >1,000 tỷ |
| volume | volume>1b | Volume >1 tỷ/ngày |
| rsi | rsi<40 | RSI < 40 |
| sector | sector=banking | Lọc theo ngành |
| exchange | exchange=HOSE | Chỉ HOSE/HNX/UPCOM |

## Output

```
🔍 SCREENER: [strategy/criteria]
Tìm thấy X mã | Sàn: ALL | Cập nhật: HH:MM

TOP 10 KẾT QUẢ:
1. XXX — [Ngành] — P/E Xx | ROE X.x% | Score: XX/100
2. YYY — ...
...

💡 TOP 3 HIGHLIGHTS:
• XXX: [lý do nổi bật]
...

Dùng /analyze [symbol] để phân tích chi tiết
```

## Lưu ý

- Kết quả screener là **điểm khởi đầu**, không phải tín hiệu mua
- Luôn verify thanh khoản: `volume > 500 triệu/ngày` trước khi vào lệnh
- Screener không lọc được: tin xấu chưa public, rủi ro quản trị, accounting fraud

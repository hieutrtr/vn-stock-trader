---
description: So sánh 2 cổ phiếu VN đầu tư nên chọn cái nào — side-by-side analysis
---

# /compare — So sánh 2 Cổ phiếu

## Cú pháp
```
/compare <SYMBOL1> <SYMBOL2>
/compare <SYMBOL1> <SYMBOL2> --mode ta     # Chỉ kỹ thuật
/compare <SYMBOL1> <SYMBOL2> --mode fa     # Chỉ cơ bản
/compare <SYMBOL1> <SYMBOL2> --mode full   # Toàn diện (mặc định)
```

## Ví dụ
```
/compare VCB TCB
/compare HPG HSG --mode fa
/compare FPT MWG
```

## Quy trình thực thi

1. Lấy dữ liệu song song cho cả hai mã
2. Chạy TA analysis cho cả hai
3. Chạy FA analysis cho cả hai
4. So sánh head-to-head từng metric
5. Cho điểm tổng hợp và khuyến nghị

## Output

```
⚖️ SO SÁNH: [SYMBOL1] vs [SYMBOL2]
════════════════════════════════════

📊 THÔNG TIN CHUNG:
┌─────────────────┬──────────────┬──────────────┐
│ Chỉ tiêu        │ [SYMBOL1]    │ [SYMBOL2]    │
├─────────────────┼──────────────┼──────────────┤
│ Ngành           │ Ngân hàng    │ Ngân hàng    │
│ Vốn hoá (tỷ đ)  │ 120,000      │ 85,000       │
│ Giá hiện tại    │ 92,000 đ     │ 45,000 đ     │
│ Sàn             │ HOSE         │ HOSE         │
└─────────────────┴──────────────┴──────────────┘

💰 ĐỊNH GIÁ:
┌─────────────────┬──────────────┬──────────────┬──────────┐
│ Chỉ số          │ [SYMBOL1]    │ [SYMBOL2]    │ Tốt hơn  │
├─────────────────┼──────────────┼──────────────┼──────────┤
│ P/E             │ 15x          │ 9x           │ [SYM2] ✓ │
│ P/B             │ 3.2x         │ 1.8x         │ [SYM2] ✓ │
│ EV/EBITDA       │ 12x          │ 7x           │ [SYM2] ✓ │
│ Dividend Yield  │ 2.1%         │ 3.5%         │ [SYM2] ✓ │
└─────────────────┴──────────────┴──────────────┴──────────┘

📈 CHẤT LƯỢNG KINH DOANH:
┌─────────────────┬──────────────┬──────────────┬──────────┐
│ ROE             │ 20%          │ 18%          │ [SYM1] ✓ │
│ ROA             │ 1.8%         │ 1.5%         │ [SYM1] ✓ │
│ EPS tăng YoY    │ +22%         │ +15%         │ [SYM1] ✓ │
│ Doanh thu tăng  │ +18%         │ +12%         │ [SYM1] ✓ │
└─────────────────┴──────────────┴──────────────┴──────────┘

🔧 KỸ THUẬT:
┌─────────────────┬──────────────┬──────────────┬──────────┐
│ Trend           │ Uptrend      │ Sideways     │ [SYM1] ✓ │
│ RSI             │ 58           │ 45           │ [SYM1] ✓ │
│ vs MA50         │ +8%          │ +1%          │ [SYM1] ✓ │
└─────────────────┴──────────────┴──────────────┴──────────┘

🏆 TỔNG ĐIỂM:
• [SYMBOL1]: XX/100 — [Định giá + Chất lượng + Kỹ thuật]
• [SYMBOL2]: XX/100 — [Định giá + Chất lượng + Kỹ thuật]

📌 KHUYẾN NGHỊ
→ Ưu tiên: [SYMBOL] vì [lý do chính]
→ Tuy nhiên: [SYMBOL kia] phù hợp nếu [điều kiện]

⚠️ Với ngân sách hữu hạn, nên chọn [SYMBOL] nếu:
• Chiến lược tăng trưởng → [SYMBOL1]
• Chiến lược value/dividend → [SYMBOL2]
```

## Lưu ý

- So sánh chỉ có ý nghĩa với **cổ phiếu cùng ngành** (không so P/E ngân hàng vs thép)
- Mỗi cổ phiếu có thể phù hợp với mục tiêu khác nhau — không có đáp án duy nhất

---
description: Đặt cảnh báo giá và điều kiện cho cổ phiếu Việt Nam
---

# /alert — Cảnh báo Cổ phiếu

## Cú pháp
```
/alert <SYMBOL> <condition>          # Đặt cảnh báo
/alert list                          # Xem danh sách cảnh báo
/alert delete <id>                   # Xoá cảnh báo
/alert clear                         # Xoá tất cả
```

## Loại điều kiện

### Cảnh báo giá
```
/alert VCB price > 95000             # Khi giá VCB vượt 95,000
/alert HPG price < 28000             # Khi giá HPG dưới 28,000
/alert FPT price = 130000            # Khi giá FPT đạt đúng 130,000
/alert MBB price cross 25000 up      # Khi giá cắt lên 25,000
/alert ACB price cross 22000 down    # Khi giá cắt xuống 22,000
```

### Cảnh báo kỹ thuật
```
/alert VNM rsi < 30                  # Khi RSI vào vùng oversold
/alert TCB rsi > 70                  # Khi RSI vào vùng overbought
/alert HPG ma_cross golden           # Golden Cross (MA20 cắt MA50 lên)
/alert SSI ma_cross death            # Death Cross (MA20 cắt MA50 xuống)
/alert VCB breakout 95000            # Breakout kháng cự 95,000
/alert HPG breakdown 28000           # Breakdown hỗ trợ 28,000
```

### Cảnh báo volume
```
/alert VHM volume > 3x               # Volume tăng hơn 3x trung bình
/alert FPT volume_spike              # Volume đột biến bất thường
```

### Cảnh báo % thay đổi
```
/alert BID change > 5%               # Tăng hơn 5% trong ngày
/alert NVL change < -5%              # Giảm hơn 5% trong ngày
/alert HPG change_week > 10%         # Tăng hơn 10% trong tuần
```

## Ví dụ thực tế

```
# Entry setup
/alert VCB price cross 92000 up      → "VCB breakout, xem xét vào"
/alert VCB rsi < 40                  → "VCB oversold, cơ hội mua"

# Stoploss monitor
/alert HPG price < 27300             → "HPG gần stoploss -3%"
/alert HPG price < 26600             → "HPG HIT STOPLOSS -5%"

# Take profit
/alert FPT price > 140000            → "FPT target TP1 đạt"
/alert FPT price > 155000            → "FPT target TP2 đạt"

# Anomaly detection
/alert SSI volume > 5x               → "SSI volume bất thường, kiểm tra tin"
```

## Output `/alert list`

```
🔔 DANH SÁCH CẢNH BÁO ĐANG THEO DÕI
════════════════════════════════════

ID  │ Mã    │ Điều kiện              │ Trạng thái
────┼───────┼────────────────────────┼───────────
001 │ VCB   │ Giá > 95,000           │ ⏳ Đang theo dõi (hiện: 92,000)
002 │ HPG   │ Giá < 26,600           │ ⏳ Đang theo dõi (hiện: 31,500)
003 │ FPT   │ RSI < 35               │ ⏳ Đang theo dõi (RSI hiện: 58)
004 │ SSI   │ Volume > 3x            │ ✅ ĐÃ KÍCH HOẠT lúc 13:45

Tổng: 4 cảnh báo (3 active, 1 triggered)
```

## Khi cảnh báo kích hoạt

```
⚡ CẢNH BÁO KÍCH HOẠT!
Mã: HPG | Điều kiện: Giá < 28,000
Giá hiện tại: 27,850 đ (lúc 14:23)

→ Dùng /analyze HPG để phân tích ngay
→ Kiểm tra tin tức: /news HPG
```

## Lưu ý

- Cảnh báo lưu **trong session** — khi thoát sẽ mất
- Kiểm tra cảnh báo bằng cách hỏi Claude: "check alerts" hoặc "có alert nào kích hoạt chưa?"
- Điều kiện kỹ thuật (RSI, MA) cần dữ liệu real-time để chính xác
- Tối đa 20 cảnh báo cùng lúc để tránh quá tải context

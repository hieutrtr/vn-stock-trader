---
description: Xem và đánh giá danh mục đầu tư — hiệu suất, phân bổ, và khuyến nghị
---

# /portfolio — Quản lý Danh mục

## Cú pháp
```
/portfolio                           # Đánh giá danh mục hiện tại
/portfolio add <SYMBOL> <shares> <price>   # Thêm vị thế
/portfolio remove <SYMBOL>           # Xoá vị thế
/portfolio update <SYMBOL> <shares> <price>  # Cập nhật vị thế
/portfolio show                      # Hiển thị danh mục
/portfolio review                    # Phân tích chi tiết (gọi portfolio-review skill)
/portfolio reset                     # Xoá toàn bộ danh mục
```

## Ví dụ
```
/portfolio add VCB 1000 85000
/portfolio add HPG 5000 28000
/portfolio add FPT 500 125000
/portfolio review
```

## Nhập danh mục nhiều mã cùng lúc
```
/portfolio add batch:
VCB 1000 85000
HPG 5000 28000
FPT 500 125000
MBB 2000 22000
```

## Output `/portfolio show`

```
💼 DANH MỤC CỦA BẠN
════════════════════════════════════

┌────────┬────────┬──────────┬────────────┬──────────┬────────┐
│ Mã     │ KL     │ Giá mua  │ Giá hiện tại│ Lãi/Lỗ   │ % NAV  │
├────────┼────────┼──────────┼────────────┼──────────┼────────┤
│ VCB    │ 1,000  │ 85,000   │ 92,000     │ +8.2%    │ 30.7%  │
│ HPG    │ 5,000  │ 28,000   │ 31,500     │ +12.5%   │ 52.5%  │
│ FPT    │ 500    │ 125,000  │ 138,000    │ +10.4%   │ 16.8%  │
└────────┴────────┴──────────┴────────────┴──────────┴────────┘

📊 TỔNG KẾT
• Tổng NAV: 299,750,000 đ
• Vốn đầu tư: 272,500,000 đ
• Lãi/Lỗ: +27,250,000 đ (+10.0%)
• vs VN-Index: +3.5% alpha

Dùng /portfolio review để phân tích chi tiết
```

## Output `/portfolio review`

Gọi skill `portfolio-review` đầy đủ — xem skill đó để biết format chi tiết.

## Lưu ý

- Danh mục lưu trong session — dùng `/portfolio show` để xem lại
- Giá cổ phiếu cập nhật **real-time** khi bạn dùng lệnh
- Lãi/lỗ là **unrealized** (chưa bán)
- Thuế 0.1%/lệnh bán chưa được tính vào P&L

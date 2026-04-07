---
name: news-update
description: Thu thập tin tức mới từ CafeF/Vietstock/VNExpress, deduplicate với archive, chỉ hiển thị tin chưa từng thấy. Dùng khi user muốn cập nhật tin tức mới nhất mà không bị lặp lại tin cũ.
argument-hint: "[SYMBOL]"
allowed-tools: Bash
---

# Skill: News Update — Tin tức mới (không trùng lặp)

## Cách chạy

Chạy 1 lệnh duy nhất:

```
Bash("cd /home/hieutran/projects/tam/stock-trader && python3 scripts/news_update.py")
```

Nếu có SYMBOL (lọc tin theo mã):

```
Bash("cd /home/hieutran/projects/tam/stock-trader && python3 scripts/news_update.py VNM")
```

## Script tự động thực hiện

1. Đọc `data/news_archive.json` (tạo mới nếu chưa có)
2. Fetch tin từ CafeF, Vietstock, VNExpress qua scraper trực tiếp
3. Dedup: so sánh `title.lower().strip()` với archive + intra-batch dedup
4. Append tin mới vào archive, giữ max 2000 bài
5. Ghi lại archive
6. Output ra stdout theo format chuẩn

## Format đầu ra

⚠️ KHÔNG dùng markdown link `[text](url)` — Telegram không render được.
PHẢI có plain text URL cho mỗi tin (paste URL trực tiếp, không wrap trong markdown).

```
📰 NEWS UPDATE
🆕 {N} tin mới  |  📦 Archive: {total} bài

• Tóm tắt ngắn 1 câu
  https://example.com/article/123 (Nguồn)
• Tóm tắt ngắn 1 câu
  https://example.com/article/456 (Nguồn)
...

✅ Không có tin mới — tất cả đã đọc.     ← khi N = 0
... và {N-15} tin khác đã lưu vào archive.  ← khi N > 15
```

## Xử lý lỗi

- `data/news_archive.json` không tồn tại → tạo mới với `[]`
- Deps chưa cài → script tự dùng venv của vn-stock-trader (`.venv/bin/python3`)
- Source lỗi → bỏ qua source đó, tiếp tục các source còn lại

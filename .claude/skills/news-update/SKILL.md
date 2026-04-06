---
name: news-update
description: Thu thập tin tức mới từ CafeF/Vietstock/VNExpress, deduplicate với archive, chỉ hiển thị tin chưa từng thấy. Dùng khi user muốn cập nhật tin tức mới nhất mà không bị lặp lại tin cũ.
argument-hint: "[SYMBOL]"
allowed-tools: mcp__vn-stock-trader__get_news, WebSearch, WebFetch, Bash, Read, Write
---

# Skill: News Update — Tin tức mới (không trùng lặp)

## Mục tiêu
Thu thập tin tức từ nhiều nguồn, so sánh với archive đã lưu, **chỉ hiển thị tin MỚI chưa từng thấy**. Tránh noise từ tin cũ lặp lại.

## Tham số
- `[SYMBOL]` (optional): Lọc tin theo mã cổ phiếu cụ thể (VD: `VNM`, `HPG`). Nếu không có, lấy tin thị trường tổng hợp.

## Quy trình thực hiện

### Bước 1 — Đọc archive hiện tại

```
Read("data/news_archive.json")
```

- Nếu file không tồn tại hoặc lỗi → coi archive là `[]`, tất cả tin sẽ là mới
- Parse JSON thành danh sách các object `{url, title, title_hash, summary, source, published_at, fetched_at, symbols}`
- Build lookup set: tập hợp tất cả `url` và `title_hash` đã có trong archive

**Tính title_hash:** dùng Bash để hash title (lowercase, strip whitespace):
```bash
echo -n "tiêu đề bài viết" | tr '[:upper:]' '[:lower:]' | tr -s ' ' | md5sum | cut -d' ' -f1
```

### Bước 2 — Thu thập tin tức

**Nếu có SYMBOL:**
```
mcp__vn-stock-trader__get_news(symbol=SYMBOL, limit=20)   → tin liên quan mã
mcp__vn-stock-trader__get_news(limit=30)                   → tin thị trường chung
WebSearch("site:cafef.vn {SYMBOL} tin tức mới nhất")
WebSearch("site:vietstock.vn {SYMBOL}")
```

**Nếu không có SYMBOL (tin thị trường tổng hợp):**
```
mcp__vn-stock-trader__get_news(limit=50)                   → tin thị trường
WebSearch("site:cafef.vn chứng khoán tin tức mới nhất")
WebSearch("site:vietstock.vn thị trường chứng khoán")
WebSearch("site:vnexpress.net chứng khoán")
```

> Với mỗi kết quả WebSearch có URL quan trọng, dùng `WebFetch(url)` để lấy nội dung đầy đủ nếu cần.

### Bước 3 — Chuẩn hoá và deduplicate

Với mỗi bài tin thu thập được, tạo object chuẩn:
```json
{
  "url": "https://...",
  "title": "Tiêu đề bài viết",
  "title_hash": "<md5 của title lowercase trimmed>",
  "summary": "Tóm tắt 1-2 câu nội dung chính",
  "source": "cafef|vietstock|vnexpress|mcp",
  "published_at": "2026-04-06T09:00:00",
  "fetched_at": "<ISO timestamp hiện tại>",
  "symbols": ["VNM", "HPG"]
}
```

**Kiểm tra trùng lặp — bài tin là MỚI nếu:**
- `url` KHÔNG có trong lookup set, VÀ
- `title_hash` KHÔNG có trong lookup set

Nếu cả hai điều kiện thỏa → bài tin mới, thêm vào danh sách `new_items`.

### Bước 4 — Cập nhật archive

```
Write("data/news_archive.json", JSON.stringify(archive + new_items, null, 2))
```

- Append `new_items` vào cuối archive hiện tại
- Giữ tối đa **2000 bài** gần nhất (xóa bài cũ nhất nếu vượt quá) để tránh file quá lớn
- Ghi lại toàn bộ file

### Bước 5 — Output

Hiển thị **chỉ các tin MỚI** theo format dưới đây. Nếu không có tin mới, thông báo rõ.

## Format đầu ra

```
📰 NEWS UPDATE{" — " + SYMBOL nếu có}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆕 {N} tin mới  |  📦 Tổng archive: {tổng số bài}

{Nếu N = 0:}
✅ Không có tin mới — tất cả đã được đọc trước đó.

{Nếu N > 0:}
1. [{SYMBOL nếu liên quan}] {Tiêu đề}
   📌 {Tóm tắt 1-2 câu}
   🔗 {Source} | {published_at}

2. ...

{Nếu > 10 tin mới:}
... và {N-10} tin khác đã lưu vào archive.
```

## Xử lý lỗi

| Tình huống | Xử lý |
|-----------|-------|
| `data/news_archive.json` không tồn tại | Tạo mới với `[]`, coi tất cả là mới |
| MCP tool lỗi | Bỏ qua, tiếp tục với WebSearch |
| URL không fetch được | Dùng title + snippet từ search result |
| JSON parse error | Backup file cũ, tạo archive mới |

## Lưu ý

- **Deduplication:** Ưu tiên `url` exact match. `title_hash` là fallback cho tin cùng nội dung khác URL (VD: syndicated content).
- **`fetched_at`** luôn là thời điểm hiện tại (không phải published_at của bài).
- **`symbols`** là danh sách mã cổ phiếu đề cập trong bài — extract từ nội dung nếu có thể.
- Khi chạy với SYMBOL cụ thể: vẫn fetch tin thị trường chung, nhưng ưu tiên hiển thị tin liên quan SYMBOL đó trước.
- **Nguồn tin đáng tin cậy:** CafeF, VietStock, VNExpress, NDH, HOSE/HNX official.

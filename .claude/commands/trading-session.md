# /trading-session — Khởi động phiên giao dịch

Start a full trading session with automated monitoring loops.

## What this does:

1. Run `/morning-brief` immediately for pre-market overview
2. Start monitoring loops:
   - `/loop 5m /portfolio-monitor` — check portfolio every 5 minutes
   - `/loop 5m /watchlist-check` — check watchlist alerts every 5 minutes
   - `/loop 30m /news` — check news every 30 minutes
3. When user says "kết thúc phiên" or after 14:45, run `/session-summary`

## Usage

```
/trading-session           # start with defaults
/trading-session quick     # skip morning brief, just start loops
```

## Session Flow

```
/trading-session
  → /morning-brief (immediate)
  → /loop 5m /portfolio-monitor
  → /loop 5m /watchlist-check
  → /loop 30m check tin tức mới ảnh hưởng danh mục
  → ... trading session active ...
  → "kết thúc phiên" or 14:45
  → /session-summary
```

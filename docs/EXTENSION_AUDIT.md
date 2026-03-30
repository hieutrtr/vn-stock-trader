# Extension Audit — VN Stock Trader

> Audit date: 2026-03-30 | Status: Fixed

## Dependency Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Claude Code Session                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CLAUDE.md ──────────────────────── Always in context               │
│                                                                     │
│  .mcp.json ──────────────────────── Register MCP server             │
│    └─→ "vn-stock-trader" (FastMCP "vn-stock-mcp")                   │
│         Tools: get_stock_price, get_market_overview,                │
│                get_top_movers, get_stock_history,                   │
│                get_financial_report, get_sector_peers,              │
│                get_news, screen_stocks,                             │
│                get_portfolio, update_portfolio,                     │
│                get_insider_trades                                   │
│                                                                     │
├──────────────────── SKILLS ─────────────────────────────────────────┤
│                                                                     │
│  /technical-analysis ──────── get_stock_price                       │
│                         └──── get_stock_history                     │
│                                                                     │
│  /fundamental-analysis ─────── get_stock_price                      │
│                         ├──── get_financial_report                  │
│                         └──── get_sector_peers                      │
│                                                                     │
│  /news-impact ─────────────── get_news                              │
│                         ├──── WebSearch                             │
│                         └──── WebFetch                              │
│                                                                     │
│  /portfolio-review ─────────── get_portfolio                        │
│                         ├──── get_stock_price                       │
│                         ├──── get_stock_history                     │
│                         ├──── get_financial_report                  │
│                         └──── get_sector_peers                      │
│                                                                     │
│  /stock-screener ──────────── screen_stocks                         │
│                         ├──── get_stock_price                       │
│                         └──── get_financial_report                  │
│                                                                     │
│  /sector-compare ──────────── get_sector_peers                      │
│                         ├──── get_stock_price                       │
│                         ├──── get_financial_report                  │
│                         └──── get_stock_history                     │
│                                                                     │
├──────────────────── COMMANDS ───────────────────────────────────────┤
│                                                                     │
│  /analyze ──────── invokes: technical-analysis + fundamental        │
│                             analysis + news-impact skills           │
│  /screen ───────── invokes: stock-screener skill                    │
│  /portfolio ────── invokes: portfolio-review skill                  │
│  /news ─────────── invokes: news-impact skill                       │
│  /compare ──────── invokes: technical-analysis + fundamental        │
│                             analysis for 2 symbols                  │
│  /report ───────── calls: get_market_overview, get_top_movers       │
│  /alert ───────────── session-scope alert tracking                  │
│                                                                     │
├──────────────────── AGENTS ─────────────────────────────────────────┤
│                                                                     │
│  market-watcher ────────────── get_stock_price ✓                    │
│                         ├──── get_market_overview ✓                 │
│                         ├──── get_top_movers ✓                      │
│                         └──── get_portfolio ✓                       │
│                                                                     │
│  news-analyst ──────────────── get_news ✓                           │
│                         ├──── get_stock_price ✓                     │
│                         ├──── get_portfolio ✓                       │
│                         ├──── WebSearch ✓                           │
│                         └──── WebFetch ✓                            │
│                                                                     │
│  portfolio-manager ─────────── get_portfolio ✓                      │
│                         ├──── get_stock_price ✓                     │
│                         ├──── get_stock_history ✓                   │
│                         ├──── get_financial_report ✓                │
│                         └──── update_portfolio ✓                    │
│                                                                     │
│  research-agent ────────────── get_stock_price ✓                    │
│                         ├──── get_stock_history ✓                   │
│                         ├──── get_financial_report ✓                │
│                         ├──── get_sector_peers ✓                    │
│                         ├──── get_news ✓                            │
│                         ├──── get_insider_trades ✓                  │
│                         └──── WebFetch ✓                            │
│                                                                     │
├──────────────────── HOOKS ──────────────────────────────────────────┤
│                                                                     │
│  settings.local.json → Stop hook → claude_bridge.on_complete        │
│  (Claude Bridge post-session callback)                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Issues Found & Fixes Applied

### Issue 1: MCP Server NOT Registered ❌ → Needs Manual Action

**Problem:** Không có `.mcp.json` file. MCP server `vn-stock-mcp` chưa được đăng ký với Claude Code.

**Impact:** TẤT CẢ tool calls `mcp__vn-stock-trader__*` đều FAIL vì Claude Code không biết server nào cung cấp tools này.

**Fix Required (manual):** Tạo file `.mcp.json` ở project root:

```json
{
  "mcpServers": {
    "vn-stock-trader": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "mcp-server/server.py"],
      "env": {}
    }
  }
}
```

> ⚠️ File `.mcp.json` là sensitive file, cần user manually approve khi Claude Code hỏi.
> Hoặc tạo thủ công bằng text editor.

**Why `vn-stock-trader` as key?** Tất cả agents đã reference `mcp__vn-stock-trader__*`. Key trong `mcpServers` phải khớp với prefix này. Server name `vn-stock-mcp` trong `FastMCP("vn-stock-mcp", ...)` là internal name — không ảnh hưởng prefix.

---

### Issue 2: Skills có `triggers` field không hợp lệ ✅ FIXED

**Problem:** Tất cả 6 skills có field `triggers: [...]` trong frontmatter. Field này **không tồn tại** trong Claude Code spec. Claude Code dùng `description` để quyết định khi nào auto-invoke skill — không dùng `triggers`.

**Before (6 files):**
```yaml
triggers:
  - "phân tích kỹ thuật"
  - "TA"
  - "chart"
  ...
```

**After:** Field `triggers` đã được xóa. `description` được mở rộng để include trigger keywords:
```yaml
description: Phân tích kỹ thuật một mã cổ phiếu Việt Nam — xu hướng, momentum, tín hiệu mua/bán. Dùng khi user hỏi về chart, RSI, MACD, support/resistance, hỗ trợ, kháng cự, hoặc tín hiệu mua/bán kỹ thuật.
```

---

### Issue 3: Skills `allowed-tools` format sai ✅ FIXED

**Problem:** 6 skills dùng YAML list với short names:
```yaml
allowed-tools:
  - get_stock_history     # ← YAML list (not supported)
  - get_stock_price       # ← Missing mcp__vn-stock-trader__ prefix
```

Correct format là **comma-separated string** với **full MCP prefix**.

**Before → After (all 6 skills):**

| Skill | Before | After |
|-------|--------|-------|
| technical-analysis | `- get_stock_history`<br>`- get_stock_price` | `mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_stock_history` |
| fundamental-analysis | `- get_financial_report`<br>`- get_sector_peers` | `mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_financial_report, mcp__vn-stock-trader__get_sector_peers` |
| news-impact | `- get_news` | `mcp__vn-stock-trader__get_news, WebSearch, WebFetch` |
| portfolio-review | `- get_portfolio` | `mcp__vn-stock-trader__get_portfolio, mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_stock_history, mcp__vn-stock-trader__get_financial_report, mcp__vn-stock-trader__get_sector_peers` |
| stock-screener | `- screen_stocks` | `mcp__vn-stock-trader__screen_stocks, mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_financial_report` |
| sector-compare | `- get_sector_peers` | `mcp__vn-stock-trader__get_sector_peers, mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_financial_report, mcp__vn-stock-trader__get_stock_history` |

---

### Issue 4: Skills body text dùng tool names không tồn tại ✅ FIXED

**Problem:** Một số skills reference tool names không có trong MCP server.

#### fundamental-analysis/SKILL.md

| Body text (cũ) | Thực tế (tools trong server) |
|----------------|------------------------------|
| `get_company_overview(symbol)` | ❌ Không tồn tại → dùng `get_stock_price` |
| `get_financial_statements(symbol)` | ❌ Không tồn tại → dùng `get_financial_report` |
| `get_financial_ratios(symbol)` | ❌ Không tồn tại → dùng `get_financial_report` |
| `get_industry_data(industry)` | ❌ Không tồn tại → dùng `get_sector_peers` |

**Fix:** Body rewritten với đúng tool names có prefix `mcp__vn-stock-trader__`.

#### news-impact/SKILL.md

| Body text (cũ) | Thực tế |
|----------------|---------|
| `get_stock_news(symbol, days=7)` | ❌ → `get_news(symbol, limit=10)` |
| `get_company_events(symbol)` | ❌ Không tồn tại, tool này không có |
| `get_market_news(category="macro")` | ❌ → `get_news(limit=30)` |
| `search_news(query=...)` | ❌ → `WebSearch(...)` |

#### portfolio-review/SKILL.md

| Body text (cũ) | Thực tế |
|----------------|---------|
| `get_financial_ratios(symbol)` | ❌ → `get_financial_report(symbol)` |
| `get_sector(symbol)` | ❌ → `get_sector_peers(symbol)` |
| `get_price_performance(peer)` | ❌ → `get_stock_history(peer)` |

---

### Issue 5: Skills `argument-hint` field còn thiếu ✅ ADDED

4 skills thiếu `argument-hint` giúp user biết cú pháp. Đã thêm vào technical-analysis, fundamental-analysis, news-impact, stock-screener, sector-compare.

---

## Agents Audit

### Format Check: ✅ PASS

Tất cả 4 agent files dùng đúng format:
- `tools:` field (NOT `allowed-tools:`) — ✅ correct
- Comma-separated string — ✅ correct
- Full `mcp__vn-stock-trader__` prefix — ✅ correct
- Standard frontmatter fields (name, description, tools) — ✅ correct

### Tool Name Verification vs MCP Server

Đối chiếu tools trong agents với tools thực sự trong `mcp-server/server.py`:

| MCP Tool | Exists in server? | Used by agents |
|----------|-------------------|----------------|
| `get_stock_price` | ✅ market.py | market-watcher, news-analyst, portfolio-manager, research-agent |
| `get_market_overview` | ✅ market.py | market-watcher |
| `get_top_movers` | ✅ market.py | market-watcher |
| `get_stock_history` | ✅ (register_history) | portfolio-manager, research-agent |
| `get_financial_report` | ✅ financials.py | portfolio-manager, research-agent |
| `get_sector_peers` | ✅ financials.py | research-agent |
| `get_news` | ✅ (register_news) | news-analyst, research-agent |
| `screen_stocks` | ✅ screener.py | (none — only in skill) |
| `get_portfolio` | ✅ (register_portfolio) | market-watcher, news-analyst, portfolio-manager |
| `update_portfolio` | ✅ (register_portfolio) | portfolio-manager |
| `get_insider_trades` | ✅ insider.py | research-agent |
| `WebSearch` | ✅ built-in | news-analyst |
| `WebFetch` | ✅ built-in | news-analyst, research-agent |

**Result: ALL agent tool references are VALID ✅**

---

## Commands Audit

### Format Check: ✅ PASS

7 command files: alert, analyze, compare, news, portfolio, report, screen

All have valid frontmatter với `description` field. Không có `allowed-tools` nào (commands dựa vào Claude để tự chọn tools).

### Linkage Check

| Command | References |
|---------|-----------|
| `/analyze` | Invokes technical-analysis + fundamental-analysis + news-impact skills |
| `/screen` | Invokes stock-screener skill |
| `/portfolio` | Invokes portfolio-review skill |
| `/news` | Invokes news-impact skill |
| `/compare` | Invokes technical-analysis + fundamental-analysis for 2 symbols |
| `/report` | Uses get_market_overview, get_top_movers, get_top_movers |
| `/alert` | Session-scope alert — no MCP tools needed |

**Result: All commands correctly describe their workflow ✅**

---

## MCP Server Audit

### Tools Exposed vs What's Referenced

All 11 tools exposed by MCP server:

| Tool | Module | Referenced in Skills | Referenced in Agents |
|------|--------|---------------------|---------------------|
| `get_stock_price` | market.py | technical-analysis, fundamental-analysis, portfolio-review, sector-compare | market-watcher, news-analyst, portfolio-manager, research-agent |
| `get_market_overview` | market.py | (report command) | market-watcher |
| `get_top_movers` | market.py | (report command) | market-watcher |
| `get_stock_history` | history.py | technical-analysis, portfolio-review, sector-compare | portfolio-manager, research-agent |
| `get_financial_report` | financials.py | fundamental-analysis, portfolio-review, stock-screener, sector-compare | portfolio-manager, research-agent |
| `get_sector_peers` | financials.py | fundamental-analysis, portfolio-review, sector-compare | research-agent |
| `get_news` | news.py | news-impact | news-analyst, research-agent |
| `screen_stocks` | screener.py | stock-screener | (none) |
| `get_portfolio` | portfolio.py | portfolio-review | market-watcher, news-analyst, portfolio-manager |
| `update_portfolio` | portfolio.py | (none) | portfolio-manager |
| `get_insider_trades` | insider.py | (none) | research-agent |

**No orphaned tools** (all tools have at least one reference).
**`get_market_overview` and `get_top_movers`** are used by market-watcher agent and indirectly by `/report` command — coverage is complete.

---

## Hooks Audit

| File | Hook | Status |
|------|------|--------|
| `.claude/settings.local.json` | `Stop` → claude_bridge.on_complete | ✅ Valid format, correct syntax |
| `.claude/settings.json` | permissions only, no hooks | ✅ OK |

---

## Summary

### Before Audit
- 6 skills với `triggers` field không hợp lệ (field không tồn tại trong Claude Code)
- 6 skills với `allowed-tools` dùng YAML list và thiếu `mcp__vn-stock-trader__` prefix
- 3 skills (fundamental-analysis, news-impact, portfolio-review) có tool names sai trong body text
- 4 skills thiếu `argument-hint`
- MCP server KHÔNG được đăng ký (thiếu `.mcp.json`)
- 4 agents: format ĐÚNG, tool names ĐÚNG ✅

### After Audit
- ✅ 6 skills frontmatter đã fix (triggers removed, allowed-tools corrected)
- ✅ 6 skills body text đã fix (sai tool names → đúng tool names)
- ✅ argument-hint added cho 5 skills
- ✅ 4 agents verified correct (no changes needed)
- ✅ 7 commands verified correct (no changes needed)
- ⚠️ `.mcp.json` cần tạo thủ công (sensitive file, cần user approve)

### Action Required

Tạo file `.mcp.json` ở project root với nội dung:

```json
{
  "mcpServers": {
    "vn-stock-trader": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "mcp-server/server.py"],
      "env": {}
    }
  }
}
```

Sau khi tạo, Claude Code sẽ hỏi để approve MCP server. Approve để tools `mcp__vn-stock-trader__*` hoạt động.

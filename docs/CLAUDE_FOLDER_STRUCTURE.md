# Claude Code — Cấu trúc .claude/ Folder

> Tài liệu này tóm tắt cách Claude Code tổ chức cấu hình, skills, commands, agents.
> Research date: 2026-03-30

---

## 1. Hai tầng cấu hình: Project vs Global

| Tầng | Đường dẫn | Chia sẻ? | Ưu tiên |
|------|-----------|---------|---------|
| **Managed** (IT) | System-level | Tất cả users | 1 (cao nhất) |
| **Global/User** | `~/.claude/` | Chỉ bạn, mọi project | 2 |
| **Project** | `.claude/` trong repo | Team qua git | 3 |
| **Local** | `.claude/settings.local.json` | Chỉ bạn, project này | 4 (thấp nhất khi merge) |

> **Quan trọng:** Specific hơn = override, KHÔNG phải lower priority = bị bỏ qua.
> Arrays (permissions, MCP) **merge** giữa các tầng. Objects **override**.

---

## 2. Skills

### Vị trí
```
~/.claude/skills/         # Global — dùng cho mọi project
.claude/skills/           # Project — chỉ project này (git-tracked)
```

### Format (2 cách — cả hai đều hoạt động)

**Cách 1: Flat file** (đơn giản, project này dùng)
```
.claude/skills/
├── technical-analysis.md
├── fundamental-analysis.md
└── stock-screener.md
```

**Cách 2: Directory với SKILL.md** (phức tạp hơn, có thể kèm scripts)
```
.claude/skills/
└── technical-analysis/
    ├── SKILL.md          # Bắt buộc
    ├── template.md       # Tuỳ chọn
    └── scripts/
        └── calc_ta.py    # Tuỳ chọn
```

### Frontmatter
```yaml
---
name: skill-name               # lowercase, hyphens
description: "Khi nào dùng"   # Claude đọc để quyết định invoke
triggers:                       # Keywords trigger tự động
  - "keyword 1"
  - "keyword 2"
allowed-tools: Read, Bash      # Tuỳ chọn — giới hạn tools
model: sonnet                  # Tuỳ chọn — override model
---
```

### Priority
- Project skills (`.claude/skills/`) **override** global (`~/.claude/skills/`) khi trùng tên
- Cả hai cùng tồn tại được (project win nếu trùng tên)

---

## 3. Commands (Slash Commands)

### Vị trí
```
~/.claude/commands/       # Global — dùng cho mọi project
.claude/commands/         # Project — chỉ project này
```

### Format
```
.claude/commands/analyze.md   → tạo lệnh /analyze
.claude/commands/screen.md    → tạo lệnh /screen
```

> **Note:** Skills và Commands về cơ bản merge thành nhau trong Claude Code mới.
> Commands là "skills invoked by slash command". Nếu trùng tên, skills thắng.

### Frontmatter tối thiểu
```yaml
---
description: Mô tả lệnh này làm gì
---
```

---

## 4. Agents

### Vị trí
```
~/.claude/agents/         # Global
.claude/agents/           # Project
```

### Format
```markdown
---
name: agent-name
description: Khi nào dùng agent này
tools: Read, Glob, Grep   # Tuỳ chọn
model: sonnet             # Tuỳ chọn
permissionMode: plan      # Tuỳ chọn
---

System prompt ở đây...
```

### Priority: Project agents > Global agents > Built-in agents

---

## 5. CLAUDE.md files

| File | Vị trí | Mục đích |
|------|--------|---------|
| `CLAUDE.md` | `./CLAUDE.md` hoặc `./.claude/CLAUDE.md` | Project instructions (git-tracked) |
| `~/.claude/CLAUDE.md` | Global | Personal instructions cho mọi project |
| `CLAUDE.local.md` | Không phải feature chuẩn | Dùng `settings.local.json` thay thế |

**Thứ tự load:**
1. Managed policy CLAUDE.md (không bỏ được)
2. Ancestor CLAUDE.md (đi lên cây thư mục)
3. Project CLAUDE.md (tại working directory)
4. Subdirectory CLAUDE.md (lazy-loaded khi truy cập file trong đó)
5. User CLAUDE.md (`~/.claude/CLAUDE.md`)

> **Best practice:** Giữ mỗi file < 200 dòng. Dùng `@import` để tách file lớn.

---

## 6. Rules Directory

```
.claude/rules/
├── code-style.md          # Load lúc khởi động (unconditional)
├── testing.md
└── api/
    └── api-design.md      # Load chỉ khi mở file match paths
```

**Path-specific rules** (tiết kiệm context):
```yaml
---
paths:
  - "src/api/**/*.ts"      # Chỉ load khi Claude mở file này
---
```

---

## 7. Settings.json

| File | Tầng | Git-tracked? |
|------|------|--------------|
| `~/.claude/settings.json` | Global | Không |
| `.claude/settings.json` | Project | Có |
| `.claude/settings.local.json` | Local | **Không** (gitignore!) |

**Merge rules:**
- Permissions arrays → merge (mọi tầng đều có hiệu lực)
- Object values → override (specific hơn thắng)

---

## 8. Cấu trúc đầy đủ dự án này

```
vn-stock-trader/
├── CLAUDE.md                         # Project instructions
├── docs/
│   └── CLAUDE_FOLDER_STRUCTURE.md    # File này
└── .claude/
    ├── settings.json                 # Project settings (git)
    ├── settings.local.json           # Local settings (gitignored)
    ├── skills/                       # PROJECT-LEVEL skills
    │   ├── technical-analysis.md     # /technical-analysis
    │   ├── fundamental-analysis.md   # /fundamental-analysis
    │   ├── news-impact.md            # /news-impact
    │   ├── stock-screener.md         # /stock-screener
    │   ├── sector-compare.md         # /sector-compare
    │   └── portfolio-review.md       # /portfolio-review
    ├── commands/                     # PROJECT-LEVEL slash commands
    │   ├── analyze.md                # /analyze
    │   ├── screen.md                 # /screen
    │   ├── portfolio.md              # /portfolio
    │   ├── news.md                   # /news
    │   ├── compare.md                # /compare
    │   ├── report.md                 # /report
    │   └── alert.md                  # /alert
    ├── agents/                       # Custom agents
    └── agent-memory/                 # Persistent memory
```

---

## 9. Thứ tự load Skills/Commands

```
Project (.claude/skills/) → Global (~/.claude/skills/)
```

Claude load mô tả (description) của tất cả skills vào context ngay từ đầu.
Nội dung đầy đủ của skill chỉ load khi được invoke.

**Kết luận cho project này:** Luôn tạo skills/commands trong `.claude/` của PROJECT,
không phải `~/.claude/` global — để team share qua git và tránh ảnh hưởng project khác.

# Plugin Research — Claude Code Plugin & Marketplace

> Nghien cuu ngay 2026-03-31. Tham khao oh-my-claudecode v4.9.3, Claude Code docs.

---

## 1. Claude Code Plugin Format

### Cau truc thu muc

```
plugin-root/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest (bat buoc)
│   └── marketplace.json     # Marketplace registry (tuy chon)
├── .claude/
│   ├── skills/              # Auto-trigger skills (SKILL.md)
│   ├── commands/            # Slash commands (.md)
│   └── agents/              # Specialized agents (.md)
├── .mcp.json                # MCP server definitions
├── settings.json            # Default settings (optional)
└── README.md
```

**Quan trong:** Chi `plugin.json` va `marketplace.json` nam trong `.claude-plugin/`. Tat ca cac directory khac (skills, commands, agents) o plugin root.

### plugin.json Schema

```json
{
  "name": "string",              // Required. kebab-case, unique identifier
  "version": "string",           // Required. Semantic versioning (X.Y.Z)
  "description": "string",       // Required. Mo ta ngan
  "author": {                    // Optional
    "name": "string",
    "email": "string"
  },
  "homepage": "string",          // Optional. URL
  "repository": "string",       // Optional. Git repo URL
  "license": "string",          // Optional. SPDX identifier
  "keywords": ["string"],       // Optional. Tags cho search

  // Component paths (relative to plugin root)
  "skills": "./path/to/skills/",
  "commands": ["./path/to/commands/"],
  "agents": "./path/to/agents/",
  "hooks": "./hooks/hooks.json",     // Hoac inline object
  "mcpServers": "./.mcp.json",      // Hoac inline object
  "lspServers": "./.lsp.json",
  "outputStyles": "./styles/",

  // User config (prompt khi enable)
  "userConfig": {
    "key": { "description": "...", "sensitive": false }
  }
}
```

### Bien dac biet

| Bien | Mo ta |
|------|-------|
| `${CLAUDE_PLUGIN_ROOT}` | Thu muc cai dat plugin (thay doi khi update) |
| `${CLAUDE_PLUGIN_DATA}` | Thu muc data persistent (`~/.claude/plugins/data/{id}/`) |
| `${user_config.key}` | Gia tri user config |

---

## 2. Marketplace Distribution

### marketplace.json

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "marketplace-id",
  "description": "Mo ta marketplace",
  "owner": { "name": "Author", "email": "email" },
  "version": "1.0.0",
  "plugins": [
    {
      "name": "plugin-name",
      "description": "Mo ta plugin",
      "version": "1.0.0",
      "source": "./",
      "category": "finance",
      "homepage": "https://...",
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### Plugin Sources

| Source | Vi du |
|--------|-------|
| Local path | `"source": "./"` |
| GitHub | `{ "source": "github", "repo": "owner/repo", "ref": "v1.0.0" }` |
| Git URL | `{ "source": "url", "url": "https://..." }` |
| npm | `{ "source": "npm", "package": "@org/pkg", "version": "1.0" }` |

### Installation Commands

```bash
# Add marketplace
/plugin marketplace add owner/repo              # GitHub
/plugin marketplace add https://git-url/repo    # Git
/plugin marketplace add ./local-path            # Local

# Install plugin tu marketplace
/plugin install plugin-name@marketplace-name

# Install with scope
claude plugin install plugin-name --scope user|project|local
```

### Official Marketplace

Submit tai:
- https://claude.ai/settings/plugins/submit
- https://platform.claude.com/plugins/submit

---

## 3. Component Registration

### Skills

- Tu dong phat hien trong thu muc `skills/`
- Moi skill can SKILL.md voi frontmatter
- Namespacing: `/plugin-name:skill-name`

### Commands

- Tu dong phat hien trong thu muc `commands/`
- File .md voi frontmatter

### Agents

- Tu dong phat hien trong thu muc `agents/`
- File .md voi frontmatter (name, description, model, effort)

### Hooks

- Cau hinh trong `hooks/hooks.json` hoac inline trong plugin.json
- Events: SessionStart, PostToolUse, Stop, etc.
- Matcher support: `"matcher": "Write|Edit"`

### MCP Servers

- Tham chieu tu `.mcp.json` hoac inline trong plugin.json
- Su dung `${CLAUDE_PLUGIN_ROOT}` cho duong dan tuong doi

---

## 4. Testing & Validation

```bash
# Load local plugin de test
claude --plugin-dir ./my-plugin

# Reload sau khi thay doi
/reload-plugins

# Validate structure
claude plugin validate .
```

---

## 5. Reference: oh-my-claudecode v4.9.3

**plugin.json:**
```json
{
  "name": "oh-my-claudecode",
  "version": "4.9.3",
  "description": "Multi-agent orchestration system for Claude Code",
  "author": { "name": "oh-my-claudecode contributors" },
  "repository": "https://github.com/Yeachan-Heo/oh-my-claudecode",
  "homepage": "https://github.com/Yeachan-Heo/oh-my-claudecode",
  "license": "MIT",
  "keywords": ["claude-code", "plugin", "multi-agent", "orchestration", "automation"],
  "skills": "./skills/",
  "mcpServers": "./.mcp.json"
}
```

**marketplace.json:**
```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "omc",
  "description": "Claude Code native multi-agent orchestration...",
  "owner": { "name": "Yeachan Heo", "email": "hurrc04@gmail.com" },
  "version": "4.9.3",
  "plugins": [
    {
      "name": "oh-my-claudecode",
      "source": "./",
      "category": "productivity",
      ...
    }
  ]
}
```

**Nhan xet:**
- Don gian, chi khai bao skills va mcpServers
- Khong khai bao commands hay agents rieng (co the tu dong phat hien)
- `"source": "./"` cho local development

---

## 6. Ap dung cho vn-stock-trader

### Nhung gi can dang ky:

| Component | So luong | Path |
|-----------|---------|------|
| Skills | 10 | `.claude/skills/` |
| Commands | 8 | `.claude/commands/` |
| Agents | 4 | `.claude/agents/` |
| MCP Server | 1 (11 tools) | `.mcp.json` |
| Hooks | 1 (Stop) | Inline hoac file |

### Luu y:

1. **Paths tuong doi:** Tat ca paths trong plugin.json phai relative to plugin root
2. **Khong hardcode absolute paths:** Dung `${CLAUDE_PLUGIN_ROOT}` thay vi `/Users/xxx/`
3. **MCP server command:** Can dung `uv run python` voi cwd dung
4. **Dependencies:** Plugin can install Python deps (uv sync)
5. **Hooks Stop:** Khong nen include trong plugin (local-specific, tied to claude-bridge)

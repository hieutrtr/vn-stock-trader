# Claude Code Extension Types — Complete Reference Guide

> Last updated: 2026-03-30 | Based on Claude Code 2.x documentation

## Table of Contents

1. [Overview & Interaction Map](#overview)
2. [Skills](#skills)
3. [Commands](#commands) (deprecated → use Skills)
4. [Agents/Subagents](#agents)
5. [Hooks](#hooks)
6. [Rules](#rules)
7. [MCP Servers](#mcp-servers)
8. [CLAUDE.md](#claudemd)
9. [How Extensions Interact](#interactions)
10. [Configuration Locations Summary](#locations)

---

## Overview

```
CLAUDE.md ──────────────────── Project instructions (always loaded)
.claude/rules/ ─────────────── Scoped rules (loaded at start or on-demand)
.claude/skills/<name>/SKILL.md ─ Skills (auto or explicit /skill-name)
.claude/agents/<name>.md ──── Subagents (Claude delegates based on description)
.claude/commands/<name>.md ── Commands (DEPRECATED, use Skills instead)
.mcp.json ──────────────────── MCP server registrations
settings.json ──────────────── Hooks, permissions, MCP config
```

---

## Skills

**Location:** `.claude/skills/<name>/SKILL.md`
**Invocation:** `/skill-name` or auto-invoked by Claude based on `description`

### Complete Format

```yaml
---
name: skill-name                          # Optional — defaults to directory name
description: |                            # CRITICAL — Claude uses this to auto-invoke
  What this skill does and WHEN to use it.
  Be specific about trigger conditions.
argument-hint: "[symbol] [options]"        # Optional — shown in autocomplete
disable-model-invocation: false           # Optional — if true, only user can invoke
user-invocable: true                      # Optional — if false, hidden from /menu
allowed-tools: Tool1, Tool2, mcp__server__tool  # Optional — comma-separated
model: inherit                            # Optional — sonnet/opus/haiku/inherit
effort: medium                            # Optional — low/medium/high/max
context: fork                             # Optional — run in subagent context
agent: Explore                            # Optional — which subagent (if context: fork)
---

# Skill Instructions

Use $ARGUMENTS for user input.
Use $ARGUMENTS[0], $ARGUMENTS[1] for indexed access.
Use ${CLAUDE_SKILL_DIR} for skill directory path.
```

### Key Points

- **`triggers` field does NOT exist** — Claude uses `description` for auto-invocation
- **`allowed-tools` format:** comma-separated string (NOT YAML list), use full MCP names
  - MCP tool format: `mcp__<server-name>__<tool-name>`
  - Built-in tools: `Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `WebSearch`, `WebFetch`
- Skills can have supporting files in the same directory (e.g., `reference.md`, scripts/)

### Allowed-Tools Examples

```yaml
# Correct — comma-separated string with full MCP prefixes
allowed-tools: mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_stock_history, WebFetch

# WRONG — YAML list (not supported)
allowed-tools:
  - get_stock_price    # ← Missing mcp__ prefix AND wrong format
```

---

## Commands

**Location:** `.claude/commands/<name>.md`
**Status:** **DEPRECATED** — merged into Skills. Both work identically but Skills are preferred.

### Format

```yaml
---
description: What this command does
disable-model-invocation: false
allowed-tools: Read, Grep
---

Command instructions here.
```

Commands are invoked as `/command-name`. They support the same frontmatter as Skills but are single files (no supporting directory).

---

## Agents/Subagents

**Location:** `.claude/agents/<name>.md`
**Invocation:** Claude auto-delegates based on `description`, or user @-mentions

### Complete Format

```yaml
---
name: agent-name                     # Optional — defaults to file name
description: |                       # CRITICAL — Claude reads this to decide when to delegate
  What this agent does and WHEN to invoke it.
tools: Tool1, Tool2, mcp__server__tool  # Optional — comma-separated allowed tools
disallowedTools: Write, Edit         # Optional — deny specific tools
model: sonnet                        # Optional — sonnet/opus/haiku/inherit
effort: high                         # Optional — low/medium/high/max
maxTurns: 20                         # Optional — max agentic turns
---

# Agent System Prompt

Your instructions here.
```

### Tools Field

- Use `tools:` (NOT `allowed-tools:`) for agents
- MCP tools: `mcp__<server-name>__<tool-name>`
- Built-in agents: `Explore` (read-only fast), `Plan` (research), `general-purpose` (all tools)

### Example

```yaml
---
name: market-watcher
description: Monitor VN stock market — use when user wants to scan portfolio or watchlist
tools: mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_market_overview
model: sonnet
---
```

---

## Hooks

**Location:** `settings.json` (or skill/agent frontmatter)

### Format

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "./scripts/validate.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write $FILE_PATH"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./scripts/session-end.sh"
          }
        ]
      }
    ]
  }
}
```

### Hook Events

| Event | When | Can Block |
|-------|------|-----------|
| `SessionStart` | Session begins | No |
| `PreToolUse` | Before tool executes | Yes |
| `PostToolUse` | After tool succeeds | No |
| `UserPromptSubmit` | Before prompt processing | Yes |
| `Stop` | Before Claude stops responding | Yes |
| `SubagentStart` / `SubagentStop` | Subagent lifecycle | No |

### Matcher Patterns

| Pattern | Matches |
|---------|---------|
| `"Bash"` | All Bash calls |
| `"Bash(npm *)"` | Bash commands starting with `npm` |
| `"Edit\|Write"` | Edit or Write tool |
| `"mcp__vn-stock-trader"` | All tools from this MCP server |
| `"mcp__vn-stock-trader__get_news"` | Specific MCP tool |

### Hook Output (stdout)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "Context injected into Claude's awareness"
  },
  "continue": true
}
```

- Exit code 0 = success
- Exit code 2 = blocking error (stderr message shown to user)

---

## Rules

**Location:** `.claude/rules/<topic>.md`

### Unconditional Rule (loaded at session start)

```markdown
# Code Style

- Use 2-space indentation
- Use conventional commits (feat:, fix:, docs:)
```

### Path-Scoped Rule (loaded when matching files opened)

```yaml
---
paths:
  - "src/api/**/*.ts"
  - "src/api/**/*.tsx"
---

# API Rules

All endpoints must include input validation.
```

Rules without `paths` frontmatter are unconditional.

---

## MCP Servers

**Location:** `.mcp.json` (preferred) or `settings.json` under `mcpServers`

### .mcp.json Format

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "python",
      "args": ["path/to/server.py"],
      "env": {
        "API_KEY": "${API_KEY}"
      }
    }
  }
}
```

### Critical: Server Name → Tool Prefix

The **key** in `mcpServers` determines the tool prefix in Claude Code:

```
mcpServers key = "vn-stock-trader"
→ Tools available as: mcp__vn-stock-trader__get_stock_price
                      mcp__vn-stock-trader__get_news
                      mcp__vn-stock-trader__screen_stocks
                      ...
```

### Server Types

| Type | Description |
|------|-------------|
| `stdio` | Local command-line process |
| `http` | HTTP endpoint |
| `sse` | Server-Sent Events |
| `ws` | WebSocket |

---

## CLAUDE.md

**Location:** `./CLAUDE.md` or `./.claude/CLAUDE.md`
**Loading:** Always at session start

Best practices:
- Keep under 200 lines (longer files waste context)
- Use `@file-path` imports to reference other files
- Use `.claude/rules/` for topic-specific or path-scoped guidance
- HTML comments `<!-- ... -->` are stripped before sending to Claude

---

## Interactions

### How extensions link to each other

```
User request
  │
  ▼
CLAUDE.md + Rules ──── Always in context (baseline instructions)
  │
  ▼
Claude reads descriptions of Skills + Agents
  │
  ├─→ Invokes Skill ──── allowed-tools restricts which tools skill can call
  │       │
  │       └─→ MCP Tools (mcp__server__tool_name)
  │
  └─→ Delegates to Agent ──── tools: field defines agent's allowed tools
          │
          └─→ MCP Tools + Built-in Tools

Hooks ──── Fire automatically at PreToolUse, PostToolUse, Stop, etc.
           Can block or inject context into any of the above
```

### Skill vs Agent: When to use which

| Use Skill when... | Use Agent when... |
|-------------------|-------------------|
| Single focused analysis task | Multi-step autonomous workflow |
| User explicitly invokes | Claude delegates automatically |
| Structured output format | Complex decision-making required |
| Read-only operations | May need to write/update data |

### Tool Name Flow

```
MCP Server registered as "vn-stock-trader" in .mcp.json
    ↓
FastMCP exposes: get_stock_price, get_news, screen_stocks, ...
    ↓
Claude Code sees: mcp__vn-stock-trader__get_stock_price, etc.
    ↓
Skills reference in allowed-tools: mcp__vn-stock-trader__get_stock_price
    ↓
Agents reference in tools: mcp__vn-stock-trader__get_stock_price
```

---

## Locations Summary

| Extension | Project | User | Plugin |
|-----------|---------|------|--------|
| Skills | `.claude/skills/<name>/SKILL.md` | `~/.claude/skills/` | `skills/` |
| Commands | `.claude/commands/<name>.md` | `~/.claude/commands/` | `commands/` |
| Agents | `.claude/agents/<name>.md` | `~/.claude/agents/` | `agents/` |
| Rules | `.claude/rules/<topic>.md` | `~/.claude/rules/` | — |
| MCP config | `.mcp.json` | `~/.claude/.mcp.json` | `.mcp.json` |
| Settings | `.claude/settings.json` | `~/.claude/settings.json` | `settings.json` |
| Hooks | In `settings.json` | In `settings.json` | `hooks/hooks.json` |
| CLAUDE.md | `./CLAUDE.md` | `~/.claude/CLAUDE.md` | — |

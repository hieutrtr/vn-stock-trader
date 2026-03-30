#!/bin/bash
# deploy.sh — Copy staged skills/commands vào .claude/ project folder
# Chạy một lần để deploy: bash docs/staged/deploy.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAGED_DIR="$PROJECT_ROOT/docs/staged"
CLAUDE_DIR="$PROJECT_ROOT/.claude"

echo "🚀 Deploy skills & commands vào $CLAUDE_DIR"
echo ""

# ---------- Skills ----------
echo "📚 Copying skills..."
cp "$STAGED_DIR/skills/fundamental-analysis.md" "$CLAUDE_DIR/skills/"
echo "  ✅ fundamental-analysis.md"

cp "$STAGED_DIR/skills/news-impact.md" "$CLAUDE_DIR/skills/"
echo "  ✅ news-impact.md"

cp "$STAGED_DIR/skills/stock-screener.md" "$CLAUDE_DIR/skills/"
echo "  ✅ stock-screener.md"

cp "$STAGED_DIR/skills/sector-compare.md" "$CLAUDE_DIR/skills/"
echo "  ✅ sector-compare.md"

cp "$STAGED_DIR/skills/portfolio-review.md" "$CLAUDE_DIR/skills/"
echo "  ✅ portfolio-review.md"

# ---------- Commands ----------
echo ""
echo "⚡ Copying commands..."
cp "$STAGED_DIR/commands/analyze.md" "$CLAUDE_DIR/commands/"
echo "  ✅ analyze.md → /analyze"

cp "$STAGED_DIR/commands/screen.md" "$CLAUDE_DIR/commands/"
echo "  ✅ screen.md → /screen"

cp "$STAGED_DIR/commands/portfolio.md" "$CLAUDE_DIR/commands/"
echo "  ✅ portfolio.md → /portfolio"

cp "$STAGED_DIR/commands/news.md" "$CLAUDE_DIR/commands/"
echo "  ✅ news.md → /news"

cp "$STAGED_DIR/commands/compare.md" "$CLAUDE_DIR/commands/"
echo "  ✅ compare.md → /compare"

cp "$STAGED_DIR/commands/report.md" "$CLAUDE_DIR/commands/"
echo "  ✅ report.md → /report"

cp "$STAGED_DIR/commands/alert.md" "$CLAUDE_DIR/commands/"
echo "  ✅ alert.md → /alert"

# ---------- Settings ----------
echo ""
echo "⚙️  Creating .claude/settings.json với permissions..."
cat > "$CLAUDE_DIR/settings.json" << 'SETTINGS_EOF'
{
  "permissions": {
    "allow": [
      "Write(.claude/skills/*)",
      "Write(.claude/commands/*)",
      "Write(.claude/agents/*)",
      "Write(.claude/settings.json)",
      "Write(docs/**)",
      "Write(src/**)",
      "Write(tests/**)",
      "Bash(python*)",
      "Bash(pytest*)",
      "Bash(pip*)",
      "Bash(ruff*)"
    ]
  }
}
SETTINGS_EOF
echo "  ✅ settings.json"

echo ""
echo "✅ DONE! Đã deploy:"
echo "   📚 Skills: $(ls $CLAUDE_DIR/skills/ | wc -l | tr -d ' ') files"
echo "   ⚡ Commands: $(ls $CLAUDE_DIR/commands/ | wc -l | tr -d ' ') files"
echo ""
echo "📌 Restart Claude Code session để load skills/commands mới."
echo "   Hoặc dùng /hooks để reload config."

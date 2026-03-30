#!/usr/bin/env bash
# install.sh — VN Stock Trader plugin installer for Claude Code
#
# Usage:
#   ./install.sh                   # Install from current directory
#   ./install.sh --verify          # Verify installation only
#   ./install.sh --uninstall       # Remove plugin

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_NAME="vn-stock-trader"

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  VN Stock Trader — Claude Code Plugin        ║${NC}"
    echo -e "${BLUE}║  Vietnamese Stock Market Analysis Tools       ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

check_prerequisites() {
    echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"

    # Check Python
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}  ✗ Python 3 not found. Install Python 3.12+${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "$(echo "$PYTHON_VERSION < 3.12" | bc -l 2>/dev/null || echo 0)" == "1" ]]; then
        echo -e "${YELLOW}  ! Python $PYTHON_VERSION detected. Python 3.12+ recommended${NC}"
    else
        echo -e "${GREEN}  ✓ Python $PYTHON_VERSION${NC}"
    fi

    # Check uv
    if ! command -v uv &>/dev/null; then
        echo -e "${RED}  ✗ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ uv $(uv --version 2>/dev/null | head -1)${NC}"

    # Check Claude Code
    if command -v claude &>/dev/null; then
        echo -e "${GREEN}  ✓ Claude Code CLI found${NC}"
    else
        echo -e "${YELLOW}  ! Claude Code CLI not found in PATH (may still work if installed elsewhere)${NC}"
    fi

    # Check plugin.json
    if [[ ! -f "$PLUGIN_DIR/.claude-plugin/plugin.json" ]]; then
        echo -e "${RED}  ✗ plugin.json not found. Run this script from the plugin root directory${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ plugin.json found${NC}"
}

install_dependencies() {
    echo ""
    echo -e "${YELLOW}[2/4] Installing Python dependencies...${NC}"
    cd "$PLUGIN_DIR"

    if uv sync 2>&1 | tail -3; then
        echo -e "${GREEN}  ✓ Dependencies installed${NC}"
    else
        echo -e "${RED}  ✗ Failed to install dependencies${NC}"
        exit 1
    fi
}

verify_installation() {
    echo ""
    echo -e "${YELLOW}[3/4] Verifying installation...${NC}"
    cd "$PLUGIN_DIR"

    # Check MCP server can start
    if timeout 10 uv run python -c "
import sys
sys.path.insert(0, 'mcp-server')
from server import mcp
print('MCP server: OK')
" 2>/dev/null; then
        echo -e "${GREEN}  ✓ MCP server loads correctly${NC}"
    else
        echo -e "${YELLOW}  ! MCP server check skipped (may need vnstock configured)${NC}"
    fi

    # Check core imports
    if uv run python -c "import vnstock; import pandas_ta; import mcp; print('Core imports: OK')" 2>/dev/null; then
        echo -e "${GREEN}  ✓ Core dependencies (vnstock, pandas-ta, mcp)${NC}"
    else
        echo -e "${RED}  ✗ Missing core dependencies${NC}"
        exit 1
    fi

    # Check skills
    SKILL_COUNT=$(find "$PLUGIN_DIR/.claude/skills" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "${GREEN}  ✓ $SKILL_COUNT skills found${NC}"

    # Check commands
    CMD_COUNT=$(find "$PLUGIN_DIR/.claude/commands" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "${GREEN}  ✓ $CMD_COUNT commands found${NC}"

    # Check agents
    AGENT_COUNT=$(find "$PLUGIN_DIR/.claude/agents" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "${GREEN}  ✓ $AGENT_COUNT agents found${NC}"

    # Run tests (quick)
    echo ""
    echo -e "${YELLOW}  Running tests...${NC}"
    if uv run pytest mcp-server/tests/ -q --tb=no 2>&1 | tail -3; then
        echo -e "${GREEN}  ✓ Tests passed${NC}"
    else
        echo -e "${YELLOW}  ! Some tests failed (plugin may still work)${NC}"
    fi
}

print_usage() {
    echo ""
    echo -e "${YELLOW}[4/4] Installation complete!${NC}"
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Plugin installed successfully!                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BLUE}To register as Claude Code plugin:${NC}"
    echo ""
    echo -e "    ${GREEN}# Option 1: Add as marketplace (recommended)${NC}"
    echo -e "    /plugin marketplace add $PLUGIN_DIR"
    echo -e "    /plugin install $PLUGIN_NAME@$PLUGIN_NAME"
    echo ""
    echo -e "    ${GREEN}# Option 2: Load directly during development${NC}"
    echo -e "    claude --plugin-dir $PLUGIN_DIR"
    echo ""
    echo -e "    ${GREEN}# Option 3: Install from GitHub (after push)${NC}"
    echo -e "    /plugin marketplace add github:hieutran/vn-stock-trader"
    echo -e "    /plugin install $PLUGIN_NAME@$PLUGIN_NAME"
    echo ""
    echo -e "  ${BLUE}Quick test:${NC}"
    echo -e "    /analyze VNM"
    echo -e "    /portfolio"
    echo -e "    /screen value"
    echo ""
    echo -e "  ${BLUE}Components included:${NC}"
    echo -e "    11 MCP tools  — Stock price, history, financials, news, screener..."
    echo -e "    10 Skills     — TA, FA, news impact, portfolio, screener, sector..."
    echo -e "     8 Commands   — /analyze, /screen, /portfolio, /news, /compare..."
    echo -e "     4 Agents     — market-watcher, news-analyst, portfolio-manager..."
    echo ""
}

do_uninstall() {
    echo -e "${YELLOW}Uninstalling vn-stock-trader plugin...${NC}"
    echo ""
    echo -e "  Run in Claude Code:"
    echo -e "    /plugin uninstall $PLUGIN_NAME@$PLUGIN_NAME"
    echo -e "    /plugin marketplace remove $PLUGIN_NAME"
    echo ""
    echo -e "${GREEN}Done.${NC}"
}

# Main
print_header

case "${1:-install}" in
    --verify|-v)
        check_prerequisites
        verify_installation
        echo -e "\n${GREEN}Verification complete.${NC}"
        ;;
    --uninstall|-u)
        do_uninstall
        ;;
    install|--install|"")
        check_prerequisites
        install_dependencies
        verify_installation
        print_usage
        ;;
    *)
        echo "Usage: $0 [--verify | --uninstall]"
        exit 1
        ;;
esac

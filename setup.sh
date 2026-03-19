#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  Personal Agentic Factory — Setup Script
#  Tested on macOS and Ubuntu/Debian
# ─────────────────────────────────────────────────────────────────
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[PAF]${NC} $1"; }
warn()  { echo -e "${YELLOW}[PAF]${NC} $1"; }
error() { echo -e "${RED}[PAF]${NC} $1"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║      🏭  Personal Agentic Factory Setup          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Check Python ─────────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Install from https://python.org"
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Found Python $PY_VERSION"

# ── Install dependencies ──────────────────────────────────────────
info "Installing Python dependencies..."
pip3 install -r requirements.txt --quiet
info "Dependencies installed ✅"

# ── Copy .env ────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    warn ".env created from template. You MUST edit it before running."
else
    info ".env already exists — skipping"
fi

# ── Check Docker ─────────────────────────────────────────────────
echo ""
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    info "Docker found and running ✅"
else
    warn "Docker not running (or not installed)."
    warn "The factory will still work using subprocess mode (USE_DOCKER=false)."
    warn "For proper sandboxing, install Docker Desktop: https://docker.com"
    # Auto-set USE_DOCKER=false in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' 's/USE_DOCKER=true/USE_DOCKER=false/' .env 2>/dev/null || true
    else
        sed -i 's/USE_DOCKER=true/USE_DOCKER=false/' .env 2>/dev/null || true
    fi
fi

# ── Create output dirs ───────────────────────────────────────────
mkdir -p factory_jobs factory_state factory_logs
info "Output directories created ✅"

# ── Check .env is filled ────────────────────────────────────────
echo ""
MISSING=()
source .env 2>/dev/null || true

[ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-your-key-here" ] && MISSING+=("ANTHROPIC_API_KEY")
[ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your-bot-token-here" ] && MISSING+=("TELEGRAM_BOT_TOKEN")
[ -z "$TELEGRAM_CHAT_ID" ] || [ "$TELEGRAM_CHAT_ID" = "your-chat-id-here" ] && MISSING+=("TELEGRAM_CHAT_ID")

if [ ${#MISSING[@]} -gt 0 ]; then
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    warn "Edit .env and fill in these values:"
    for key in "${MISSING[@]}"; do
        warn "  → $key"
    done
    warn ""
    warn "Anthropic key : https://console.anthropic.com"
    warn "Telegram bot  : Message @BotFather on Telegram"
    warn "Telegram ID   : Message @userinfobot on Telegram"
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo ""
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "✅ Setup complete! Run the factory:"
    info ""
    info "  python3 main.py          ← Start everything"
    info "  python3 main.py bot      ← Telegram bot only"
    info "  python3 main.py dashboard ← Web dashboard only"
    info ""
    info "  # Or test with a direct build:"
    info "  python3 main.py build \"build a BTC price tracker CLI\""
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
echo ""

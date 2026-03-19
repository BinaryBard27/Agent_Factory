"""
Central config — all values come from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── AI ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
MODEL               = os.getenv("MODEL", "claude-opus-4-5")
MAX_TOKENS          = int(os.getenv("MAX_TOKENS", "4096"))

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")   # your personal chat id

# ── Factory ───────────────────────────────────────────────────────────────────
MAX_RETRIES         = int(os.getenv("MAX_RETRIES", "6"))
OUTPUT_BASE_DIR     = os.getenv("OUTPUT_BASE_DIR", "factory_jobs")
STATE_DIR           = os.getenv("STATE_DIR", "factory_state")
LOG_DIR             = os.getenv("LOG_DIR", "factory_logs")

# ── Sandbox ───────────────────────────────────────────────────────────────────
USE_DOCKER          = os.getenv("USE_DOCKER", "true").lower() == "true"
DOCKER_IMAGE_PYTHON = os.getenv("DOCKER_IMAGE_PYTHON", "python:3.11-slim")
DOCKER_IMAGE_NODE   = os.getenv("DOCKER_IMAGE_NODE", "node:20-slim")
SANDBOX_TIMEOUT     = int(os.getenv("SANDBOX_TIMEOUT", "60"))

# ── Validation ────────────────────────────────────────────────────────────────
def validate():
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise EnvironmentError(f"Missing env vars: {', '.join(missing)}\nCopy .env.example → .env and fill in values.")

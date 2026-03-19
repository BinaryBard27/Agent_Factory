"""
Telegram Bot — Your remote control.
Commands:
  /build <task>   — Start a new factory job
  /status         — Check all running/recent jobs
  /resume <task>  — Resume a crashed job
  /cancel <task>  — Cancel a job
  /help           — Show commands
"""
import time
import threading
import requests
from config.settings import TELEGRAM_BOT_TOKEN
from core.logger import log
from core import job_queue as Queue
import core.orchestrator as Factory
import state.manager as State


BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
_offset = 0


# ── Telegram API helpers ───────────────────────────────────────────────────────
def get_updates() -> list:
    global _offset
    try:
        r = requests.get(
            f"{BASE}/getUpdates",
            params={"offset": _offset, "timeout": 30, "allowed_updates": ["message"]},
            timeout=35
        )
        updates = r.json().get("result", [])
        if updates:
            _offset = updates[-1]["update_id"] + 1
        return updates
    except Exception as e:
        log("telegram", f"getUpdates error: {e}")
        return []


def send(chat_id: str, text: str):
    try:
        requests.post(
            f"{BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        log("telegram", f"Send error: {e}")


# ── Command handlers ──────────────────────────────────────────────────────────
def handle_build(chat_id: str, task: str):
    if not task.strip():
        send(chat_id, "❌ Usage: `/build <describe what you want to build>`")
        return

    pos = Queue.enqueue(task.strip(), chat_id=chat_id)
    if pos > 1:
        send(chat_id, f"📋 Queued at position {pos}. I'll start when the current job finishes.")
    log("telegram", f"Enqueued for {chat_id}: {task[:60]}")


def handle_status(chat_id: str):
    jobs = State.list_jobs()
    queued = Queue.size()

    if not jobs and not queued:
        send(chat_id, "📭 No jobs found.")
        return

    lines = ["📊 *Factory Status*\n"]
    if queued:
        lines.append(f"⏳ {queued} job(s) in queue\n")

    for j in jobs[-10:]:
        icon = {"done": "✅", "failed": "💀", "code": "⚙️", "architect": "📐"}.get(j["stage"], "❓")
        lines.append(f"{icon} `{j['task'][:50]}` — {j['stage']} (attempt {j['attempt']})")

    send(chat_id, "\n".join(lines))


def handle_resume(chat_id: str, task: str):
    if not task.strip():
        send(chat_id, "❌ Usage: `/resume <original task text>`")
        return

    state = State.load(task.strip())
    if not state:
        send(chat_id, "❌ No saved state found for that task.")
        return

    send(chat_id, f"⚡ Resuming job at stage: `{state['stage']}`")

    def _run():
        Factory.run(task.strip(), chat_id=chat_id)

    threading.Thread(target=_run, daemon=True).start()


def handle_cancel(chat_id: str, task: str):
    if not task.strip():
        send(chat_id, "❌ Usage: `/cancel <task>`")
        return
    State.clear(task.strip())
    send(chat_id, "🗑️ State cleared. Job will not resume.")


def handle_help(chat_id: str):
    msg = """🏭 *Personal Agentic Factory*

Available commands:

`/build <task>` — Build something
  _Example: /build a CLI crypto price tracker_

`/status` — See all jobs

`/resume <task>` — Resume a crashed job

`/cancel <task>` — Clear state for a job

`/help` — This message

---
Just describe what you want built. The factory handles the rest."""
    send(chat_id, msg)


# ── Message router ─────────────────────────────────────────────────────────────
def handle_message(msg: dict):
    chat_id = str(msg["chat"]["id"])
    text    = msg.get("text", "").strip()

    if not text:
        return

    log("telegram", f"[{chat_id}] {text[:80]}")

    if text.startswith("/build"):
        handle_build(chat_id, text[6:].strip())
    elif text.startswith("/status"):
        handle_status(chat_id)
    elif text.startswith("/resume"):
        handle_resume(chat_id, text[7:].strip())
    elif text.startswith("/cancel"):
        handle_cancel(chat_id, text[7:].strip())
    elif text.startswith("/help") or text.startswith("/start"):
        handle_help(chat_id)
    else:
        # Treat plain messages as /build
        send(chat_id, f"🏭 Starting build for: `{text[:100]}`\n\nI'll update you as it progresses...")
        handle_build(chat_id, text)


# ── Polling loop ──────────────────────────────────────────────────────────────
def run():
    if not TELEGRAM_BOT_TOKEN:
        log("telegram", "❌ TELEGRAM_BOT_TOKEN not set. Bot disabled.")
        return

    log("telegram", "✅ Bot polling started. Send /help to your bot.")

    while True:
        try:
            updates = get_updates()
            for update in updates:
                if "message" in update:
                    handle_message(update["message"])
        except KeyboardInterrupt:
            log("telegram", "Bot stopped.")
            break
        except Exception as e:
            log("telegram", f"Loop error: {e}")
            time.sleep(5)

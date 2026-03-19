"""
Liaison — Sends real-time Telegram updates during job execution.
Acts as the "project manager" keeping you informed from your phone.
"""
import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from core.logger import log


def _send(text: str, chat_id: str = None) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        return False

    target = chat_id or TELEGRAM_CHAT_ID
    if not target:
        return False

    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id":    target,
        "text":       text,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        log("liaison", f"Send failed: {e}")
        return False


def _send_document(file_path: str, caption: str = "", chat_id: str = None) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        return False
    target = chat_id or TELEGRAM_CHAT_ID
    url    = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": target, "caption": caption, "parse_mode": "Markdown"},
                files={"document": f},
                timeout=30
            )
        return r.status_code == 200
    except Exception as e:
        log("liaison", f"Doc send failed: {e}")
        return False


# ── Public message helpers ────────────────────────────────────────────────────

def job_started(task: str, chat_id: str = None):
    msg = f"🏭 *Factory Started*\n\n📋 `{task[:200]}`\n\n⚙️ Architect is designing the system..."
    _send(msg, chat_id)
    log("liaison", "Job started notification sent")


def plan_ready(plan: dict, chat_id: str = None):
    files = "\n".join(f"  • `{f['path']}`" for f in plan["files"])
    msg = (
        f"📐 *Architecture Ready*\n\n"
        f"📝 {plan['summary']}\n"
        f"💻 Language: `{plan['language']}`\n\n"
        f"*Files to build:*\n{files}\n\n"
        f"✍️ Coder is writing code..."
    )
    _send(msg, chat_id)


def attempt_started(attempt: int, max_retries: int, chat_id: str = None):
    msg = f"🔨 *Coding Attempt {attempt}/{max_retries}*\n\nCoder is writing... Auditor will test it next."
    _send(msg, chat_id)


def attempt_failed(attempt: int, reason: str, retries_left: int, chat_id: str = None):
    msg = (
        f"⚠️ *Attempt {attempt} Failed*\n\n"
        f"❌ {reason[:300]}\n\n"
        f"🔄 {retries_left} attempt(s) remaining. Coder is fixing..."
    )
    _send(msg, chat_id)


def job_complete(task: str, attempt: int, run_cmd: str, chat_id: str = None):
    msg = (
        f"✅ *Job Complete!*\n\n"
        f"📋 `{task[:150]}`\n\n"
        f"🎯 Passed after *{attempt}* attempt(s)\n"
        f"▶️ Run: `{run_cmd}`\n\n"
        f"📦 Files are ready in your output folder."
    )
    _send(msg, chat_id)
    log("liaison", "Completion notification sent")


def job_failed(task: str, attempts: int, last_error: str, chat_id: str = None):
    msg = (
        f"💀 *Job Failed*\n\n"
        f"📋 `{task[:150]}`\n\n"
        f"Exhausted all *{attempts}* attempts.\n"
        f"Last error: `{last_error[:300]}`\n\n"
        f"Check the log file for full details."
    )
    _send(msg, chat_id)
    log("liaison", "Failure notification sent")


def send_zip(zip_path: str, task: str, chat_id: str = None):
    caption = f"📦 *Your app is ready!*\n`{task[:100]}`"
    ok = _send_document(zip_path, caption, chat_id)
    if ok:
        log("liaison", f"Zip sent: {zip_path}")
    else:
        log("liaison", "Zip send failed")
    return ok


def info(msg: str, chat_id: str = None):
    _send(f"ℹ️ {msg}", chat_id)


def ask(question: str, chat_id: str = None):
    """Ask user for input — they reply to the bot."""
    _send(f"❓ *Input needed:*\n\n{question}", chat_id)

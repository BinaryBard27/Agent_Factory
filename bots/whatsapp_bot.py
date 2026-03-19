"""
WhatsApp Bot — via Twilio WhatsApp Sandbox.
Runs as a lightweight Flask webhook server.

Setup:
1. Sign up at https://www.twilio.com (free tier works)
2. Enable WhatsApp Sandbox in Twilio Console
3. Set your TWILIO_* vars in .env
4. Expose this server: ngrok http 8081
5. Set webhook URL in Twilio to: https://your-ngrok-url/whatsapp

Or use with a real Twilio number for production.
"""
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from config.settings import (
    TELEGRAM_BOT_TOKEN  # We reuse the Anthropic key; Twilio keys come from env
)
from core.logger import log
from core import job_queue as Queue
import state.manager as State


TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")  # e.g. whatsapp:+14155238886
WHATSAPP_PORT       = int(os.getenv("WHATSAPP_PORT", "8081"))


def send_whatsapp(to: str, body: str):
    """Send a WhatsApp message via Twilio REST API."""
    if not TWILIO_ACCOUNT_SID:
        log("whatsapp", "Twilio not configured — skipping send")
        return

    import urllib.request
    import urllib.parse
    import base64

    url  = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = urllib.parse.urlencode({
        "From": TWILIO_WHATSAPP_FROM,
        "To":   f"whatsapp:{to}" if not to.startswith("whatsapp:") else to,
        "Body": body
    }).encode("utf-8")

    creds = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
    req   = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Basic {creds}",
        "Content-Type":  "application/x-www-form-urlencoded"
    })
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log("whatsapp", f"Send failed: {e}")


def _handle_incoming(from_number: str, body: str):
    body = body.strip()
    log("whatsapp", f"[{from_number}] {body[:80]}")

    if body.lower().startswith("/status"):
        jobs = State.list_jobs()
        if not jobs:
            send_whatsapp(from_number, "📭 No jobs found.")
            return
        lines = ["📊 Recent Jobs\n"]
        for j in jobs[-5:]:
            icon = {"done": "✅", "failed": "💀", "code": "⚙️"}.get(j["stage"], "❓")
            lines.append(f"{icon} {j['task'][:40]} — {j['stage']}")
        send_whatsapp(from_number, "\n".join(lines))
        return

    if body.lower().startswith("/help"):
        send_whatsapp(from_number,
            "🏭 Personal Agentic Factory\n\n"
            "Just send a message describing what you want built.\n\n"
            "Commands:\n"
            "/status — see recent jobs\n"
            "/help — this message"
        )
        return

    # Default — treat as build task
    task = body.lstrip("/build").strip()
    pos  = Queue.enqueue(task, chat_id=None)  # WhatsApp notifications sent manually below
    send_whatsapp(from_number,
        f"🏭 Got it!\n\n"
        f"Building: {task[:100]}\n\n"
        f"Queue position: {pos}\n"
        f"I'll message you when it's done."
    )

    # Run in background and notify on completion
    def _notify_on_done():
        import core.orchestrator as Factory
        result = Factory.run(task)
        if result["success"]:
            send_whatsapp(from_number,
                f"✅ Done in {result['attempts']} attempt(s)!\n\n"
                f"Run: {result['run']}\n"
                f"Output folder: {result['out_dir']}"
            )
        else:
            send_whatsapp(from_number,
                f"💀 Build failed after {result.get('attempts', 0)} attempts.\n"
                f"Error: {result.get('last_error', 'unknown')[:200]}"
            )

    threading.Thread(target=_notify_on_done, daemon=True).start()


class WhatsAppHandler(BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass

    def do_POST(self):
        length   = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8")
        params   = parse_qs(raw_body)

        from_num = params.get("From", [""])[0]
        body     = params.get("Body", [""])[0]

        if from_num and body:
            threading.Thread(
                target=_handle_incoming,
                args=(from_num, body),
                daemon=True
            ).start()

        # Twilio expects a TwiML response
        twiml = "<?xml version='1.0'?><Response></Response>"
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", len(twiml))
        self.end_headers()
        self.wfile.write(twiml.encode())

    def do_GET(self):
        msg = b"PAF WhatsApp Webhook is running."
        self.send_response(200)
        self.send_header("Content-Length", len(msg))
        self.end_headers()
        self.wfile.write(msg)


def run(daemon=True):
    if not TWILIO_ACCOUNT_SID:
        log("whatsapp", "⚠️  TWILIO_ACCOUNT_SID not set — WhatsApp bot disabled")
        return None

    server = HTTPServer(("0.0.0.0", WHATSAPP_PORT), WhatsAppHandler)
    log("whatsapp", f"✅ WhatsApp webhook on port {WHATSAPP_PORT}")

    if daemon:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    else:
        server.serve_forever()


if __name__ == "__main__":
    run(daemon=False)

#!/usr/bin/env python3
"""
Personal Agentic Factory — Entry Point

Modes:
  python main.py              → Start everything (bot + dashboard + whatsapp)
  python main.py bot          → Telegram bot only
  python main.py build <task> → Run a single job from CLI
  python main.py status       → List all jobs
  python main.py resume <task>→ Resume a crashed job
  python main.py dashboard    → Web dashboard only (http://localhost:8080)
"""
import sys
import os
import time
import signal

sys.path.insert(0, os.path.dirname(__file__))


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║          🏭  PERSONAL AGENTIC FACTORY  🏭                 ║
║     Architect → Coder → Auditor → Your App               ║
║                                                          ║
║  Text it from your phone. Come home to working code.     ║
╚══════════════════════════════════════════════════════════╝
""")


def cmd_all():
    """Start all services: Telegram bot + Dashboard + WhatsApp webhook."""
    from core.logger import log
    from core.dashboard import run as start_dashboard
    from bots.whatsapp_bot import run as start_whatsapp
    from bots.telegram_bot import run as start_telegram

    print_banner()
    log("main", "Starting all services...")

    # Dashboard (background thread)
    start_dashboard(daemon=True)

    # WhatsApp webhook (background thread, only if configured)
    start_whatsapp(daemon=True)

    # Telegram bot (blocking — main thread)
    log("main", "All services up. Telegram bot now polling...")
    log("main", "Dashboard → http://localhost:8080")
    start_telegram()


def cmd_bot():
    from core.logger import log
    from bots.telegram_bot import run
    print_banner()
    log("main", "Starting Telegram bot only...")
    run()


def cmd_dashboard():
    from core.logger import log
    from core.dashboard import run
    print_banner()
    log("main", "Starting dashboard only...")
    run(daemon=False)


def cmd_build(task: str):
    import core.orchestrator as Factory
    from core.logger import log
    print_banner()
    log("main", f"CLI build: {task}")
    result = Factory.run(task)
    if result["success"]:
        print(f"\n✅ Done in {result['attempts']} attempt(s)")
        print(f"📁 Output : {result['out_dir']}")
        print(f"▶️  Run    : cd {result['out_dir']} && {result['run']}")
        if result.get("zip"):
            print(f"📦 Zip    : {result['zip']}")
    else:
        print(f"\n❌ Failed after {result.get('attempts', 0)} attempt(s)")
        print(f"   Error: {result.get('last_error', 'unknown')}")
        sys.exit(1)


def cmd_status():
    import state.manager as State
    jobs = State.list_jobs()
    if not jobs:
        print("No jobs found.")
        return

    print(f"\n{'ID':10s} {'Stage':12s} {'Att':4s} {'Updated':20s} Task")
    print("─" * 80)
    for j in sorted(jobs, key=lambda x: x.get("_updated",""), reverse=True):
        icon = {"done":"✅","failed":"💀","code":"⚙️","architect":"📐"}.get(j["stage"],"❓")
        upd  = j.get("_updated","")[:19].replace("T"," ")
        print(f"{j.get('_job_id','?'):10s} {icon}{j['stage']:11s} {j['attempt']:<4d} {upd:20s} {j['task'][:35]}")


def cmd_resume(task: str):
    import state.manager as State
    state = State.load(task)
    if not state:
        print(f"❌ No saved state for: {task}")
        sys.exit(1)
    print(f"⚡ Resuming at stage: {state['stage']}")
    cmd_build(task)


# ── Graceful shutdown ─────────────────────────────────────────────────────────
def _handle_signal(sig, frame):
    print("\n\n👋 Shutting down factory...")
    sys.exit(0)

signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    cmd  = args[0].lower() if args else "all"

    # Soft config check
    try:
        from config.settings import validate
        validate()
    except EnvironmentError as e:
        print(f"\n⚠️  {e}\n")
        if cmd in ("all", "bot"):
            sys.exit(1)

    if cmd in ("all", "start"):
        cmd_all()
    elif cmd == "bot":
        cmd_bot()
    elif cmd == "dashboard":
        cmd_dashboard()
    elif cmd == "build":
        if len(args) < 2:
            print('Usage: python main.py build "your task here"')
            sys.exit(1)
        cmd_build(" ".join(args[1:]))
    elif cmd == "status":
        cmd_status()
    elif cmd in ("resume", "retry"):
        if len(args) < 2:
            print('Usage: python main.py resume "your original task"')
            sys.exit(1)
        cmd_resume(" ".join(args[1:]))
    else:
        # Treat as a direct task
        cmd_build(" ".join(args))

"""
Orchestrator — The main factory loop.
Architect → Coder → Auditor → (retry) → Done
Full state recovery on crash/resume.
"""
import os
import shutil
import zipfile
import time
from pathlib import Path
from datetime import datetime

import state.manager as State
import core.architect as Architect
import core.coder     as Coder
import core.auditor   as Auditor
import liaison.messenger as Liaison
from core.logger import log, set_job
from config.settings import MAX_RETRIES, OUTPUT_BASE_DIR


# ── File I/O ──────────────────────────────────────────────────────────────────
def _write_files(files: dict, out_dir: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for rel_path, content in files.items():
        full = Path(out_dir) / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        log("writer", f"Wrote: {rel_path}")


def _zip_output(out_dir: str, job_id: str) -> str:
    zip_path = f"{out_dir}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in Path(out_dir).rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(out_dir))
    log("writer", f"Zipped: {zip_path}")
    return zip_path


# ── Main ──────────────────────────────────────────────────────────────────────
def run(task: str, chat_id: str = None) -> dict:
    """
    Returns:
        {"success": bool, "out_dir": str, "zip": str, "attempts": int}
    """
    # ── State recovery ──
    state = State.load(task)
    if state and state.get("stage") not in ("done", "failed"):
        log("factory", f"⚡ RESUMING job {state['_job_id']} at stage: {state['stage']}")
        Liaison.info(f"Resuming previous job at stage: {state['stage']}", chat_id)
    else:
        state = State.fresh(task)
        log("factory", f"NEW JOB: {state['_job_id']}")

    set_job(state["_job_id"])
    out_dir = str(Path(OUTPUT_BASE_DIR) / state["_job_id"])

    # ── Header ──
    log("factory", "=" * 60)
    log("factory", f"TASK: {task}")
    log("factory", "=" * 60)
    Liaison.job_started(task, chat_id)

    # ── Stage 1: Architect ──
    if state["stage"] == "architect":
        try:
            plan = Architect.run(task)
            state["plan"]  = plan
            state["stage"] = "code"
            State.save(task, state)
            Liaison.plan_ready(plan, chat_id)
        except Exception as e:
            log("factory", f"Architect failed: {e}")
            Liaison.job_failed(task, 0, str(e), chat_id)
            state["stage"] = "failed"
            State.save(task, state)
            return {"success": False, "error": str(e)}

    plan = state["plan"]

    # ── Stage 2+3: Code → Audit loop ──
    while state["attempt"] < MAX_RETRIES:
        attempt = state["attempt"] + 1
        log("factory", f"─── Attempt {attempt}/{MAX_RETRIES} ───")
        Liaison.attempt_started(attempt, MAX_RETRIES, chat_id)

        # Code
        try:
            code_result = Coder.run(task, plan, state["error_history"])
        except Exception as e:
            log("factory", f"Coder crashed: {e}")
            state["error_history"].append(f"Coder exception: {str(e)}")
            state["attempt"] += 1
            State.save(task, state)
            continue

        # Write files fresh each attempt
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        _write_files(code_result["files"], out_dir)
        state["files"] = code_result["files"]
        State.save(task, state)

        # Audit
        passed, reason = Auditor.run(plan, out_dir)

        if passed:
            # ── SUCCESS ──
            log("factory", "=" * 60)
            log("factory", f"✅ COMPLETE in {attempt} attempt(s)")
            log("factory", f"Output: {out_dir}/")
            log("factory", f"Run: cd {out_dir} && {plan['run_command']}")
            log("factory", "=" * 60)

            zip_path = _zip_output(out_dir, state["_job_id"])
            Liaison.job_complete(task, attempt, plan["run_command"], chat_id)
            Liaison.send_zip(zip_path, task, chat_id)

            state["stage"]   = "done"
            state["zip"]     = zip_path
            state["out_dir"] = out_dir
            State.save(task, state)

            return {
                "success":  True,
                "out_dir":  out_dir,
                "zip":      zip_path,
                "attempts": attempt,
                "run":      plan["run_command"]
            }

        # Failed — record and retry
        log("factory", f"Attempt {attempt} failed. Retrying...")
        state["error_history"].append(reason)
        state["attempt"] += 1
        State.save(task, state)
        Liaison.attempt_failed(attempt, reason, MAX_RETRIES - state["attempt"], chat_id)
        time.sleep(1)

    # ── All retries exhausted ──
    last = state["error_history"][-1] if state["error_history"] else "Unknown"
    log("factory", f"❌ FAILED after {MAX_RETRIES} attempts")
    Liaison.job_failed(task, MAX_RETRIES, last, chat_id)
    state["stage"] = "failed"
    State.save(task, state)

    return {"success": False, "attempts": MAX_RETRIES, "last_error": last}

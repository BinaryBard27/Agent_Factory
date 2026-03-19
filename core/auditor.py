"""
Agent 3 — Auditor
Executes the code (in Docker or subprocess) and verifies output.
Returns (passed: bool, reason: str).
"""
import subprocess
import os
import json
import anthropic
from pathlib import Path
from config.settings import (
    ANTHROPIC_API_KEY, MODEL, MAX_TOKENS,
    USE_DOCKER, DOCKER_IMAGE_PYTHON, DOCKER_IMAGE_NODE, SANDBOX_TIMEOUT
)
from core.logger import log

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── Docker check ──────────────────────────────────────────────────────────────
def _docker_available() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


# ── Run in Docker sandbox ────────────────────────────────────────────────────
def _run_docker(plan: dict, work_dir: str) -> tuple[int, str, str]:
    lang    = plan["language"]
    image   = DOCKER_IMAGE_NODE if lang == "typescript" else DOCKER_IMAGE_PYTHON
    abs_dir = str(Path(work_dir).resolve())

    # Install command inside container
    install_cmd = plan.get("install_command", "")
    run_cmd     = plan["run_command"]

    # Combine install + run
    if install_cmd:
        shell_cmd = f"cd /app && {install_cmd} --quiet 2>/dev/null ; {run_cmd}"
    else:
        shell_cmd = f"cd /app && {run_cmd}"

    docker_cmd = [
        "docker", "run", "--rm",
        "--network=host",
        "--memory=512m",
        "--cpus=1",
        "-v", f"{abs_dir}:/app",
        image,
        "sh", "-c", shell_cmd
    ]

    log("auditor", f"Docker: {image}")
    result = subprocess.run(
        docker_cmd,
        capture_output=True, text=True,
        timeout=SANDBOX_TIMEOUT
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ── Run in subprocess (fallback) ─────────────────────────────────────────────
def _run_subprocess(plan: dict, work_dir: str) -> tuple[int, str, str]:
    log("auditor", "Subprocess mode (Docker not available)")

    if plan.get("install_command"):
        log("auditor", f"Installing: {plan['install_command']}")
        subprocess.run(
            plan["install_command"],
            shell=True, capture_output=True,
            cwd=work_dir, timeout=120
        )

    result = subprocess.run(
        plan["run_command"],
        shell=True, capture_output=True, text=True,
        cwd=work_dir, timeout=SANDBOX_TIMEOUT
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ── AI verdict ────────────────────────────────────────────────────────────────
def _ai_verdict(criteria: str, stdout: str, stderr: str) -> tuple[bool, str]:
    system = """You are a QA engineer. Given success criteria and program output, decide pass/fail.
Respond ONLY with JSON: {"passed": true or false, "reason": "one sentence explanation"}"""

    user = f"""Success criteria: {criteria}

STDOUT:
{stdout or '(empty)'}

STDERR:
{stderr or '(empty)'}

Did the program meet the success criteria?"""

    response = client.messages.create(
        model=MODEL, max_tokens=256, system=system,
        messages=[{"role": "user", "content": user}]
    )
    raw = response.content[0].text.strip().strip("```json").strip("```").strip()
    v   = json.loads(raw)
    return v["passed"], v["reason"]


# ── Main entry ────────────────────────────────────────────────────────────────
def run(plan: dict, work_dir: str) -> tuple[bool, str]:
    log("auditor", "Executing code...")

    try:
        use_docker = USE_DOCKER and _docker_available()

        if use_docker:
            code, stdout, stderr = _run_docker(plan, work_dir)
        else:
            code, stdout, stderr = _run_subprocess(plan, work_dir)

        log("auditor", f"Exit: {code}")
        if stdout: log("auditor", f"STDOUT: {stdout[:400]}")
        if stderr: log("auditor", f"STDERR: {stderr[:300]}")

        if code != 0:
            error = f"Process exited with code {code}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            log("auditor", "❌ Non-zero exit")
            return False, error

        passed, reason = _ai_verdict(plan["success_criteria"], stdout, stderr)
        icon = "✅" if passed else "❌"
        log("auditor", f"{icon} {reason}")
        return passed, reason

    except subprocess.TimeoutExpired:
        msg = f"Timed out after {SANDBOX_TIMEOUT}s. Program must exit on its own."
        log("auditor", f"❌ {msg}")
        return False, msg

    except Exception as e:
        msg = f"Execution error: {str(e)}"
        log("auditor", f"❌ {msg}")
        return False, msg

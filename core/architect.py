"""
Agent 1 — Architect
Turns a vague task into a precise technical spec.
"""
import json
import anthropic
from config.settings import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS
from core.logger import log

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = """You are a senior software architect. Given a task, produce a precise technical plan.

Respond ONLY with a valid JSON object — no markdown fences, no explanation, just raw JSON.

Schema:
{
  "summary":          "one-line description of what this builds",
  "language":         "python | typescript",
  "files": [
    {"path": "relative/path/file.py", "purpose": "what this file does"}
  ],
  "entry_point":       "main file to execute",
  "run_command":       "python main.py  OR  node index.js  etc",
  "dependencies":      ["package1", "package2"],
  "install_command":   "pip install package1 package2  OR  npm install",
  "success_criteria":  "exact description of stdout/behavior that proves it works"
}

Rules:
- Prefer minimal dependencies. Use stdlib when possible.
- run_command must be a single shell command that exits after producing output.
- success_criteria must be checkable from stdout/stderr alone.
- No interactive programs. Apps must run headlessly and exit.
"""


def run(task: str) -> dict:
    log("architect", f"Designing: {task[:80]}...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Task: {task}"}]
    )
    raw = response.content[0].text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    plan = json.loads(raw)
    log("architect", f"Plan ready — {plan['language']} | {len(plan['files'])} file(s) | {plan['summary']}")
    return plan

"""
Agent 2 — Coder
Writes complete, working code for every file in the plan.
On retry, it receives the error history and must fix the bugs.
"""
import json
import anthropic
from config.settings import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS
from core.logger import log

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = """You are an expert software engineer. Write complete, production-quality code.

Respond ONLY with a valid JSON object — no markdown, no explanation, just raw JSON.

Schema:
{
  "files": {
    "path/to/file.py": "full file content as a string",
    "path/to/other.py": "full file content as a string"
  }
}

Strict rules:
- Write EVERY file completely. Zero placeholders. Zero TODOs. Zero '...' shortcuts.
- Code must run immediately without any modification.
- All imports must be from the approved dependency list or stdlib.
- Programs must exit on their own (no infinite loops, no input() prompts).
- Handle all exceptions internally — never let the program crash with a traceback.
- Output must match the success criteria exactly.
"""


def run(task: str, plan: dict, error_history: list[str]) -> dict:
    is_retry = len(error_history) > 0
    log("coder", f"{'Fixing bugs' if is_retry else 'Writing code'} (attempt {len(error_history)+1})...")

    file_list = "\n".join(
        f"  - {f['path']}: {f['purpose']}" for f in plan["files"]
    )

    error_block = ""
    if error_history:
        recent = error_history[-3:]   # Last 3 failures for context
        errors = "\n\n---\n".join(recent)
        error_block = f"""
⚠️  PREVIOUS ATTEMPTS FAILED. You must fix these specific errors — do NOT repeat them:

{errors}

Study the errors carefully. Fix the root cause, not just the symptom.
"""

    user = f"""Task: {task}

Plan:
  Summary:          {plan['summary']}
  Language:         {plan['language']}
  Entry point:      {plan['entry_point']}
  Run command:      {plan['run_command']}
  Dependencies:     {', '.join(plan['dependencies'])}
  Success criteria: {plan['success_criteria']}

Files to create:
{file_list}
{error_block}
Write all files completely. No shortcuts."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}]
    )
    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    result = json.loads(raw)
    log("coder", f"Generated {len(result['files'])} file(s): {', '.join(result['files'].keys())}")
    return result

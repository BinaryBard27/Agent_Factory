"""
Web Dashboard — Monitor all factory jobs from your browser.
Runs on http://localhost:8080
No framework needed — pure stdlib HTTP server.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import state.manager as State
from config.settings import LOG_DIR, OUTPUT_BASE_DIR
from core.logger import log


# ── HTML Templates ─────────────────────────────────────────────────────────────
def _html_page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — PAF</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Courier New', monospace; background: #0d0d0d; color: #e0e0e0; padding: 20px; }}
  h1 {{ color: #00ff88; font-size: 1.4em; margin-bottom: 20px; border-bottom: 1px solid #222; padding-bottom: 10px; }}
  h2 {{ color: #00aaff; font-size: 1.1em; margin: 20px 0 10px; }}
  .job-card {{ background: #111; border: 1px solid #222; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
  .job-card:hover {{ border-color: #333; }}
  .stage {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }}
  .stage-done {{ background: #003320; color: #00ff88; }}
  .stage-failed {{ background: #330000; color: #ff4444; }}
  .stage-code {{ background: #002233; color: #00aaff; }}
  .stage-architect {{ background: #221100; color: #ffaa00; }}
  .task {{ font-size: 0.95em; margin: 8px 0; color: #ccc; }}
  .meta {{ font-size: 0.75em; color: #666; margin-top: 8px; }}
  .log-box {{ background: #080808; border: 1px solid #222; border-radius: 6px; padding: 14px;
              font-size: 0.78em; line-height: 1.6; white-space: pre-wrap; max-height: 500px;
              overflow-y: auto; color: #aaa; }}
  .log-box .ok  {{ color: #00ff88; }}
  .log-box .err {{ color: #ff4444; }}
  .log-box .inf {{ color: #00aaff; }}
  a {{ color: #00aaff; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .btn {{ display: inline-block; padding: 6px 14px; background: #1a1a1a; border: 1px solid #333;
          border-radius: 6px; color: #ccc; font-size: 0.8em; cursor: pointer; text-decoration: none; }}
  .btn:hover {{ background: #222; color: #fff; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; }}
  .badge {{ background: #00ff8822; color: #00ff88; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; }}
  .empty {{ color: #444; text-align: center; padding: 40px; font-size: 0.9em; }}
  .refresh {{ font-size: 0.75em; color: #444; }}
</style>
<script>
  // Auto-refresh active jobs every 5s
  setTimeout(() => {{
    if (document.querySelector('.stage-code, .stage-architect')) {{
      location.reload();
    }}
  }}, 5000);
</script>
</head>
<body>
<h1>🏭 Personal Agentic Factory</h1>
{body}
</body>
</html>"""


def _stage_badge(stage: str) -> str:
    cls = f"stage-{stage}"
    icons = {"done": "✅", "failed": "💀", "code": "⚙️", "architect": "📐"}
    icon = icons.get(stage, "❓")
    return f'<span class="stage {cls}">{icon} {stage}</span>'


def _jobs_page() -> str:
    jobs = State.list_jobs()
    if not jobs:
        body = '<div class="empty">No jobs yet. Send a message to your Telegram bot or run:<br><br><code>python main.py build "your task"</code></div>'
        return _html_page("Dashboard", body)

    jobs_sorted = sorted(jobs, key=lambda j: j.get("_updated", ""), reverse=True)

    cards = []
    for j in jobs_sorted:
        job_id  = j.get("_job_id", "?")
        stage   = j.get("stage", "?")
        attempt = j.get("attempt", 0)
        task    = j.get("task", "")[:120]
        updated = j.get("_updated", "")[:19].replace("T", " ")
        errors  = len(j.get("error_history", []))

        log_link   = f'<a class="btn" href="/logs/{job_id}">📄 Logs</a>'
        files_link = ""
        if stage == "done":
            files_link = f'<a class="btn" href="/files/{job_id}">📁 Files</a>'

        card = f"""<div class="job-card">
  <div class="header">
    <div>{_stage_badge(stage)} &nbsp; <code style="font-size:0.8em;color:#555">{job_id}</code></div>
    <div>{log_link} {files_link}</div>
  </div>
  <div class="task">{task}</div>
  <div class="meta">Attempt {attempt} &nbsp;·&nbsp; {errors} error(s) &nbsp;·&nbsp; Updated {updated}</div>
</div>"""
        cards.append(card)

    total   = len(jobs)
    done    = sum(1 for j in jobs if j.get("stage") == "done")
    active  = sum(1 for j in jobs if j.get("stage") in ("code", "architect"))

    summary = f"""
<div style="display:flex;gap:16px;margin-bottom:20px;font-size:0.8em;color:#666">
  <span>Total: <b style="color:#ccc">{total}</b></span>
  <span>Done: <b style="color:#00ff88">{done}</b></span>
  <span>Active: <b style="color:#00aaff">{active}</b></span>
  <span style="margin-left:auto" class="refresh">Auto-refreshes when jobs are active</span>
</div>
"""

    body = summary + "\n".join(cards)
    return _html_page("Dashboard", body)


def _log_page(job_id: str) -> str:
    log_path = Path(LOG_DIR) / f"{job_id}.log"
    if not log_path.exists():
        return _html_page("Log", f'<div class="empty">Log not found: {job_id}</div>')

    with open(log_path) as f:
        raw = f.read()

    # Colorize key patterns
    lines = []
    for line in raw.split("\n"):
        if "✅" in line or "COMPLETE" in line or "PASSED" in line:
            lines.append(f'<span class="ok">{line}</span>')
        elif "❌" in line or "FAILED" in line or "failed" in line or "error" in line.lower():
            lines.append(f'<span class="err">{line}</span>')
        elif "[ARCHITECT]" in line or "[CODER]" in line or "[AUDITOR]" in line:
            lines.append(f'<span class="inf">{line}</span>')
        else:
            lines.append(line)

    colored = "\n".join(lines)
    body = f"""
<a class="btn" href="/">← Back</a>
<h2>Job Log: {job_id}</h2>
<div class="log-box">{colored}</div>
"""
    return _html_page(f"Log {job_id}", body)


def _files_page(job_id: str) -> str:
    job_dir = Path(OUTPUT_BASE_DIR) / job_id
    if not job_dir.exists():
        return _html_page("Files", f'<div class="empty">Output dir not found for job {job_id}</div>')

    file_list = list(job_dir.rglob("*"))
    files_html = []
    for fp in sorted(file_list):
        if fp.is_file():
            rel = fp.relative_to(job_dir)
            size = fp.stat().st_size
            files_html.append(
                f'<div class="job-card"><a href="/source/{job_id}/{rel}">{rel}</a>'
                f'<span style="float:right;color:#555;font-size:0.8em">{size} bytes</span></div>'
            )

    body = f"""
<a class="btn" href="/">← Back</a>
<h2>Output Files: {job_id}</h2>
{"".join(files_html) or '<div class="empty">No files found.</div>'}
"""
    return _html_page(f"Files {job_id}", body)


def _source_page(job_id: str, rel_path: str) -> str:
    full = Path(OUTPUT_BASE_DIR) / job_id / rel_path
    if not full.exists():
        return _html_page("Source", '<div class="empty">File not found</div>')

    with open(full, errors="replace") as f:
        content = f.read()

    escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = f"""
<a class="btn" href="/files/{job_id}">← Back</a>
<h2>{rel_path}</h2>
<div class="log-box">{escaped}</div>
"""
    return _html_page(rel_path, body)


# ── HTTP Handler ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass  # Suppress default access logs

    def _respond(self, code: int, body: str, content_type="text/html"):
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", len(encoded))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)
        parts  = [p for p in parsed.path.strip("/").split("/") if p]

        if not parts:
            self._respond(200, _jobs_page())

        elif parts[0] == "logs" and len(parts) == 2:
            self._respond(200, _log_page(parts[1]))

        elif parts[0] == "files" and len(parts) == 2:
            self._respond(200, _files_page(parts[1]))

        elif parts[0] == "source" and len(parts) >= 3:
            rel = "/".join(parts[2:])
            self._respond(200, _source_page(parts[1], rel))

        elif parts[0] == "api" and parts[1:] == ["jobs"]:
            jobs = State.list_jobs()
            self._respond(200, json.dumps(jobs, indent=2), "application/json")

        else:
            self._respond(404, _html_page("404", '<div class="empty">Page not found</div>'))


# ── Server ─────────────────────────────────────────────────────────────────────
def run(host="0.0.0.0", port=8080, daemon=True):
    server = HTTPServer((host, port), Handler)
    log("dashboard", f"✅ Dashboard running at http://localhost:{port}")

    if daemon:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    else:
        server.serve_forever()


if __name__ == "__main__":
    run(daemon=False)

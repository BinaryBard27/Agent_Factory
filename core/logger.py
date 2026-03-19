"""
Shared logger — prints to console + writes to per-job log file.
"""
import os
from datetime import datetime
from pathlib import Path
from config.settings import LOG_DIR


_job_id_ctx: str = "global"


def set_job(job_id: str):
    global _job_id_ctx
    _job_id_ctx = job_id
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


def log(agent: str, msg: str):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{agent.upper():12s}] {msg}"
    print(line, flush=True)
    log_file = Path(LOG_DIR) / f"{_job_id_ctx}.log"
    with open(log_file, "a") as f:
        f.write(line + "\n")

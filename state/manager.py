"""
State Manager — checkpoint every stage, resume after any crash.
"""
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from config.settings import STATE_DIR


def _job_id(task: str) -> str:
    h = hashlib.md5(task.encode()).hexdigest()[:8]
    return h


def _path(job_id: str) -> Path:
    Path(STATE_DIR).mkdir(parents=True, exist_ok=True)
    return Path(STATE_DIR) / f"{job_id}.json"


def save(task: str, state: dict):
    job_id = _job_id(task)
    state["_job_id"]  = job_id
    state["_updated"] = datetime.now().isoformat()
    with open(_path(job_id), "w") as f:
        json.dump(state, f, indent=2)


def load(task: str) -> dict | None:
    p = _path(_job_id(task))
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


def clear(task: str):
    p = _path(_job_id(task))
    if p.exists():
        p.unlink()


def fresh(task: str) -> dict:
    return {
        "task":          task,
        "stage":         "architect",   # architect | code | done | failed
        "attempt":       0,
        "plan":          None,
        "error_history": [],
        "files":         {},
        "started_at":    datetime.now().isoformat(),
    }


def list_jobs() -> list[dict]:
    Path(STATE_DIR).mkdir(parents=True, exist_ok=True)
    jobs = []
    for f in Path(STATE_DIR).glob("*.json"):
        with open(f) as fh:
            jobs.append(json.load(fh))
    return jobs

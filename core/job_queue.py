"""
Job Queue — Serializes concurrent build requests.
If two Telegram messages arrive at once, they queue, not collide.
"""
import threading
import queue
import time
from core.logger import log
import core.orchestrator as Factory


_q: queue.Queue = queue.Queue()
_lock           = threading.Lock()
_running        = False
_worker_thread  = None


def _worker():
    global _running
    while True:
        try:
            item = _q.get(timeout=5)
        except queue.Empty:
            with _lock:
                if _q.empty():
                    _running = False
            continue

        task    = item["task"]
        chat_id = item.get("chat_id")
        log("queue", f"Starting job: {task[:60]}")

        try:
            Factory.run(task, chat_id=chat_id)
        except Exception as e:
            log("queue", f"Job crashed: {e}")
        finally:
            _q.task_done()
            log("queue", f"Job done. {_q.qsize()} remaining.")


def _ensure_worker():
    global _running, _worker_thread
    with _lock:
        if not _running:
            _running = True
            _worker_thread = threading.Thread(target=_worker, daemon=True)
            _worker_thread.start()
            log("queue", "Worker started")


def enqueue(task: str, chat_id: str = None) -> int:
    """Add a job to the queue. Returns queue position (1-indexed)."""
    _q.put({"task": task, "chat_id": chat_id})
    _ensure_worker()
    pos = _q.qsize()
    log("queue", f"Enqueued: '{task[:50]}' — position {pos}")
    return pos


def size() -> int:
    return _q.qsize()


def is_busy() -> bool:
    return _running and not _q.empty()

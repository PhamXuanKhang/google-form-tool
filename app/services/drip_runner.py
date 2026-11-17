"""Scheduled ("drip") runs: send each planned response at its own time.

A runner works through one run's planned rows, sending only rows whose
``due_at`` has passed, at most ``max_per_tick`` per tick. The clock, the sleep
function and the batch sender are injectable so tests run without real time
or a browser. Every state change goes to the run store first, so a hard kill
loses at most the rows being sent; on the next start ``recover_interrupted_runs``
marks those rows unknown and the run interrupted, and nothing is resent until
the user resumes.
"""
from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from app.domain.drip_schedule import due_rows, next_due, respread
from app.logging_config import logger
from app.services.run_store import ROW_IN_FLIGHT, ROW_PLANNED, ROW_UNKNOWN

DEFAULT_TICK_SECONDS = 5.0
UNFINISHED_RUN_STATUSES = ("pending", "running", "paused")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# send_batch(rows, on_row_result) sends the given rows and calls
# on_row_result(index, status, error, started_at, finished_at) for each.
SendBatch = Callable[[List[Dict[str, Any]], Callable], None]


class DripRunner:
    def __init__(self, *, store, header: Dict[str, Any], send_batch: SendBatch,
                 clock: Callable[[], datetime] = utc_now, sleep: Optional[Callable[[float], None]] = None,
                 tick_seconds: float = DEFAULT_TICK_SECONDS, max_per_tick: Optional[int] = None):
        self.store = store
        self.header = header
        self.run_id = header.get("run_id")
        self.send_batch = send_batch
        self.clock = clock
        self.tick_seconds = tick_seconds
        self._max_per_tick = max_per_tick
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._wake = threading.Event()
        self._sleep = sleep or self._wake.wait
        self._lock = threading.RLock()
        self.rows: Dict[int, Dict[str, Any]] = {}
        self.started = time.monotonic()
        self.final_status: Optional[str] = None
        self.plan = None  # not a plain submitter; kept for code that checks the attribute

    @property
    def max_per_tick(self) -> int:
        # Read from the header each time: a new run's header is set after registration.
        return self._max_per_tick or max(1, int(self.header.get("threads") or 1))

    # ------------------------------------------------------------- control

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def pause(self) -> None:
        self._pause.set()
        self._wake.set()

    @property
    def stop_flag(self):
        return self._stop

    # -------------------------------------------------------------- status

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            rows = list(self.rows.values())
        success = sum(1 for row in rows if row["status"] == "success")
        failed = sum(1 for row in rows if row["status"] in ("failed", ROW_UNKNOWN))
        completed = success + failed
        return {
            "running": self.final_status is None,
            "total": len(rows),
            "completed": completed,
            "success": success,
            "failed": failed,
            "current_threads": 0,
            "elapsed_time": int(time.monotonic() - self.started),
            "success_rate": (success / completed * 100) if completed else 0,
            "warning": None,
            "scheduled": True,
            "paused": self._pause.is_set(),
            "next_due_at": next_due(rows),
            "run_status": self.final_status or "running",
        }

    # ----------------------------------------------------------------- run

    def _record(self, index, status, error, started_at, finished_at) -> None:
        self.store.record_result(self.run_id, index, status, error, started_at, finished_at)
        with self._lock:
            if index in self.rows:
                self.rows[index]["status"] = status

    def _respread(self, rows: List[Dict[str, Any]], now: datetime) -> None:
        window_end = datetime.fromisoformat(self.header["schedule"]["window_end"])
        times = respread(len(rows), now, window_end, float(self.header.get("min_delay") or 0),
                         random.Random(f"{self.run_id}:{now.isoformat()}"))
        new_times = {row["index"]: when.isoformat() for row, when in zip(rows, times)}
        self.store.record_schedule(self.run_id, new_times)
        with self._lock:
            for index, due_at in new_times.items():
                self.rows[index]["due_at"] = due_at

    def abandon(self) -> None:
        """Release a runner whose run never started, so the form is not left busy."""
        self.final_status = "interrupted"
        self._run_live = False

    def load(self) -> None:
        """Read the run's rows from the store (done again when the run starts)."""
        rows = {row["index"]: row for row in self.store.load_rows(self.run_id)}
        with self._lock:
            self.rows = rows

    def run(self) -> str:
        """Send due rows until none are left, or until stopped or paused."""
        final = "interrupted"
        try:
            self.load()
            self.store.update_run(self.run_id, status="running")
            while True:
                if self._stop.is_set():
                    final = "stopped"
                    break
                if self._pause.is_set():
                    final = "paused"
                    break
                with self._lock:
                    rows = list(self.rows.values())
                if not any(row["status"] == ROW_PLANNED for row in rows):
                    final = "completed"
                    break
                now = self.clock()
                due = due_rows(rows, now, len(rows))
                if len(due) > self.max_per_tick:
                    # More is overdue than one tick may send (the computer slept, for
                    # example): send a tick's worth and spread the rest again.
                    self._respread(due[self.max_per_tick:], now)
                    due = due[:self.max_per_tick]
                if due:
                    self.send_batch(due, self._record)
                    with self._lock:
                        untouched = all(self.rows[row["index"]]["status"] == ROW_PLANNED for row in due)
                    if untouched:
                        # The sender reported nothing (the browser could not start, for
                        # example). Stop instead of retrying the same rows forever; they
                        # stay planned so the user can resume.
                        logger.error("Scheduled run %s: a batch sent no row; stopping", self.run_id)
                        break
                    continue
                upcoming = next_due(rows)
                wait = self.tick_seconds
                if upcoming:
                    wait = min(wait, max(0.0, (datetime.fromisoformat(upcoming) - now).total_seconds()))
                self._sleep(max(wait, 0.01))
        except Exception:
            logger.exception("Scheduled run %s failed", self.run_id)
            final = "interrupted"
        finally:
            self.final_status = final
            self.store.update_run(self.run_id, status=final,
                                  finished_at=datetime.now().isoformat(timespec="seconds"))
        return final


def schedule_times(header: Dict[str, Any], rows: List[Dict[str, Any]], now: datetime, rng: random.Random) -> Dict[int, str]:
    """New send times for a run's waiting rows, within what is left of its window."""
    waiting = sorted((row for row in rows if row["status"] == ROW_PLANNED), key=lambda row: row["index"])
    window_end = datetime.fromisoformat(header["schedule"]["window_end"])
    times = respread(len(waiting), now, window_end, float(header.get("min_delay") or 0), rng)
    return {row["index"]: when.isoformat() for row, when in zip(waiting, times)}


def recover_interrupted_runs(store, live_run_ids=frozenset()) -> List[str]:
    """After a restart: unfinished runs become interrupted and their in-flight
    rows unknown (they may have reached Google). Nothing is sent."""
    recovered = []
    for header in store.list_runs():
        run_id = header["run_id"]
        if header.get("status") not in UNFINISHED_RUN_STATUSES or run_id in live_run_ids:
            continue
        for row in store.load_rows(run_id):
            if row["status"] == ROW_IN_FLIGHT:
                store.record_result(run_id, row["index"], ROW_UNKNOWN, "interrupted",
                                    row.get("started_at"), None)
        store.update_run(run_id, status="interrupted")
        recovered.append(run_id)
    if recovered:
        logger.info("Marked %s unfinished run(s) as interrupted after restart", len(recovered))
    return recovered


def window_end_for(start: datetime, window_seconds: float) -> datetime:
    return start + timedelta(seconds=window_seconds)

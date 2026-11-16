"""Durable record of submission runs.

Two parts, kept apart on purpose:

- A small header per run in the ``runs`` table of ``db.json``. It is written
  only when the run is created and when its status changes.
- One append-only JSONL file per run under ``Config.RUNS_DIR``. Creating the
  run writes a ``plan`` line per row; every change in a row's state appends a
  ``result`` line. Reading merges lines by ``index`` and the latest line wins.

Per-row writes never touch ``db.json``. TinyDB rewrites the whole file on each
write, so logging hundreds of rows there would slow every write down and put
saved forms at risk if the app is killed mid-write. A torn final JSONL line
costs at most that one row update.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from tinydb import Query, TinyDB

from app.services.storage_service import _DB_WRITE_LOCK

RUNS_TABLE = "runs"

RUN_STATUSES = ("pending", "running", "paused", "interrupted", "completed", "stopped")
ROW_PLANNED = "planned"
ROW_IN_FLIGHT = "in_flight"
ROW_SUCCESS = "success"
ROW_FAILED = "failed"
ROW_UNKNOWN = "unknown"
ROW_RESULT_STATUSES = (ROW_IN_FLIGHT, ROW_SUCCESS, ROW_FAILED, ROW_UNKNOWN)

_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

_file_locks: Dict[str, threading.Lock] = {}
_file_locks_guard = threading.Lock()


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def is_valid_run_id(run_id: Any) -> bool:
    return isinstance(run_id, str) and bool(_RUN_ID_PATTERN.match(run_id))


def _lock_for(path: Path) -> threading.Lock:
    key = str(path)
    with _file_locks_guard:
        lock = _file_locks.get(key)
        if lock is None:
            lock = _file_locks[key] = threading.Lock()
        return lock


class RunStore:
    def __init__(self, db_path: str, runs_dir: str):
        self.db_path = db_path
        self.runs_dir = Path(runs_dir)

    # ------------------------------------------------------------- headers

    def create_run(
        self,
        *,
        form_id: str,
        mode: str,
        seed: int,
        threads: int,
        min_delay: float,
        max_delay: float,
        rows: Iterable[Dict[str, Any]],
        target_snapshot: Optional[Dict[str, Any]] = None,
        retry_of: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist a new run: the plan lines first, then the header."""
        run_id = uuid.uuid4().hex
        rows = list(rows)
        self._append_lines(run_id, (
            {"kind": "plan", "index": row["index"], "answers": row["answers"],
             "skipped": row.get("skipped", []),
             **({"persona_id": row["persona_id"]} if row.get("persona_id") else {})}
            for row in rows
        ))
        header = {
            "run_id": run_id,
            "form_id": form_id,
            "created_at": _now(),
            "mode": mode,
            "seed": seed,
            "total": len(rows),
            "threads": threads,
            "min_delay": min_delay,
            "max_delay": max_delay,
            "status": "pending",
            "target_snapshot": target_snapshot,
            "retry_of": retry_of,
        }
        if extra:
            header.update(extra)
        with _DB_WRITE_LOCK, TinyDB(self.db_path) as db:
            db.table(RUNS_TABLE).insert(header)
        return header

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        if not is_valid_run_id(run_id):
            return None
        with TinyDB(self.db_path) as db:
            found = db.table(RUNS_TABLE).get(Query().run_id == run_id)
        return dict(found) if found else None

    def list_runs(self, form_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with TinyDB(self.db_path) as db:
            table = db.table(RUNS_TABLE)
            found = table.search(Query().form_id == form_id) if form_id else table.all()
        runs = [dict(run) for run in found]
        runs.sort(key=lambda run: run.get("created_at") or "", reverse=True)
        return runs

    def update_run(self, run_id: str, **fields: Any) -> bool:
        """Change header fields such as ``status``. Returns False if unknown."""
        if not is_valid_run_id(run_id):
            return False
        status = fields.get("status")
        if status is not None and status not in RUN_STATUSES:
            raise ValueError(f"Unknown run status '{status}'")
        with _DB_WRITE_LOCK, TinyDB(self.db_path) as db:
            updated = db.table(RUNS_TABLE).update(fields, Query().run_id == run_id)
        return bool(updated)

    # ---------------------------------------------------------------- rows

    def record_result(
        self,
        run_id: str,
        index: int,
        status: str,
        error: Optional[str] = None,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
    ) -> None:
        if status not in ROW_RESULT_STATUSES:
            raise ValueError(f"Unknown row status '{status}'")
        self._append_lines(run_id, [{
            "kind": "result", "index": index, "status": status, "error": error,
            "started_at": started_at, "finished_at": finished_at, "at": _now(),
        }])

    def load_rows(self, run_id: str) -> List[Dict[str, Any]]:
        """Return every row of a run, merged by index, ordered by index.

        Lines that are not valid JSON (for example a final line cut short by
        a crash) are skipped.
        """
        path = self._path(run_id)
        if not path.exists():
            return []
        rows: Dict[int, Dict[str, Any]] = {}
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or not isinstance(record.get("index"), int):
                    continue
                index = record["index"]
                if record.get("kind") == "plan":
                    rows[index] = {
                        "index": index,
                        "answers": record.get("answers") or {},
                        "skipped": record.get("skipped") or [],
                        "persona_id": record.get("persona_id"),
                        "status": ROW_PLANNED,
                        "error": None,
                        "started_at": None,
                        "finished_at": None,
                        "attempts": 0,
                    }
                elif record.get("kind") == "result" and index in rows:
                    row = rows[index]
                    row["status"] = record.get("status")
                    row["error"] = record.get("error")
                    if record.get("status") == ROW_IN_FLIGHT:
                        row["attempts"] += 1
                    if record.get("started_at"):
                        row["started_at"] = record["started_at"]
                    row["finished_at"] = record.get("finished_at")
        return [rows[index] for index in sorted(rows)]

    # ------------------------------------------------------------- helpers

    def _path(self, run_id: str) -> Path:
        if not is_valid_run_id(run_id):
            raise ValueError("Invalid run id")
        return self.runs_dir / f"{run_id}.jsonl"

    def _append_lines(self, run_id: str, records: Iterable[Dict[str, Any]]) -> None:
        path = self._path(run_id)
        payload = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
        if not payload:
            return
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        with _lock_for(path), path.open("a+b") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            if size:
                # Start on a fresh line if a previous write was cut short.
                handle.seek(size - 1)
                if handle.read(1) != b"\n":
                    handle.write(b"\n")
            handle.write(payload.encode("utf-8"))

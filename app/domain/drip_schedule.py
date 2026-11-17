"""Spreading a run's responses over a time window.

All times are timezone-aware UTC datetimes.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

MIN_WINDOW_SECONDS = 60
MAX_WINDOW_SECONDS = 7 * 24 * 3600
MIN_GAP_SECONDS = 1.0


def build_schedule(count: int, start: datetime, window_seconds: float, rng: random.Random) -> List[datetime]:
    """One send time per response: the window is cut into ``count`` equal slots and
    each response gets a random moment inside its own slot, so sends are spread
    out without clustering."""
    if count <= 0:
        return []
    slot = window_seconds / count
    return [start + timedelta(seconds=(index + rng.random()) * slot) for index in range(count)]


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def due_rows(rows: Iterable[Dict[str, Any]], now: datetime, max_per_tick: int) -> List[Dict[str, Any]]:
    """Planned rows whose send time has come, earliest first, at most ``max_per_tick``."""
    due = [
        row for row in rows
        if row.get("status") == "planned" and (when := _parse(row.get("due_at"))) is not None and when <= now
    ]
    due.sort(key=lambda row: row["due_at"])
    return due[:max(1, max_per_tick)]


def next_due(rows: Iterable[Dict[str, Any]]) -> Optional[str]:
    times = [row["due_at"] for row in rows if row.get("status") == "planned" and row.get("due_at")]
    return min(times) if times else None


def respread(remaining_count: int, now: datetime, window_end: datetime, min_gap_seconds: float,
             rng: random.Random) -> List[datetime]:
    """New send times for the responses still waiting.

    They are spread over what is left of the window. If too little is left to
    keep ``min_gap_seconds`` between sends, they are spaced exactly that far
    apart instead, so a late resume never sends everything at once.
    """
    gap = max(min_gap_seconds, MIN_GAP_SECONDS)
    left = (window_end - now).total_seconds()
    if left >= remaining_count * gap:
        return build_schedule(remaining_count, now, left, rng)
    return [now + timedelta(seconds=(index + 1) * gap) for index in range(remaining_count)]

"""Summaries of planned and submitted answers against their targets.

Both the pre-run simulation and the post-run report use ``distribution``:
the simulation feeds it every planned row, the report only the rows that
were submitted successfully. Targets come from a ``target_snapshot`` so a
report compares a run with the configuration it was started from.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.domain.response_plan import ResponsePlan, target_snapshot
from app.models import Form

CHOICE_TYPES = {"multiple_choice", "dropdown", "linear_scale", "checkbox"}
SINGLE_CHOICE_TYPES = {"multiple_choice", "dropdown", "linear_scale"}
TEXT_SAMPLE_LIMIT = 5


def _rate(count: int, total: int) -> float:
    return round(count * 100 / total, 1) if total else 0.0


def _answer_for(row: Dict[str, Any], question_id: str, entry_param: Optional[str]) -> Any:
    value = row.get(question_id)
    if value is None and entry_param:
        value = row.get(entry_param)
    if value in ("", []):
        return None
    return value


def _option_targets(meta: Dict[str, Any]) -> Dict[str, float]:
    options = meta.get("options") or {}
    weights = {text: max(0.0, float(pct or 0)) for text, pct in options.items()}
    if meta.get("type") in SINGLE_CHOICE_TYPES:
        total = sum(weights.values())
        if total > 0:
            return {text: round(weight * 100 / total, 1) for text, weight in weights.items()}
    return {text: round(weight, 1) for text, weight in weights.items()}


def distribution(snapshot: Dict[str, Dict[str, Any]], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-question counts and rates for ``rows`` next to the snapshot targets.

    Choice questions list every configured option (plus any other value seen)
    with its count, rate and target. Checkbox rates are per response, so they
    can add up to more than 100. Text questions report how many distinct
    values appear and a few samples.
    """
    total = len(rows)
    questions = []
    for question_id, meta in snapshot.items():
        values = [_answer_for(row, question_id, meta.get("entry_param")) for row in rows]
        answered = [value for value in values if value is not None]
        blank = total - len(answered)
        summary: Dict[str, Any] = {
            "question_id": question_id,
            "text": meta.get("text"),
            "type": meta.get("type"),
            "answered": len(answered),
            "blank": blank,
            "blank_rate": _rate(blank, total),
            "target_fill": meta.get("fill_percentage"),
        }
        if meta.get("type") in CHOICE_TYPES and meta.get("options"):
            counts: Counter = Counter()
            for value in answered:
                for choice in (value if isinstance(value, list) else [value]):
                    counts[str(choice)] += 1
            targets = _option_targets(meta)
            options = [
                {"text": text, "count": counts.pop(text, 0), "target": target}
                for text, target in targets.items()
            ]
            options += [
                {"text": text, "count": count, "target": None}
                for text, count in sorted(counts.items())
            ]
            for option in options:
                option["rate"] = _rate(option["count"], total)
            summary["kind"] = "choice"
            summary["options"] = options
        else:
            texts = [", ".join(map(str, v)) if isinstance(v, list) else str(v) for v in answered]
            distinct = list(dict.fromkeys(texts))
            summary["kind"] = "text"
            summary["distinct"] = len(distinct)
            summary["samples"] = distinct[:TEXT_SAMPLE_LIMIT]
        questions.append(summary)
    return questions


def retry_candidates(
    family: List[List[Dict[str, Any]]],
    include_unknown: bool = False,
) -> List[Dict[str, Any]]:
    """Rows of a run that should be sent again.

    ``family`` is the original run's rows followed by the rows of each earlier
    retry, oldest first. Retry rows keep the original row index, and a row's
    current outcome is the one from the latest run that attempted it. Failed
    rows qualify; rows whose outcome is unknown only when asked, because they
    may already have reached Google. A row that any retry sent successfully
    is never sent again. Answers always come from the original run.
    """
    if not family:
        return []
    wanted = {"failed", "unknown"} if include_unknown else {"failed"}
    current: Dict[int, str] = {}
    for rows in family:
        for row in rows:
            if row.get("status") != "planned" or row["index"] not in current:
                current[row["index"]] = row.get("status")
    return [row for row in family[0] if current.get(row["index"]) in wanted]


def _persona_breakdown(persona_targets: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per persona: how many rows it got and how its answers compare with its own targets."""
    total = len(rows)
    breakdown = []
    for persona in persona_targets:
        mine = [row["answers"] for row in rows if row.get("persona_id") == persona["persona_id"]]
        breakdown.append({
            "persona_id": persona["persona_id"],
            "name": persona["name"],
            "weight": persona["weight"],
            "count": len(mine),
            "share": _rate(len(mine), total),
            "questions": distribution(persona["targets"], mine),
        })
    return breakdown


def summarize_plan(form: Form, plan: ResponsePlan) -> Dict[str, Any]:
    """What a plan would send, question by question, and per persona when the form has them."""
    summary = {
        "total": len(plan.rows),
        "questions": distribution(target_snapshot(form), plan.answers()),
        "skipped": plan.skipped_summary(),
    }
    if form.personas and any(row.persona_id for row in plan.rows):
        from app.domain.personas import persona_targets

        summary["personas"] = _persona_breakdown(
            persona_targets(form), [{"answers": row.answers, "persona_id": row.persona_id} for row in plan.rows]
        )
    return summary


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def summarize_run(form: Optional[Form], header: Dict[str, Any], rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Outcome of a run and its successful answers against the run's targets."""
    rows = list(rows)
    statuses = Counter(row.get("status") for row in rows)
    successful = [row["answers"] for row in rows if row.get("status") == "success"]

    started = [t for t in (_parse_time(row.get("started_at")) for row in rows) if t]
    finished = [t for t in (_parse_time(row.get("finished_at")) for row in rows) if t]
    duration = None
    if started and finished:
        duration = max(0, int((max(finished) - min(started)).total_seconds()))

    snapshot = header.get("target_snapshot") or (target_snapshot(form) if form else {})
    failures = Counter(row.get("error") or "unknown_error" for row in rows if row.get("status") == "failed")

    summary = {
        "total": len(rows),
        "success": statuses.get("success", 0),
        "failed": statuses.get("failed", 0),
        "unknown": statuses.get("unknown", 0),
        "in_flight": statuses.get("in_flight", 0),
        "pending": statuses.get("planned", 0),
        "success_rate": _rate(statuses.get("success", 0), len(rows)),
        "duration_seconds": duration,
        "questions": distribution(snapshot, successful),
        "failure_reasons": [{"reason": reason, "count": count} for reason, count in failures.most_common()],
    }
    if header.get("personas"):
        summary["personas"] = _persona_breakdown(
            header["personas"], [row for row in rows if row.get("status") == "success"]
        )
    return summary

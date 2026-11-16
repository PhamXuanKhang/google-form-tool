"""Seeded response plans.

A plan is the full list of answer rows a run will send, decided before any
browser opens. Simulation, run history, retries and scheduling all read the
same plan, so what was previewed is what gets submitted.

``answers`` holds the values the app sends. In prefill mode the browser step
may still pick a first option for a required choice question that the plan
left empty; that fallback is not part of the plan.
"""
from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.form_processor import FormProcessor
from app.models import Form

PLAN_MODE_PREFILL = "prefill_link"
PLAN_MODE_DOM_FILL = "dom_fill"
PLAN_MODES = (PLAN_MODE_PREFILL, PLAN_MODE_DOM_FILL)

# Prefill links cannot carry these question types.
SKIPPABLE_PREFILL_TYPES = {"file_upload", "rating", "unknown"}
# Question types the browser filler knows how to answer in direct mode.
DOM_FILLABLE_TYPES = {
    "input_text", "input_email", "textarea", "date", "time",
    "dropdown", "multiple_choice", "checkbox", "linear_scale",
}

SKIP_REASON_PREFILL = "unsupported_in_prefill"
SKIP_REASON_DOM_FILL = "unsupported_in_dom_fill"


@dataclass
class PlanRow:
    index: int
    answers: Dict[str, Any]
    skipped: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "answers": self.answers, "skipped": self.skipped}


@dataclass
class ResponsePlan:
    seed: int
    mode: str
    rows: List[PlanRow]

    def answers(self) -> List[Dict[str, Any]]:
        return [row.answers for row in self.rows]

    def skipped_summary(self) -> Dict[str, int]:
        """Count skipped answers per question type, as warnings report them."""
        summary: Dict[str, int] = {}
        for row in self.rows:
            for skipped in row.skipped:
                q_type = skipped["type"]
                summary[q_type] = summary.get(q_type, 0) + 1
        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {"seed": self.seed, "mode": self.mode, "rows": [row.to_dict() for row in self.rows]}


def new_seed() -> int:
    """Return a fresh seed that survives a JSON round trip in JavaScript."""
    return secrets.randbits(48)


def question_type_lookup(form: Form) -> Dict[str, str]:
    """Map every accepted answer key (question id and entry param) to its type."""
    lookup: Dict[str, str] = {}
    if not form.response_config or not form.response_config.pages:
        return lookup
    for page in form.response_config.pages:
        for question in page.questions or []:
            if question.question_id:
                lookup[question.question_id] = question.type
            entry_param = question.get_entry_param()
            if entry_param:
                lookup[entry_param] = question.type
    return lookup


def target_snapshot(form: Form) -> Dict[str, Dict[str, Any]]:
    """Capture each question's configured target so later reports compare a
    run against what was asked for at the time, not against later edits."""
    snapshot: Dict[str, Dict[str, Any]] = {}
    if not form.response_config or not form.response_config.pages:
        return snapshot
    for page in form.response_config.pages:
        for question in page.questions or []:
            config = question.answer_config
            snapshot[question.question_id] = {
                "text": question.text,
                "type": question.type,
                "fill_percentage": config.fill_percentage if config else None,
                "options": (
                    {option.text: option.percentage for option in config.options}
                    if config and config.options else None
                ),
            }
    return snapshot


def filter_unsendable(
    answers: Dict[str, Any], type_lookup: Dict[str, str], mode: str
) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Split one answer row into what the mode can send and what it skips.

    Keys that do not match a known question are kept unchanged.
    """
    kept: Dict[str, Any] = {}
    skipped: List[Dict[str, str]] = []
    for key, value in answers.items():
        q_type = type_lookup.get(key)
        if mode == PLAN_MODE_PREFILL and q_type in SKIPPABLE_PREFILL_TYPES:
            skipped.append({"question_id": key, "type": q_type, "reason": SKIP_REASON_PREFILL})
            continue
        if mode == PLAN_MODE_DOM_FILL and q_type is not None and q_type not in DOM_FILLABLE_TYPES:
            skipped.append({"question_id": key, "type": q_type, "reason": SKIP_REASON_DOM_FILL})
            continue
        kept[key] = value
    return kept, skipped


def build_plan(
    form: Form,
    count: int,
    seed: Optional[int] = None,
    mode: str = PLAN_MODE_PREFILL,
    responses_list: Optional[List[Dict[str, Any]]] = None,
    responses: Optional[Dict[str, Any]] = None,
) -> ResponsePlan:
    """Build the rows a run will send.

    - ``responses_list`` (uploaded data): one row per item, ``count`` ignored.
    - ``responses`` (one fixed answer set): repeated ``count`` times.
    - Otherwise answers come from the form's configuration. Prefill spreads
      each question's percentages across rows as exact quotas; direct mode
      draws every row independently.

    The same form, count, seed and mode always give the same plan.
    """
    if mode not in PLAN_MODES:
        raise ValueError(f"Unknown submission_mode '{mode}'. Expected one of: {list(PLAN_MODES)}")
    if seed is None:
        seed = new_seed()

    processor = FormProcessor(form, rng=random.Random(seed))
    if responses_list:
        raw_rows = [dict(row) for row in responses_list]
    elif responses is not None:
        raw_rows = [dict(responses) for _ in range(max(0, count))]
    elif mode == PLAN_MODE_PREFILL:
        raw_rows = processor.generate_prefill_responses(count, shuffle=True)
    else:
        raw_rows = [
            FormProcessor(form, rng=random.Random(f"{seed}:{index}")).generate_random_responses()
            for index in range(max(0, count))
        ]

    raw_rows = processor.apply_prefill_branch_stops(raw_rows)

    type_lookup = question_type_lookup(form)
    rows = []
    for index, answers in enumerate(raw_rows):
        kept, skipped = filter_unsendable(answers, type_lookup, mode)
        rows.append(PlanRow(index=index, answers=kept, skipped=skipped))
    return ResponsePlan(seed=seed, mode=mode, rows=rows)

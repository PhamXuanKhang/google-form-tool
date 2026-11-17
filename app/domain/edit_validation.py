"""Validation of answer-setting edits before they are stored.

``apply_user_edits`` assigns values without checks, and a stored value the
Form model rejects (for example a percentage of 150) makes the whole form
unloadable. Every path that stores answer settings validates them here first.
"""
from __future__ import annotations

import math
from typing import Any

from app.models import Form

MAX_ANSWERS = 10000
MAX_ANSWER_LENGTH = 10000
MAX_OPTIONS = 500


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_percentage(value: Any, where: str) -> None:
    if not _is_number(value) or value < 0 or value > 100:
        raise ValueError(f"{where} must be a number from 0 to 100.")


def validate_edit(question_id: str, edit: Any) -> None:
    """Check one question's edit; raises ValueError naming the bad field."""
    if not isinstance(edit, dict):
        raise ValueError(f"Edit for question '{question_id}' must be an object.")
    if "fill_percentage" in edit and edit["fill_percentage"] is not None:
        _check_percentage(edit["fill_percentage"], f"fill_percentage of question '{question_id}'")
    if "answers" in edit and edit["answers"] is not None:
        answers = edit["answers"]
        if not isinstance(answers, list) or len(answers) > MAX_ANSWERS:
            raise ValueError(f"answers of question '{question_id}' must be a list of at most {MAX_ANSWERS} texts.")
        for answer in answers:
            if not isinstance(answer, str) or len(answer) > MAX_ANSWER_LENGTH:
                raise ValueError(
                    f"Each answer of question '{question_id}' must be text of at most {MAX_ANSWER_LENGTH} characters."
                )
    if "options" in edit and edit["options"] is not None:
        options = edit["options"]
        if not isinstance(options, list) or len(options) > MAX_OPTIONS:
            raise ValueError(f"options of question '{question_id}' must be a list.")
        for option in options:
            if not isinstance(option, dict) or not isinstance(option.get("text"), str):
                raise ValueError(f"Each option of question '{question_id}' needs a text.")
            _check_percentage(option.get("percentage"), f"percentage of option '{option['text']}' in question '{question_id}'")
            next_page = option.get("next_page_id")
            if next_page is not None and not isinstance(next_page, str):
                raise ValueError(f"next_page_id of option '{option['text']}' must be text or null.")


def validate_edits(form: Form, edits: Any, require_known_questions: bool = False) -> None:
    """Check a whole edits payload (question_id -> edit) for ``form``.

    Edits for questions the form does not have are ignored by the processor;
    with ``require_known_questions`` they are rejected instead.
    """
    if not isinstance(edits, dict):
        raise ValueError("edits must be an object keyed by question_id.")
    known = {
        question.question_id
        for page in (form.response_config.pages if form.response_config else [])
        for question in page.questions or []
    }
    for question_id, edit in edits.items():
        if require_known_questions and question_id not in known:
            raise ValueError(f"Unknown question '{question_id}'.")
        validate_edit(question_id, edit)

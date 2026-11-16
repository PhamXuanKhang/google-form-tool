"""Checks for an AI Autopilot proposal before anyone can apply it.

The model's answer is untrusted input. This module turns it into the edits
shape ``/save_edit`` takes and the payload ``/forms/<id>/personas`` takes,
or rejects it:

- a percentage that is not a number, is negative, or is over 100 rejects the
  whole proposal;
- unknown questions and options are dropped with a warning;
- single-choice percentages within 1 point of 100 are scaled to exactly 100;
  further off, that question is dropped with a warning;
- suggested text answers are capped in number and length.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from app.domain.edit_validation import validate_edits
from app.domain.personas import MAX_PERSONAS, SINGLE_CHOICE_TYPES, validate_personas
from app.models import Form

TEXT_TYPES = {"input_text", "textarea", "input_email", "date", "time"}
CHOICE_TYPES = SINGLE_CHOICE_TYPES | {"checkbox"}
MAX_SUGGESTED_ANSWERS = 50
MAX_ANSWER_CHARS = 200
SUM_TOLERANCE = 1.0


class ProposalError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class _Option(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str
    percentage: Any = None


class _Question(BaseModel):
    model_config = ConfigDict(extra="ignore")
    question_id: str
    fill_percentage: Any = None
    options: Optional[List[_Option]] = None
    answers: Optional[List[Any]] = None


class _Persona(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    weight: Any
    description: Optional[str] = None
    overrides: List[_Question] = []


class _Proposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    questions: List[_Question] = []
    personas: Optional[List[_Persona]] = None


def _percentage(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or value < 0 or value > 100:
        raise ProposalError("invalid_percentage", f"The proposal has an invalid percentage for {where}.")
    return float(value)


def _to_hundred(values: List[float]) -> List[float]:
    total = sum(values)
    hundredths = [round(value / total * 10000) for value in values]
    largest = max(range(len(values)), key=lambda index: values[index])
    hundredths[largest] += 10000 - sum(hundredths)
    return [value / 100 for value in hundredths]


def _clean_question(question, item: _Question, label: str, warnings: List[str]) -> Optional[Dict[str, Any]]:
    edit: Dict[str, Any] = {}
    if item.fill_percentage is not None:
        edit["fill_percentage"] = _percentage(item.fill_percentage, f"{label} fill rate")

    if item.options is not None and question.type in CHOICE_TYPES:
        known = [option.text for option in (question.answer_config.options or [])] if question.answer_config else []
        proposed: Dict[str, float] = {}
        for option in item.options:
            value = _percentage(option.percentage, f"{label} option '{option.text}'")
            if option.text not in known:
                warnings.append(f"{label}: dropped unknown option '{option.text}'.")
                continue
            proposed[option.text] = value
        values = [proposed.get(text, 0.0) for text in known]
        if question.type in SINGLE_CHOICE_TYPES:
            total = sum(values)
            if total == 0 or abs(total - 100) > SUM_TOLERANCE:
                warnings.append(f"{label}: skipped because option percentages total {round(total, 2)}, not 100.")
                values = None
            elif total != 100:
                values = _to_hundred(values)
        if values is not None:
            edit["options"] = [{"text": text, "percentage": value} for text, value in zip(known, values)]

    if item.answers is not None and question.type in TEXT_TYPES:
        answers = [str(answer)[:MAX_ANSWER_CHARS] for answer in item.answers if str(answer).strip()]
        if len(answers) > MAX_SUGGESTED_ANSWERS:
            warnings.append(f"{label}: kept the first {MAX_SUGGESTED_ANSWERS} suggested answers.")
        if answers:
            edit["answers"] = answers[:MAX_SUGGESTED_ANSWERS]
    return edit or None


def validate_proposal(form: Form, raw: Any, want_personas: bool) -> Dict[str, Any]:
    """Return {"edits", "personas", "warnings"} or raise ProposalError."""
    try:
        proposal = _Proposal.model_validate(raw)
    except ValidationError:
        raise ProposalError("invalid_ai_response", "The AI answer did not match the expected format.")

    questions = {
        question.question_id: question
        for page in (form.response_config.pages if form.response_config else [])
        for question in page.questions or []
    }
    warnings: List[str] = []

    def clean_all(items: List[_Question], prefix: str) -> Dict[str, Any]:
        cleaned = {}
        for item in items:
            question = questions.get(item.question_id)
            if question is None:
                warnings.append(f"{prefix}dropped unknown question '{item.question_id}'.")
                continue
            edit = _clean_question(question, item, f"{prefix}{question.text!r}", warnings)
            if edit:
                cleaned[item.question_id] = edit
        return cleaned

    edits = clean_all(proposal.questions, "")
    personas = None
    if want_personas and proposal.personas:
        items = proposal.personas
        if len(items) > MAX_PERSONAS:
            warnings.append(f"Kept the first {MAX_PERSONAS} personas.")
            items = items[:MAX_PERSONAS]
        weights = [_percentage(item.weight, f"persona '{item.name}' weight") for item in items]
        total = sum(weights)
        if total == 0 or abs(total - 100) > SUM_TOLERANCE:
            warnings.append(f"Personas skipped because their weights total {round(total, 2)}, not 100.")
        else:
            weights = _to_hundred(weights) if total != 100 else weights
            payload = [
                {"name": item.name[:80], "weight": weight, "description": (item.description or "")[:1000] or None,
                 "overrides": clean_all(item.overrides, f"Persona '{item.name}': ")}
                for item, weight in zip(items, weights)
            ]
            try:
                personas = [p.model_dump(mode="json") for p in validate_personas(form, payload)]
            except ValueError as error:
                warnings.append(f"Personas skipped: {error}")

    validate_edits(form, edits, require_known_questions=True)
    return {"edits": edits, "personas": personas, "warnings": warnings}

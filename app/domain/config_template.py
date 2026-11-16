"""Answer configuration templates, separate from the form they came from.

A template holds, per question, the fill rate, text answers and option
percentages. It can be exported to a file, saved by name, and applied to the
same form or to another form with a compatible structure. Matching is by
question id first, then by question text and type; a question whose options
differ is reported and left unchanged. Templates never hold API keys or
paths: the schema forbids unknown fields.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models import Form

TEMPLATE_SCHEMA_VERSION = 1


class TemplateOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=2000)
    percentage: float = Field(ge=0, le=100)
    next_page_id: Optional[str] = Field(default=None, max_length=200)


class TemplateQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(max_length=200)
    text: str = Field(default="", max_length=5000)
    type: str = Field(max_length=50)
    fill_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    answers: Optional[List[str]] = Field(default=None, max_length=10000)
    options: Optional[List[TemplateOption]] = Field(default=None, max_length=500)


class ConfigTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    name: str = Field(min_length=1, max_length=200)
    created_at: str = Field(max_length=50)
    form_fingerprint: str = Field(max_length=100)
    questions: List[TemplateQuestion] = Field(max_length=1000)


def _questions(form: Form):
    for page in (form.response_config.pages if form.response_config else []):
        for question in page.questions or []:
            yield question


def form_fingerprint(form: Form) -> str:
    """Hash of the form's structure: question order, types and option counts."""
    shape = [
        [question.type, len(question.answer_config.options or []) if question.answer_config else 0]
        for question in _questions(form)
    ]
    return hashlib.sha256(json.dumps(shape).encode("utf-8")).hexdigest()[:16]


def build_template(form: Form, name: Optional[str] = None) -> Dict[str, Any]:
    questions = []
    for question in _questions(form):
        config = question.answer_config
        item: Dict[str, Any] = {"question_id": question.question_id, "text": question.text, "type": question.type}
        if config is not None:
            if config.fill_percentage is not None:
                item["fill_percentage"] = config.fill_percentage
            if config.answers is not None:
                item["answers"] = list(config.answers)
            if config.options is not None:
                item["options"] = [
                    {"text": option.text, "percentage": option.percentage, "next_page_id": option.next_page_id}
                    for option in config.options
                ]
        questions.append(item)
    template = {
        "schema_version": TEMPLATE_SCHEMA_VERSION,
        "name": (name or form.title or "Template")[:200],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "form_fingerprint": form_fingerprint(form),
        "questions": questions,
    }
    return ConfigTemplate.model_validate(template).model_dump(mode="json")


def parse_template(data: Any) -> ConfigTemplate:
    """Validate raw JSON; raises ValueError with a readable message."""
    if not isinstance(data, dict):
        raise ValueError("A template must be a JSON object.")
    if data.get("schema_version") != TEMPLATE_SCHEMA_VERSION:
        raise ValueError(f"Unsupported template schema_version; expected {TEMPLATE_SCHEMA_VERSION}.")
    try:
        return ConfigTemplate.model_validate(data)
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        raise ValueError(f"Invalid template at {where}: {first['msg']}")


def match_template(form: Form, template: ConfigTemplate) -> Dict[str, Any]:
    """Preview applying ``template`` to ``form`` and build the edits for matched questions."""
    by_id = {question.question_id: question for question in _questions(form)}
    by_text = {}
    for question in _questions(form):
        by_text.setdefault((question.text.strip().lower(), question.type), question)

    matched, unmatched, edits = [], [], {}
    used = set()
    for item in template.questions:
        target = by_id.get(item.question_id)
        how = "id"
        if target is None or target.type != item.type:
            target = by_text.get((item.text.strip().lower(), item.type))
            how = "text"
        if target is None or target.question_id in used:
            unmatched.append({"question_id": item.question_id, "text": item.text, "reason": "not_found"})
            continue
        if item.options is not None:
            form_options = [option.text for option in (target.answer_config.options or [])] if target.answer_config else []
            if sorted(form_options) != sorted(option.text for option in item.options):
                unmatched.append({"question_id": item.question_id, "text": item.text, "reason": "options_differ"})
                continue
        used.add(target.question_id)
        edit: Dict[str, Any] = {}
        if item.fill_percentage is not None:
            edit["fill_percentage"] = item.fill_percentage
        if item.answers is not None:
            edit["answers"] = list(item.answers)
        if item.options is not None:
            edit["options"] = [
                {"text": option.text, "percentage": option.percentage, "next_page_id": option.next_page_id}
                for option in item.options
            ]
        if edit:
            edits[target.question_id] = edit
        matched.append({"question_id": target.question_id, "text": target.text, "matched_by": how})

    missing = [
        {"question_id": question.question_id, "text": question.text}
        for question in _questions(form) if question.question_id not in used
    ]
    return {
        "same_structure": template.form_fingerprint == form_fingerprint(form),
        "matched": matched,
        "unmatched": unmatched,
        "missing": missing,
        "edits": edits,
    }

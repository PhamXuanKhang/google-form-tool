"""Personas: weighted groups of respondents with their own answer settings."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from pydantic import ValidationError

from app.models import Form, Persona

MAX_PERSONAS = 8
WEIGHT_TOLERANCE = 0.01
SINGLE_CHOICE_TYPES = {"multiple_choice", "dropdown", "linear_scale", "rating"}
SUM_TOLERANCE = 1.0


def _questions(form: Form):
    for page in (form.response_config.pages if form.response_config else []):
        for question in page.questions or []:
            yield question


def merged_form(form: Form, persona: Persona) -> Form:
    """A copy of ``form`` whose questions use the persona's overrides."""
    merged = form.model_copy(deep=True)
    for question in _questions(merged):
        override = persona.overrides.get(question.question_id)
        if override is None:
            continue
        base_branches = {
            option.text: option.next_page_id
            for option in ((question.answer_config.options or []) if question.answer_config else [])
        }
        question.answer_config = override.model_copy(deep=True)
        # Branching belongs to the form, not to a persona: keep the shared setting.
        for option in question.answer_config.options or []:
            option.next_page_id = base_branches.get(option.text)
    merged.personas = None
    return merged


def validate_personas(form: Form, raw: Any) -> List[Persona]:
    """Check a full persona list for ``form``; raises ValueError with a readable message.

    An empty list clears personas. Otherwise: at most 8 personas, unique ids,
    weights totalling 100, overrides only for questions of this form, option
    texts that exist on the question, and single-choice percentages that
    total 100 when any is set.
    """
    if not isinstance(raw, list):
        raise ValueError("personas must be a list.")
    if len(raw) > MAX_PERSONAS:
        raise ValueError(f"A form can have at most {MAX_PERSONAS} personas.")
    personas = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each persona must be an object.")
        item = dict(item)
        item.setdefault("persona_id", uuid.uuid4().hex[:12])
        try:
            personas.append(Persona.model_validate(item))
        except ValidationError as error:
            first = error.errors()[0]
            raise ValueError(f"Invalid persona at {'.'.join(str(p) for p in first['loc'])}: {first['msg']}")
    if not personas:
        return []

    ids = [persona.persona_id for persona in personas]
    if len(set(ids)) != len(ids):
        raise ValueError("Persona ids must be unique.")
    total = sum(persona.weight for persona in personas)
    if abs(total - 100) > WEIGHT_TOLERANCE:
        raise ValueError(f"Persona weights must total 100 (got {round(total, 2)}).")

    questions = {question.question_id: question for question in _questions(form)}
    for persona in personas:
        for question_id, config in persona.overrides.items():
            question = questions.get(question_id)
            if question is None:
                raise ValueError(f"Persona '{persona.name}' overrides unknown question '{question_id}'.")
            if config.options is not None:
                known = {option.text for option in (question.answer_config.options or [])} if question.answer_config else set()
                unknown = [option.text for option in config.options if option.text not in known]
                if unknown:
                    raise ValueError(f"Persona '{persona.name}': question '{question_id}' has no option '{unknown[0]}'.")
                option_total = sum(option.percentage for option in config.options)
                if question.type in SINGLE_CHOICE_TYPES and option_total > 0 and abs(option_total - 100) > SUM_TOLERANCE:
                    raise ValueError(
                        f"Persona '{persona.name}': option percentages of question '{question_id}' must total 100."
                    )
    return personas


def persona_targets(form: Form) -> List[Dict[str, Any]]:
    """Per-persona targets, stored with a run so reports compare each persona."""
    from app.domain.response_plan import target_snapshot

    return [
        {"persona_id": persona.persona_id, "name": persona.name, "weight": persona.weight,
         "targets": target_snapshot(merged_form(form, persona))}
        for persona in (form.personas or [])
    ]

"""Tests for Question.entry_id (TIP-002).

Covers:
- Backward compatibility: questions stored before TIP-002 (no entry_id field)
  still validate when loaded from TinyDB.
- get_entry_param() helper used by prefill-link mode.
"""
from datetime import datetime

from app.models import (
    AnswerConfig,
    AnswerOption,
    Form,
    Page,
    Question,
    ResponseConfig,
)


def test_question_loads_without_entry_id():
    """Old persisted questions without entry_id must still validate."""
    raw = {
        "question_id": "123456789",
        "type": "input_text",
        "text": "Your name?",
        "answer_config": {"fill_percentage": 100, "answers": [], "options": None},
    }
    q = Question.model_validate(raw)
    assert q.entry_id is None
    assert q.question_id == "123456789"


def test_question_with_entry_id_round_trip():
    q = Question(
        question_id="123",
        entry_id="entry.123",
        type="multiple_choice",
        text="Pick one",
        answer_config=AnswerConfig(
            options=[AnswerOption(text="A", percentage=50.0)],
            fill_percentage=None,
            answers=None,
        ),
    )
    dumped = q.model_dump()
    assert dumped["entry_id"] == "entry.123"
    assert Question.model_validate(dumped).entry_id == "entry.123"


def test_get_entry_param_prefers_entry_id():
    q = Question(
        question_id="123",
        entry_id="entry.999",
        type="input_text",
        text="t",
        answer_config=AnswerConfig(fill_percentage=100, answers=[], options=None),
    )
    assert q.get_entry_param() == "entry.999"


def test_get_entry_param_falls_back_to_numeric_question_id():
    q = Question(
        question_id="123456789",
        type="input_text",
        text="t",
        answer_config=AnswerConfig(fill_percentage=100, answers=[], options=None),
    )
    assert q.get_entry_param() == "entry.123456789"


def test_get_entry_param_returns_none_for_non_numeric_id():
    q = Question(
        question_id="q_email",
        type="input_email",
        text="email",
        answer_config=AnswerConfig(fill_percentage=0, answers=[], options=None),
    )
    assert q.get_entry_param() is None


def test_form_loads_without_entry_id_field():
    """Whole form serialized before TIP-002 still validates."""
    raw = {
        "id": "form_legacy",
        "title": "Legacy",
        "description": "",
        "url": "https://example.com/form",
        "created_at": datetime.now().isoformat(),
        "last_used": None,
        "response_config": {
            "pages": [
                {
                    "page_id": "page_1",
                    "questions": [
                        {
                            "question_id": "q1",
                            "type": "input_text",
                            "text": "Name?",
                            "answer_config": {
                                "fill_percentage": 100,
                                "answers": [],
                                "options": None,
                            },
                        }
                    ],
                }
            ]
        },
        "submissions": None,
    }
    form = Form.model_validate(raw)
    assert form.response_config.pages[0].questions[0].entry_id is None

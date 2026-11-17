import time
from datetime import datetime

import pytest

import app.adapters.ai.ai_responder as ai_responder
from app.domain.edit_validation import validate_edits
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig


def _form():
    return Form(
        id="f_edit", title="Edit", description="", url="https://docs.google.com/forms/d/e/EDIT/viewform",
        created_at=datetime(2026, 1, 1), last_used=None, submissions=None,
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
            Question(question_id="q1", type="multiple_choice", text="Pick",
                     answer_config=AnswerConfig(fill_percentage=100, options=[
                         AnswerOption(text="A", percentage=100.0), AnswerOption(text="B", percentage=0.0)])),
        ])]),
    )


class MemoryStorage:
    def __init__(self, form):
        self.data = form.model_dump(mode="json")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def get_form_by_id(self, form_id):
        return Form.model_validate(self.data)

    def save_form(self, form):
        self.data = form.model_dump(mode="json")
        return True


@pytest.mark.parametrize("edit", [
    {"options": [{"text": "A", "percentage": 150}]},
    {"options": [{"text": "A"}]},
    {"options": [{"text": "A", "percentage": "50"}]},
    {"options": [{"text": "A", "percentage": float("nan")}]},
    {"options": [{"percentage": 10}]},
    {"options": "A=100"},
    {"fill_percentage": 101},
    {"fill_percentage": -1},
    {"answers": "one answer"},
    {"answers": [1, 2]},
    "not an object",
])
def test_invalid_edits_are_rejected_and_the_form_still_loads(client, storage_stub, edit):
    storage = storage_stub(MemoryStorage(_form()))
    before = dict(storage.data)

    response = client.post("/save_edit", json={"form_id": "f_edit", "edits": {"q1": edit}})

    assert response.status_code == 400
    assert storage.data == before
    assert Form.model_validate(storage.data)


def test_valid_edits_are_saved(client, storage_stub):
    storage = storage_stub(MemoryStorage(_form()))

    response = client.post("/save_edit", json={"form_id": "f_edit", "edits": {
        "q1": {"fill_percentage": 80, "options": [{"text": "A", "percentage": 40}, {"text": "B", "percentage": 60}]},
        "unknown": {"answers": ["ignored"]},
    }})

    assert response.status_code == 200
    options = storage.data["response_config"]["pages"][0]["questions"][0]["answer_config"]["options"]
    assert [o["percentage"] for o in options] == [40, 60]


@pytest.mark.domain
def test_strict_mode_rejects_unknown_questions():
    with pytest.raises(ValueError, match="Unknown question"):
        validate_edits(_form(), {"nope": {}}, require_known_questions=True)


def test_ai_timeout_returns_without_waiting_for_the_hung_request(monkeypatch):
    class SlowModels:
        def generate_content(self, **kwargs):
            time.sleep(3)

    responder = ai_responder.AIResponder.__new__(ai_responder.AIResponder)
    responder.client = type("Client", (), {"models": SlowModels()})()
    responder.model_name = "fake"
    responder.timeout_seconds = 0.2

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        responder._generate_content("hello")

    assert time.monotonic() - started < 1.5

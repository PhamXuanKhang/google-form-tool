"""AI Autopilot: POST /ai/propose_config with a fake Gemini client."""
import json
import logging
import time
from datetime import datetime

import pytest

import app.adapters.ai.ai_responder as ai_responder
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig

SECRET_KEY = "fake-gemini-key-for-tests-0123456789"


def _form():
    return Form(
        id="f_ai", title="Coffee survey", description="", url="https://docs.google.com/forms/d/e/AI/viewform",
        created_at=datetime(2026, 1, 1), last_used=None, submissions=None,
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
            Question(question_id="q_drink", type="multiple_choice", text="Favourite drink",
                     answer_config=AnswerConfig(fill_percentage=100, options=[
                         AnswerOption(text="Coffee", percentage=50.0), AnswerOption(text="Tea", percentage=50.0)])),
            Question(question_id="q_extras", type="checkbox", text="Extras",
                     answer_config=AnswerConfig(fill_percentage=100, options=[
                         AnswerOption(text="Milk", percentage=0.0), AnswerOption(text="Sugar", percentage=0.0)])),
            Question(question_id="q_name", type="input_text", text="Name",
                     answer_config=AnswerConfig(fill_percentage=100, answers=[])),
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
        return Form.model_validate(self.data) if form_id == self.data["id"] else None


def _install_fake_gemini(monkeypatch, reply=None, delay=0.0, prompts=None):
    class Models:
        def list(self):
            return []

        def generate_content(self, **kwargs):
            if prompts is not None:
                prompts.append(kwargs)
            if delay:
                time.sleep(delay)
            return type("Response", (), {"text": reply if isinstance(reply, str) else json.dumps(reply)})()

    class Client:
        def __init__(self, api_key):
            self.models = Models()

    monkeypatch.setattr(ai_responder, "genai", type("GenAI", (), {"Client": Client}))
    monkeypatch.setattr(ai_responder, "GENAI_AVAILABLE", True)


@pytest.fixture
def storage(storage_stub):
    return storage_stub(MemoryStorage(_form()))


def _propose(client, **overrides):
    body = {"form_id": "f_ai", "api_key": SECRET_KEY, "audience": "Office workers in Hanoi", "want_personas": False}
    body.update(overrides)
    return client.post("/ai/propose_config", json=body)


GOOD = {
    "questions": [
        {"question_id": "q_drink", "options": [{"text": "Coffee", "percentage": 70.4}, {"text": "Tea", "percentage": 30}]},
        {"question_id": "q_extras", "options": [{"text": "Milk", "percentage": 40}, {"text": "Sugar", "percentage": 25}]},
        {"question_id": "q_name", "answers": ["Lan", "Minh"]},
        {"question_id": "q_ghost", "answers": ["x"]},
    ],
}


def test_valid_proposal_is_checked_and_nothing_is_saved(client, storage, monkeypatch, caplog):
    prompts = []
    _install_fake_gemini(monkeypatch, GOOD, prompts=prompts)
    before = json.loads(json.dumps(storage.data))

    response = _propose(client)
    data = response.get_json()

    assert response.status_code == 200
    drink = data["edits"]["q_drink"]["options"]
    assert [o["percentage"] for o in drink] == [70.12, 29.88]
    assert sum(o["percentage"] for o in drink) == pytest.approx(100)
    assert data["edits"]["q_extras"]["options"] == [{"text": "Milk", "percentage": 40.0}, {"text": "Sugar", "percentage": 25.0}]
    assert data["edits"]["q_name"] == {"answers": ["Lan", "Minh"]}
    assert any("q_ghost" in warning for warning in data["warnings"])
    assert data["personas"] is None
    assert storage.data == before
    assert prompts[0]["config"] == {"response_mime_type": "application/json"}
    assert "<<<DATA" in prompts[0]["contents"] and "Office workers in Hanoi" in prompts[0]["contents"]
    assert SECRET_KEY not in response.get_data(as_text=True)
    assert SECRET_KEY not in caplog.text


@pytest.mark.parametrize("reply,code", [
    ("this is not json", "invalid_ai_response"),
    ({"questions": "nope"}, "invalid_ai_response"),
    ({"questions": [{"question_id": "q_drink", "options": [{"text": "Coffee", "percentage": -5}]}]}, "invalid_percentage"),
    ({"questions": [{"question_id": "q_drink", "options": [{"text": "Coffee", "percentage": "lots"}]}]}, "invalid_percentage"),
])
def test_bad_ai_answers_are_rejected_with_a_code(client, storage, monkeypatch, caplog, reply, code):
    _install_fake_gemini(monkeypatch, reply)
    before = json.loads(json.dumps(storage.data))

    response = _propose(client)

    assert response.status_code == 422
    assert response.get_json()["code"] == code
    assert storage.data == before
    assert SECRET_KEY not in caplog.text


def test_options_far_from_100_are_skipped_with_a_warning(client, storage, monkeypatch):
    _install_fake_gemini(monkeypatch, {"questions": [
        {"question_id": "q_drink", "options": [{"text": "Coffee", "percentage": 60}, {"text": "Tea", "percentage": 10}]},
        {"question_id": "q_drink2", "options": []},
        {"question_id": "q_name", "answers": ["A"], "options": [{"text": "Juice", "percentage": 10}]},
    ]})

    data = _propose(client).get_json()

    assert "q_drink" not in data["edits"]
    assert any("total 70" in warning for warning in data["warnings"])


def test_timeout_returns_504(client, storage, monkeypatch):
    _install_fake_gemini(monkeypatch, GOOD, delay=2)
    monkeypatch.setattr(ai_responder.Config, "AI_REQUEST_TIMEOUT_SECONDS", 0.2)

    started = time.monotonic()
    response = _propose(client)

    assert response.status_code == 504
    assert response.get_json()["code"] == "ai_timeout"
    assert time.monotonic() - started < 1.5


def test_personas_are_proposed_when_asked(client, storage, monkeypatch):
    _install_fake_gemini(monkeypatch, dict(GOOD, personas=[
        {"name": "Coffee lovers", "weight": 70, "overrides": [
            {"question_id": "q_drink", "options": [{"text": "Coffee", "percentage": 95}, {"text": "Tea", "percentage": 5}]}]},
        {"name": "Tea people", "weight": 30.5, "overrides": []},
    ]))

    with_personas = _propose(client, want_personas=True).get_json()
    without = _propose(client).get_json()

    assert [p["name"] for p in with_personas["personas"]] == ["Coffee lovers", "Tea people"]
    assert sum(p["weight"] for p in with_personas["personas"]) == pytest.approx(100)
    assert with_personas["personas"][0]["overrides"]["q_drink"]["options"][0]["percentage"] == 95
    assert without["personas"] is None


@pytest.mark.parametrize("body,status", [
    ({"api_key": ""}, 400),
    ({"audience": ""}, 400),
    ({"audience": "x" * 2001}, 400),
    ({"form_id": "missing"}, 404),
])
def test_request_validation(client, storage, monkeypatch, body, status):
    _install_fake_gemini(monkeypatch, GOOD)

    assert _propose(client, **body).status_code == status


def test_too_large_prompt_is_refused_not_truncated(client, storage, monkeypatch):
    _install_fake_gemini(monkeypatch, GOOD)
    monkeypatch.setattr(ai_responder.Config, "AI_MAX_PROMPT_CHARS", 100)

    response = _propose(client)

    assert response.status_code == 400
    assert response.get_json()["code"] == "prompt_too_large"


def test_persona_and_autopilot_script_never_writes_html():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "static" / "js" / "form_filling"
              / "personas_autopilot.js").read_text(encoding="utf-8")

    assert "innerHTML" not in source
    assert "textContent" in source


def test_api_key_never_reaches_the_logs_on_unexpected_errors(client, storage, monkeypatch, caplog):
    class Exploding:
        def __init__(self, api_key):
            raise RuntimeError(f"boom {api_key}")

    monkeypatch.setattr(ai_responder, "genai", type("GenAI", (), {"Client": Exploding}))
    monkeypatch.setattr(ai_responder, "GENAI_AVAILABLE", True)
    caplog.set_level(logging.DEBUG)

    response = _propose(client)

    assert response.status_code == 500
    assert SECRET_KEY not in caplog.text
    assert SECRET_KEY not in response.get_data(as_text=True)

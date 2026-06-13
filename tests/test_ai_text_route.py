"""Tests for the inline AI text generation route (TIP-006).

POST /generate_ai_text_answers — narrow endpoint that returns N text variations
for one input_text/textarea question. The AIResponder is mocked to avoid real
Gemini calls.
"""
from datetime import datetime

import pytest

import app.main_routes as main_routes
from app.models import (
    AnswerConfig,
    Form,
    Page,
    Question,
    ResponseConfig,
)


def _build_form() -> Form:
    return Form(
        id="form_ai",
        title="AI Form",
        description="",
        url="https://docs.google.com/forms/d/e/FAKEID/viewform",
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(
            pages=[
                Page(
                    page_id="p1",
                    questions=[
                        Question(
                            question_id="q_text",
                            entry_id="entry.111",
                            type="input_text",
                            text="What is your name?",
                            answer_config=AnswerConfig(
                                fill_percentage=100, answers=[], options=None
                            ),
                        ),
                        Question(
                            question_id="q_para",
                            entry_id="entry.222",
                            type="textarea",
                            text="Tell us about yourself",
                            answer_config=AnswerConfig(
                                fill_percentage=100, answers=[], options=None
                            ),
                        ),
                        Question(
                            question_id="q_mc",
                            entry_id="entry.333",
                            type="multiple_choice",
                            text="Color?",
                            answer_config=AnswerConfig(
                                fill_percentage=100, answers=None, options=[]
                            ),
                        ),
                    ],
                )
            ]
        ),
        submissions=None,
    )


class FakeStorage:
    def __init__(self, form):
        self.form = form

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def get_form_by_id(self, form_id):
        return self.form if form_id == self.form.id else None


@pytest.fixture
def form():
    return _build_form()


@pytest.fixture
def patch_storage(monkeypatch, form):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage(form))
    return form


class FakeAIResponder:
    """Captures the question + count it was asked for and returns canned text."""

    instances = []

    def __init__(self, api_key):
        self.api_key = api_key
        self.calls = []
        FakeAIResponder.instances.append(self)

    def generate_text_variations(self, question, count, context=None):
        self.calls.append({
            "question_id": question.question_id,
            "type": question.type,
            "count": count,
            "context": context,
        })
        return [f"AI answer {i + 1} for {question.question_id}" for i in range(count)]


@pytest.fixture
def patch_ai(monkeypatch):
    FakeAIResponder.instances = []
    import app.core.ai_responder as ai_module

    monkeypatch.setattr(ai_module, "AIResponder", FakeAIResponder)
    monkeypatch.setattr(ai_module, "is_ai_available", lambda: True)
    return FakeAIResponder


# ---------------------------------------------------------------- happy path


def test_generates_n_answers_for_text_question(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "q_text",
            "api_key": "k_test",
            "count": 3,
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["answers"] == [
        "AI answer 1 for q_text",
        "AI answer 2 for q_text",
        "AI answer 3 for q_text",
    ]
    assert len(patch_ai.instances) == 1
    assert patch_ai.instances[0].api_key == "k_test"
    assert patch_ai.instances[0].calls == [
        {"question_id": "q_text", "type": "input_text", "count": 3, "context": "AI Form"}
    ]


def test_textarea_question_is_supported(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "q_para",
            "api_key": "k",
            "count": 2,
        },
    )
    assert response.status_code == 200
    assert len(response.get_json()["answers"]) == 2


# ------------------------------------------------------------------ rejections


def test_rejects_non_text_question_type(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "q_mc",
            "api_key": "k",
            "count": 1,
        },
    )
    assert response.status_code == 400
    assert "input_text or textarea" in response.get_json()["error"]
    # AI responder must not be touched at all.
    assert patch_ai.instances == []


def test_404_for_unknown_question(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "missing",
            "api_key": "k",
            "count": 1,
        },
    )
    assert response.status_code == 404


def test_404_for_unknown_form(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "no_such_form",
            "question_id": "q_text",
            "api_key": "k",
            "count": 1,
        },
    )
    assert response.status_code == 404


def test_400_when_required_field_missing(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={"form_id": "form_ai", "question_id": "q_text"},  # api_key missing
    )
    assert response.status_code == 400


def test_400_when_count_out_of_range(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "q_text",
            "api_key": "k",
            "count": 0,
        },
    )
    assert response.status_code == 400

    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "q_text",
            "api_key": "k",
            "count": 501,
        },
    )
    assert response.status_code == 400


def test_400_when_count_not_integer(client, patch_storage, patch_ai):
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "q_text",
            "api_key": "k",
            "count": "abc",
        },
    )
    assert response.status_code == 400


def test_500_handler_does_not_echo_api_key(client, patch_storage, monkeypatch, caplog):
    """Belt-and-suspenders: verify the error path never returns or logs the api_key."""
    import app.core.ai_responder as ai_module

    class BoomResponder:
        def __init__(self, api_key):
            self.api_key = api_key

        def generate_text_variations(self, *args, **kwargs):
            raise RuntimeError("simulated outage")

    monkeypatch.setattr(ai_module, "AIResponder", BoomResponder)
    monkeypatch.setattr(ai_module, "is_ai_available", lambda: True)

    secret = "super-secret-api-key-do-not-leak"
    response = client.post(
        "/generate_ai_text_answers",
        json={
            "form_id": "form_ai",
            "question_id": "q_text",
            "api_key": secret,
            "count": 1,
        },
    )

    assert response.status_code == 500
    assert secret not in response.get_data(as_text=True)
    assert secret not in caplog.text

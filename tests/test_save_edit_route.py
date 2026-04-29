from datetime import datetime

import app.main_routes as main_routes
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig


class FakeStorage:
    def __init__(self, form=None, save_result=True):
        self.form = form
        self.save_result = save_result
        self.saved_form = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def _load_form(self, form_id):
        if self.form and self.form.id == form_id:
            return self.form
        return None

    def save_form(self, form):
        self.saved_form = form
        return self.save_result


def make_manual_config_form():
    return Form(
        id="form_manual_001",
        title="Manual Config Form",
        description="Test form",
        url="https://example.com/manual-config",
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(
            pages=[
                Page(
                    page_id="page_1",
                    questions=[
                        Question(
                            question_id="q_text",
                            type="input_text",
                            text="Your name",
                            answer_config=AnswerConfig(fill_percentage=100, answers=[], options=None),
                        ),
                        Question(
                            question_id="q_choice",
                            type="multiple_choice",
                            text="Favorite color",
                            answer_config=AnswerConfig(
                                fill_percentage=100,
                                answers=None,
                                options=[
                                    AnswerOption(text="Red", percentage=50),
                                    AnswerOption(text="Blue", percentage=50),
                                ],
                            ),
                        ),
                    ],
                )
            ]
        ),
        submissions=[],
    )


def test_save_edit_applies_text_answers_and_fill_percentage(client, monkeypatch):
    form = make_manual_config_form()
    storage = FakeStorage(form)
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    response = client.post(
        "/save_edit",
        json={
            "form_id": form.id,
            "edits": {
                "q_text": {
                    "fill_percentage": 80,
                    "answers": ["Alice", "Bob"],
                }
            },
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    saved_question = storage.saved_form.response_config.pages[0].questions[0]
    assert saved_question.answer_config.fill_percentage == 80
    assert saved_question.answer_config.answers == ["Alice", "Bob"]


def test_save_edit_applies_option_percentages(client, monkeypatch):
    form = make_manual_config_form()
    storage = FakeStorage(form)
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    response = client.post(
        "/save_edit",
        json={
            "form_id": form.id,
            "edits": {
                "q_choice": {
                    "options": [
                        {"text": "Red", "percentage": 70},
                        {"text": "Blue", "percentage": 30},
                    ]
                }
            },
        },
    )

    assert response.status_code == 200
    saved_question = storage.saved_form.response_config.pages[0].questions[1]
    percentages = {option.text: option.percentage for option in saved_question.answer_config.options}
    assert percentages == {"Red": 70, "Blue": 30}


def test_save_edit_returns_404_for_missing_form(client, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage())

    response = client.post(
        "/save_edit",
        json={"form_id": "missing", "edits": {"q_text": {"fill_percentage": 50}}},
    )

    assert response.status_code == 404
    assert "Form not found" in response.get_json()["error"]

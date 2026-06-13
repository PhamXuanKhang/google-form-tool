from datetime import datetime

import app.main_routes as main_routes
from app.models import AnswerConfig, Form, Page, Question, ResponseConfig, CopyResult


class FakeStorage:
    def __init__(self, form=None):
        self.form = form
        self.saved_form = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get_form_by_url(self, url):
        if self.form and str(self.form.url) == url:
            return self.form
        return None

    def get_form_by_id(self, form_id):
        if self.form and self.form.id == form_id:
            return self.form
        return None

    def save_form(self, form):
        self.saved_form = form
        self.form = form
        return True


def make_copy_form():
    return Form(
        id="form_copy_001",
        title="Copy Source",
        description="Source description",
        url="https://docs.google.com/forms/d/example/viewform",
        created_at=datetime.now(),
        last_used=datetime.now(),
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[Question(question_id="q1", type="short_answer", text="Name", answer_config=AnswerConfig())])]),
        submissions=[],
    )


def test_form_copy_page_renders(client):
    response = client.get("/form_copy")

    assert response.status_code == 200
    assert b"Copy Form" in response.data


def test_extract_source_rejects_invalid_url(client):
    response = client.post("/form_copy/extract_source", json={"form_url": "https://example.com/form"})

    assert response.status_code == 400
    assert "valid Google Form URL" in response.get_json()["error"]


def test_extract_source_uses_cached_form(client, monkeypatch):
    form = make_copy_form()
    storage = FakeStorage(form)
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    response = client.post("/form_copy/extract_source", json={"form_url": str(form.url)})

    assert response.status_code == 200
    data = response.get_json()
    assert data["form"]["id"] == form.id
    assert data["form"]["title"] == "Copy Source"


def test_preview_plan_returns_plan(client, monkeypatch):
    form = make_copy_form()
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage(form))

    response = client.post("/form_copy/preview_plan", json={"form_id": form.id})

    assert response.status_code == 200
    data = response.get_json()
    assert data["plan"]["source_form_id"] == form.id
    assert data["plan"]["operations"][0]["kind"] == "set_title_description"


def test_preview_plan_rejects_missing_form(client, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage())

    response = client.post("/form_copy/preview_plan", json={"form_id": "missing"})

    assert response.status_code == 404


def test_apply_to_target_requires_ownership_confirmation(client, monkeypatch):
    form = make_copy_form()
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage(form))

    response = client.post(
        "/form_copy/apply_to_target",
        json={"form_id": form.id, "target_url": "https://docs.google.com/forms/d/example/edit", "ownership_confirmed": False},
    )

    assert response.status_code == 400
    assert "confirm" in response.get_json()["error"]


def test_apply_to_target_rejects_invalid_edit_url(client, monkeypatch):
    form = make_copy_form()
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage(form))

    response = client.post(
        "/form_copy/apply_to_target",
        json={"form_id": form.id, "target_url": "https://docs.google.com/forms/d/example/viewform", "ownership_confirmed": True},
    )

    assert response.status_code == 400


def test_apply_to_target_returns_copier_result(client, monkeypatch):
    form = make_copy_form()
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage(form))

    class FakeCopier:
        def __init__(self, **kwargs):
            pass

        def apply_plan(self, plan, target_url):
            return CopyResult(status="success", operations_total=len(plan.operations), operations_succeeded=len(plan.operations))

    monkeypatch.setattr(main_routes, "FormCopier", FakeCopier)

    response = client.post(
        "/form_copy/apply_to_target",
        json={"form_id": form.id, "target_url": "https://docs.google.com/forms/d/example/edit", "ownership_confirmed": True},
    )

    assert response.status_code == 200
    assert response.get_json()["result"]["status"] == "success"

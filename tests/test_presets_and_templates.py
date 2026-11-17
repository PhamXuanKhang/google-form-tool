import io
import json
from datetime import datetime

import pytest

from app.domain.distribution_presets import (
    BELL, FIRST_HEAVY, NEGATIVE_SKEW, ORDERED_PRESETS, POSITIVE_SKEW, UNIFORM, apply_preset,
)
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig


# ---------------------------------------------------------------- presets


@pytest.mark.domain
@pytest.mark.parametrize("count", range(2, 12))
@pytest.mark.parametrize("preset", ORDERED_PRESETS)
def test_every_preset_sums_to_100_without_negatives(count, preset):
    values = apply_preset(count, preset, ordered=True)

    assert len(values) == count
    assert round(sum(values), 2) == 100.0
    assert all(value >= 0 for value in values)
    assert all(round(value, 2) == value for value in values)


@pytest.mark.domain
@pytest.mark.parametrize("count", range(2, 12))
def test_preset_shapes(count):
    uniform = apply_preset(count, UNIFORM, ordered=True)
    positive = apply_preset(count, POSITIVE_SKEW, ordered=True)
    negative = apply_preset(count, NEGATIVE_SKEW, ordered=True)
    bell = apply_preset(count, BELL, ordered=True)
    first = apply_preset(count, FIRST_HEAVY, ordered=False)

    assert max(uniform) - min(uniform) <= 0.011
    assert positive == sorted(positive)
    assert negative == sorted(negative, reverse=True)
    assert all(abs(bell[i] - bell[-1 - i]) <= 0.011 for i in range(count))
    assert bell[count // 2] == max(bell)
    assert first[0] == max(first) and first[0] >= 50


@pytest.mark.domain
def test_directional_presets_need_an_ordered_question():
    for preset in (POSITIVE_SKEW, NEGATIVE_SKEW, BELL):
        with pytest.raises(ValueError):
            apply_preset(4, preset, ordered=False)
    with pytest.raises(ValueError):
        apply_preset(0, UNIFORM, ordered=True)
    with pytest.raises(ValueError):
        apply_preset(3, "zigzag", ordered=True)
    assert apply_preset(1, FIRST_HEAVY, ordered=False) == [100.0]


def test_presets_route(client):
    scale = client.get("/presets?type=linear_scale&options=5").get_json()["presets"]
    choice = client.get("/presets?type=multiple_choice&options=3").get_json()["presets"]

    assert set(scale) == set(ORDERED_PRESETS)
    assert set(choice) == {UNIFORM, FIRST_HEAVY}
    assert client.get("/presets?type=checkbox&options=3").status_code == 400
    assert client.get("/presets?type=dropdown&options=0").status_code == 400


# -------------------------------------------------------------- templates


def _form(form_id="f_tpl", color_options=("Red", "Blue")):
    return Form(
        id=form_id, title="Template form", description="",
        url=f"https://docs.google.com/forms/d/e/{form_id}/viewform",
        created_at=datetime(2026, 1, 1), last_used=None, submissions=None,
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
            Question(question_id="name", type="input_text", text="Your name",
                     answer_config=AnswerConfig(fill_percentage=80, answers=["Ann", "Bob"])),
            Question(question_id="color", type="multiple_choice", text="Favourite color",
                     answer_config=AnswerConfig(fill_percentage=100, options=[
                         AnswerOption(text=text, percentage=100.0 if i == 0 else 0.0)
                         for i, text in enumerate(color_options)])),
            Question(question_id="cv", type="file_upload", text="CV", answer_config=None),
        ])]),
    )


class MemoryStorage:
    """Keeps forms as JSON so every load returns a fresh copy, like TinyDB."""

    def __init__(self, *forms):
        self.forms = {form.id: form.model_dump(mode="json") for form in forms}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def get_form_by_id(self, form_id):
        data = self.forms.get(form_id)
        return Form.model_validate(data) if data else None

    def save_form(self, form):
        self.forms[form.id] = form.model_dump(mode="json")
        return True


@pytest.fixture
def storage(storage_stub):
    return storage_stub(MemoryStorage(_form()))


def _config(storage, form_id="f_tpl"):
    return storage.forms[form_id]["response_config"]


def test_export_then_import_on_the_same_form_restores_the_configuration(client, storage):
    exported = client.get("/forms/f_tpl/config/export")
    template = exported.get_json()
    original = json.loads(json.dumps(_config(storage)))

    # Change the configuration, then bring it back from the exported file.
    storage.forms["f_tpl"]["response_config"]["pages"][0]["questions"][1]["answer_config"]["options"][0]["percentage"] = 0.0
    storage.forms["f_tpl"]["response_config"]["pages"][0]["questions"][0]["answer_config"]["answers"] = ["Zed"]
    preview = client.post("/forms/f_tpl/config/import", json={"template": template}).get_json()
    assert preview["applied"] is False
    assert preview["preview"]["same_structure"] is True

    result = client.post("/forms/f_tpl/config/import", json={"template": template, "apply": True}).get_json()

    assert exported.headers["Content-Disposition"].startswith("attachment")
    assert template["schema_version"] == 1
    assert result["applied"] is True
    assert _config(storage) == original


def test_import_into_a_different_form_applies_only_matching_questions(client, storage_stub):
    source = _form("f_src")
    source.response_config.pages[0].questions[0].answer_config.answers = ["From template"]
    target = _form("f_dst", color_options=("Red", "Green"))
    target.response_config.pages[0].questions[0].question_id = "different_id"
    storage = storage_stub(MemoryStorage(source, target))

    template = client.get("/forms/f_src/config/export").get_json()
    result = client.post("/forms/f_dst/config/import", json={"template": template, "apply": True}).get_json()
    preview = result["preview"]

    assert preview["same_structure"] is True
    assert {item["question_id"]: item["matched_by"] for item in preview["matched"]} == {"different_id": "text", "cv": "id"}
    assert preview["unmatched"] == [{"question_id": "color", "text": "Favourite color", "reason": "options_differ"}]
    assert preview["missing"] == [{"question_id": "color", "text": "Favourite color"}]
    questions = _config(storage, "f_dst")["pages"][0]["questions"]
    assert questions[0]["answer_config"]["answers"] == ["From template"]
    assert questions[1]["answer_config"]["options"][0]["percentage"] == 100.0  # untouched


@pytest.mark.parametrize("payload", [
    {"template": {"schema_version": 99, "name": "x", "created_at": "", "form_fingerprint": "", "questions": []}},
    {"template": {"schema_version": 1, "name": "x", "created_at": "", "form_fingerprint": "", "questions": [],
                  "api_key": "secret"}},
    {"template": {"schema_version": 1, "name": "x", "created_at": "", "form_fingerprint": "",
                  "questions": [{"question_id": "color", "type": "multiple_choice",
                                 "options": [{"text": "Red", "percentage": 150}]}]}},
    {"template": "not an object"},
    {},
])
def test_invalid_templates_are_rejected_and_the_form_is_unchanged(client, storage, payload):
    before = json.loads(json.dumps(_config(storage)))

    response = client.post("/forms/f_tpl/config/import", json=dict(payload, apply=True))

    assert response.status_code == 400
    assert _config(storage) == before


def test_uploaded_files_that_are_not_json_or_too_large_are_rejected(client, storage):
    before = json.loads(json.dumps(_config(storage)))

    not_json = client.post("/forms/f_tpl/config/import", data={"file": (io.BytesIO(b"\x00not json"), "t.json"),
                                                                 "apply": "true"})
    client.application.config["MAX_CONTENT_LENGTH"] = 1000
    too_large = client.post("/forms/f_tpl/config/import", data={"file": (io.BytesIO(b"{" + b" " * 5000 + b"}"), "t.json")})

    assert not_json.status_code == 400
    assert too_large.status_code == 413
    assert _config(storage) == before


def test_uploaded_template_file_is_previewed(client, storage):
    template = client.get("/forms/f_tpl/config/export").get_data()

    response = client.post("/forms/f_tpl/config/import", data={"file": (io.BytesIO(template), "config.json")})

    assert response.status_code == 200
    assert response.get_json()["applied"] is False


def test_template_menu_script_never_writes_html():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "static" / "js" / "form_filling" / "config_tools.js").read_text(
        encoding="utf-8")

    assert "innerHTML" not in source
    assert "textContent" in source


def test_saved_templates_can_be_listed_applied_and_deleted(client, storage):
    saved = client.post("/templates", json={"form_id": "f_tpl", "name": "Baseline"}).get_json()
    listed = client.get("/templates").get_json()["templates"]

    assert any(t["template_id"] == saved["template_id"] and t["name"] == "Baseline" for t in listed)
    applied = client.post("/forms/f_tpl/config/import", json={"template_id": saved["template_id"], "apply": True})
    assert applied.status_code == 200
    assert client.post(f"/templates/{saved['template_id']}/delete").get_json()["success"] is True
    assert client.post(f"/templates/{saved['template_id']}/delete").status_code == 404
    assert client.post("/forms/f_tpl/config/import", json={"template_id": saved["template_id"]}).status_code == 404
    assert client.post("/templates", json={"form_id": "f_tpl", "name": ""}).status_code == 400
    assert client.get("/forms/missing/config/export").status_code == 404

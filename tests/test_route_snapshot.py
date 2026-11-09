"""Route contract snapshot.

Pins every route of the ``main`` blueprint: rule, methods, endpoint name, and for
representative requests the status code plus the JSON key set (or content type).
It must stay green across refactors that move route code between modules.
No test here starts Selenium or touches the network.
"""
import importlib
import io
import json
from datetime import datetime

import pytest

from app.models import (
    AnswerConfig,
    AnswerOption,
    Form,
    Page,
    Question,
    ResponseConfig,
    Submission,
)

FORM_URL = "https://docs.google.com/forms/d/e/SNAPID/viewform"
FORM_ID = Form.get_id_from_url(FORM_URL)
EDIT_URL = "https://docs.google.com/forms/d/SNAPID/edit"

EXPECTED_ROUTES = {
    ("/healthz", ("GET",), "main.healthz"),
    ("/diagnostics/runtime", ("GET",), "main.runtime_diagnostics"),
    ("/", ("GET",), "main.index"),
    ("/forms/delete", ("POST",), "main.delete_form"),
    ("/form_filling", ("GET", "POST"), "main.form_filling"),
    ("/about", ("GET",), "main.about"),
    ("/settings/diagnostics", ("GET",), "main.settings_diagnostics"),
    ("/form_copy", ("GET",), "main.form_copy"),
    ("/form_copy/extract_source", ("POST",), "main.form_copy_extract_source"),
    ("/form_copy/preview_plan", ("POST",), "main.form_copy_preview_plan"),
    ("/form_copy/apply_to_target", ("POST",), "main.form_copy_apply_to_target"),
    ("/form_filling/extract", ("POST",), "main.extract"),
    ("/form_filling/preview", ("GET",), "main.preview"),
    ("/load_data", ("POST",), "main.load_data"),
    ("/validate_api_key", ("POST",), "main.validate_api_key"),
    ("/generate_ai_text_answers", ("POST",), "main.generate_ai_text_answers"),
    ("/save_edit", ("POST",), "main.save_edit"),
    ("/start_submission", ("POST",), "main.start_submission"),
    ("/stop_submission", ("POST",), "main.stop_submission"),
    ("/submission_status", ("GET",), "main.submission_status"),
    ("/submission_history/<form_id>", ("GET",), "main.submission_history"),
    ("/export_history/<form_id>", ("GET",), "main.export_history"),
}


def _snapshot_form() -> Form:
    return Form(
        id=FORM_ID,
        title="Snapshot Form",
        description="",
        url=FORM_URL,
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(
            pages=[
                Page(
                    page_id="page_1",
                    questions=[
                        Question(
                            question_id="111",
                            entry_id="entry.111",
                            type="input_text",
                            text="Name?",
                            answer_config=AnswerConfig(
                                fill_percentage=100, answers=["Alice"], options=None
                            ),
                        ),
                        Question(
                            question_id="222",
                            entry_id="entry.222",
                            type="multiple_choice",
                            text="Color?",
                            answer_config=AnswerConfig(
                                fill_percentage=100,
                                answers=None,
                                options=[
                                    AnswerOption(text="Red", percentage=100.0),
                                    AnswerOption(text="Blue", percentage=0.0),
                                ],
                            ),
                        ),
                    ],
                )
            ]
        ),
        submissions=[
            Submission(
                submission_id="sub_1",
                num_submission=1,
                concurrent_thread=1,
                time_used=10,
                success_rate=100.0,
                network_status="ok",
            )
        ],
    )


class _SharedStorage:
    """Hands the same open storage to every ``with get_storage_service()``."""

    def __init__(self, storage):
        self._storage = storage

    def __enter__(self):
        return self._storage

    def __exit__(self, exc_type, exc_value, traceback):
        return None


@pytest.fixture
def seeded(temp_db, storage_stub):
    temp_db.save_form(_snapshot_form())
    storage_stub(_SharedStorage(temp_db))
    return temp_db


def _patch_first(monkeypatch, module_names, attr, value):
    """Patch ``attr`` on the first importable module, so the test survives module moves."""
    for name in module_names:
        try:
            module = importlib.import_module(name)
        except ImportError:
            continue
        monkeypatch.setattr(module, attr, value)
        return
    raise AssertionError(f"none of {module_names} importable")


SUBMITTER_MODULES = ("app.adapters.browser.form_submitter",)
AI_MODULES = ("app.adapters.ai.ai_responder",)


class _FakeSubmitter:
    def __init__(self, **kwargs):
        pass

    def prepare_prefill_queue(self, **kwargs):
        return 2, {}, None

    def submit_form(self, **kwargs):
        return Submission(
            submission_id="fake",
            num_submission=2,
            concurrent_thread=1,
            time_used=1,
            success_rate=100.0,
            network_status="ok",
        )

    def get_status(self):
        return {"running": False}

    def stop(self):
        pass


class _FakeResponder:
    def __init__(self, api_key):
        pass

    def generate_text_variations(self, question, count, context=None):
        return ["a"] * count


def _keys(response):
    body = response.get_json()
    assert isinstance(body, dict), body
    return sorted(body)


# (id, method, url, request kwargs, status, sorted JSON keys)
JSON_CASES = [
    ("healthz", "get", "/healthz", {}, 200, ["status"]),
    ("delete-missing-url", "post", "/forms/delete", {"json": {}}, 400, ["error"]),
    ("delete-unknown", "post", "/forms/delete", {"json": {"form_url": "https://docs.google.com/forms/d/e/NOPE/viewform"}}, 404, ["error"]),
    ("delete-ok", "post", "/forms/delete", {"json": {"form_url": FORM_URL}}, 200, ["success"]),
    ("extract-empty", "post", "/form_filling/extract", {"json": {}}, 400, ["error"]),
    ("extract-bad-url", "post", "/form_filling/extract", {"json": {"form_url": "https://example.com/x"}}, 400, ["error"]),
    ("extract-cached", "post", "/form_filling/extract", {"json": {"form_url": FORM_URL}}, 200, ["message", "success"]),
    ("preview-no-session", "get", "/form_filling/preview", {}, 400, ["error"]),
    ("copy-source-empty", "post", "/form_copy/extract_source", {"json": {}}, 400, ["error"]),
    ("copy-source-bad-url", "post", "/form_copy/extract_source", {"json": {"form_url": "https://example.com/x"}}, 400, ["error"]),
    ("copy-source-cached", "post", "/form_copy/extract_source", {"json": {"form_url": FORM_URL}}, 200, ["form", "success"]),
    ("copy-plan-empty", "post", "/form_copy/preview_plan", {"json": {}}, 400, ["error"]),
    ("copy-plan-unknown", "post", "/form_copy/preview_plan", {"json": {"form_id": "nope"}}, 404, ["error"]),
    ("copy-plan-ok", "post", "/form_copy/preview_plan", {"json": {"form_id": FORM_ID}}, 200, ["plan", "success"]),
    ("copy-apply-empty", "post", "/form_copy/apply_to_target", {"json": {}}, 400, ["error"]),
    ("copy-apply-bad-url", "post", "/form_copy/apply_to_target", {"json": {"form_id": FORM_ID, "target_url": "https://example.com"}}, 400, ["error"]),
    ("copy-apply-no-ownership", "post", "/form_copy/apply_to_target", {"json": {"form_id": FORM_ID, "target_url": EDIT_URL}}, 400, ["error"]),
    ("load-no-form-id", "post", "/load_data", {"data": {}}, 400, ["error"]),
    ("load-no-file", "post", "/load_data", {"data": {"form_id": FORM_ID}}, 400, ["error"]),
    ("load-bad-suffix", "post", "/load_data", {"data": {"form_id": FORM_ID, "answer_file": (io.BytesIO(b"x"), "a.txt")}, "content_type": "multipart/form-data"}, 400, ["error"]),
    ("load-unknown-form", "post", "/load_data", {"data": {"form_id": "nope", "answer_file": (io.BytesIO(b"[]"), "a.json")}, "content_type": "multipart/form-data"}, 404, ["error"]),
    ("load-json-ok", "post", "/load_data", {"data": {"form_id": FORM_ID, "answer_file": (io.BytesIO(json.dumps([{"111": "Bob"}]).encode()), "a.json")}, "content_type": "multipart/form-data"}, 200, ["message", "preview", "row_count", "rows_loaded", "success", "upload_id"]),
    ("apikey-missing", "post", "/validate_api_key", {"json": {}}, 400, ["error", "valid"]),
    ("ai-text-missing", "post", "/generate_ai_text_answers", {"json": {}}, 400, ["error"]),
    ("ai-text-bad-count", "post", "/generate_ai_text_answers", {"json": {"form_id": FORM_ID, "question_id": "111", "api_key": "k", "count": 0}}, 400, ["error"]),
    ("ai-text-unknown-form", "post", "/generate_ai_text_answers", {"json": {"form_id": "nope", "question_id": "111", "api_key": "k"}}, 404, ["error"]),
    ("ai-text-unknown-question", "post", "/generate_ai_text_answers", {"json": {"form_id": FORM_ID, "question_id": "nope", "api_key": "k"}}, 404, ["error"]),
    ("ai-text-wrong-type", "post", "/generate_ai_text_answers", {"json": {"form_id": FORM_ID, "question_id": "222", "api_key": "k"}}, 400, ["error"]),
    ("ai-text-ok", "post", "/generate_ai_text_answers", {"json": {"form_id": FORM_ID, "question_id": "111", "api_key": "k", "count": 2}}, 200, ["answers", "success"]),
    ("save-edit-no-id", "post", "/save_edit", {"json": {}}, 400, ["error"]),
    ("save-edit-no-edits", "post", "/save_edit", {"json": {"form_id": FORM_ID}}, 400, ["error"]),
    ("save-edit-unknown", "post", "/save_edit", {"json": {"form_id": "nope", "edits": {"111": {}}}}, 404, ["error"]),
    ("save-edit-ok", "post", "/save_edit", {"json": {"form_id": FORM_ID, "edits": {"111": {"answers": ["Zed"]}}}}, 200, None),
    ("start-no-form-id", "post", "/start_submission", {"json": {}}, 400, ["error"]),
    ("start-bad-mode", "post", "/start_submission", {"json": {"form_id": FORM_ID, "submission_mode": "nope"}}, 400, ["error"]),
    ("start-bad-count", "post", "/start_submission", {"json": {"form_id": FORM_ID, "num_submissions": 0}}, 400, ["error"]),
    ("start-bad-upload", "post", "/start_submission", {"json": {"form_id": FORM_ID, "upload_id": "gone"}}, 400, ["error"]),
    ("start-unknown-form", "post", "/start_submission", {"json": {"form_id": "nope", "num_submissions": 1}}, 404, ["error"]),
    ("start-ok", "post", "/start_submission", {"json": {"form_id": FORM_ID, "num_submissions": 2, "concurrent_threads": 1}}, 200, ["message", "prepared_count", "submission_mode", "success", "warnings"]),
    ("stop-all", "post", "/stop_submission", {"json": {}}, 200, ["message", "success"]),
    ("stop-unknown", "post", "/stop_submission", {"json": {"form_id": "nope"}}, 200, ["message", "success"]),
    ("status-all", "get", "/submission_status", {}, 200, ["active_submissions", "count"]),
    ("status-unknown", "get", "/submission_status?form_id=nope", {}, 200, ["message", "running"]),
    ("history-ok", "get", f"/submission_history/{FORM_ID}", {}, 200, ["form_id", "submissions", "success", "title"]),
    ("history-unknown", "get", "/submission_history/nope", {}, 404, ["error"]),
    ("export-unknown", "get", "/export_history/nope", {}, 404, ["error"]),
]


@pytest.mark.parametrize(
    "method,url,kwargs,status,keys",
    [pytest.param(m, u, k, s, keys, id=i) for i, m, u, k, s, keys in JSON_CASES],
)
def test_json_route_contract(client, seeded, monkeypatch, method, url, kwargs, status, keys):
    _patch_first(monkeypatch, SUBMITTER_MODULES, "FormSubmitter", _FakeSubmitter)
    _patch_first(monkeypatch, AI_MODULES, "AIResponder", _FakeResponder)
    _patch_first(monkeypatch, AI_MODULES, "is_ai_available", lambda: True)

    response = getattr(client, method)(url, **kwargs)

    assert response.status_code == status
    if keys is not None:
        assert _keys(response) == keys


def test_preview_returns_stored_form_with_session(client, seeded):
    with client.session_transaction() as session:
        session["form_url"] = FORM_URL

    response = client.get("/form_filling/preview")

    assert response.status_code == 200
    assert _keys(response) == sorted(_snapshot_form().model_dump(mode="json"))


def test_preview_unknown_form_in_session(client, seeded):
    with client.session_transaction() as session:
        session["form_url"] = "https://docs.google.com/forms/d/e/NOPE/viewform"

    response = client.get("/form_filling/preview")

    assert response.status_code == 404
    assert _keys(response) == ["error"]


def test_runtime_diagnostics_keys(client):
    response = client.get("/diagnostics/runtime")

    assert response.status_code == 200
    assert {"app_data_path", "db_path", "log_path", "chrome_path", "chromedriver_path", "mode"} <= set(
        response.get_json()
    )


@pytest.mark.parametrize(
    "method,url",
    [
        ("get", "/"),
        ("get", "/form_filling"),
        ("post", "/form_filling"),
        pytest.param(
            "get",
            "/about",
            marks=pytest.mark.xfail(
                strict=True,
                raises=ValueError,
                reason="about.html passes a literal '%' through gettext; the page raises today",
            ),
        ),
        ("get", "/settings/diagnostics"),
        ("get", "/form_copy"),
    ],
)
def test_page_routes_render_html(client, seeded, method, url):
    response = getattr(client, method)(url)

    assert response.status_code == 200
    assert response.mimetype == "text/html"


def test_export_history_formats(client, seeded):
    csv_response = client.get(f"/export_history/{FORM_ID}")
    explicit_csv = client.get(f"/export_history/{FORM_ID}?format=csv")
    json_response = client.get(f"/export_history/{FORM_ID}?format=json")

    assert csv_response.status_code == 200
    assert csv_response.mimetype == "text/csv"
    assert csv_response.data.decode().splitlines()[0].startswith("submission_id,")
    assert explicit_csv.mimetype == "text/csv"
    assert json_response.status_code == 200
    assert json_response.mimetype == "application/json"
    assert json.loads(json_response.data)[0]["submission_id"] == "sub_1"


def test_main_blueprint_routes_match_expected_table(client):
    app = client.application
    actual = set()
    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith("main."):
            continue
        methods = tuple(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        actual.add((rule.rule, methods, rule.endpoint))

    assert actual == EXPECTED_ROUTES
    assert len(actual) == 22

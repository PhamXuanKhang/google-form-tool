"""A run started from /start_submission submits exactly its stored plan."""
import json
import threading
import time
from collections import Counter
from datetime import datetime

import pytest

import app.services.submission_manager as submission_manager
from app.adapters.browser import form_submitter as form_submitter_module
from app.adapters.browser.form_submitter import FormSubmitter
from app.domain.prefill_link_generator import PrefillLinkGenerator
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig
from app.services import set_run_store_provider
from app.services.run_store import RunStore


def _form():
    return Form(
        id="form_run",
        title="Run form",
        description="",
        url="https://docs.google.com/forms/d/e/RUN/viewform",
        created_at=datetime(2026, 1, 1),
        last_used=None,
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
            Question(question_id="111", entry_id="entry.111", type="input_text", text="Name",
                     answer_config=AnswerConfig(fill_percentage=100, answers=["Ann", "Bob", "Cid"])),
            Question(question_id="222", entry_id="entry.222", type="multiple_choice", text="Color",
                     answer_config=AnswerConfig(fill_percentage=100, options=[
                         AnswerOption(text="Red", percentage=70.0),
                         AnswerOption(text="Blue", percentage=30.0),
                     ])),
        ])]),
        submissions=None,
    )


class FakeStorage:
    def __init__(self, form):
        self.form = form
        self.saved = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def get_form_by_id(self, form_id):
        return self.form

    def add_submission(self, form_id, submission):
        self.saved.append(submission)
        return True


class FakeDriver:
    def quit(self):
        pass


class CapturingThread:
    instances = []

    def __init__(self, target, args):
        self.target = target
        self.args = args
        self.daemon = False
        CapturingThread.instances.append(self)

    def start(self):
        pass


@pytest.fixture
def run_store(tmp_path):
    store = RunStore(str(tmp_path / "db.json"), str(tmp_path / "runs"))
    set_run_store_provider(lambda: store)
    return store


@pytest.fixture(autouse=True)
def _clear_active():
    submission_manager.active_submitters.clear()
    yield
    submission_manager.active_submitters.clear()


@pytest.fixture
def started(client, monkeypatch, storage_stub, run_store):
    """Start a run through the route, then execute its background job inline."""
    storage = storage_stub(FakeStorage(_form()))
    monkeypatch.setattr(FormSubmitter, "initialize_driver", lambda self: FakeDriver())

    def start(**payload):
        CapturingThread.instances = []
        monkeypatch.setattr(threading, "Thread", CapturingThread)
        body = {"form_id": "form_run", "num_submissions": 12, "concurrent_threads": 3,
                "min_delay": 0, "max_delay": 0}
        body.update(payload)
        response = client.post("/start_submission", json=body)
        job = CapturingThread.instances[0] if CapturingThread.instances else None
        monkeypatch.setattr(threading, "Thread", _REAL_THREAD)
        if job is not None:
            job.target(*job.args)
        return response

    start.storage = storage
    return start


_REAL_THREAD = threading.Thread


def _sent_counter(items):
    return Counter(json.dumps(item, sort_keys=True) for item in items)


def test_prefill_run_submits_the_stored_plan(started, run_store, monkeypatch):
    sent = []
    lock = threading.Lock()

    def fake_submit(self, driver, url):
        with lock:
            sent.append(url)
        return True

    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", fake_submit)

    response = started(seed=77)
    data = response.get_json()

    assert response.status_code == 200
    assert data["seed"] == 77
    run = run_store.get_run(data["run_id"])
    rows = run_store.load_rows(data["run_id"])
    assert run["status"] == "completed"
    assert run["total"] == 12
    assert all(row["status"] == "success" for row in rows)
    generator = PrefillLinkGenerator(_form())
    assert Counter(sent) == Counter(generator.build_prefill_url(row["answers"]) for row in rows)
    assert len(started.storage.saved) == 1


def test_direct_run_submits_each_row_once_with_its_own_answers(started, run_store, monkeypatch):
    sent = []
    lock = threading.Lock()

    def fake_submit(self, driver):
        answers = dict(self.responses)
        time.sleep(0.002)  # let other workers interleave
        with lock:
            sent.append(answers)
        return dict(self.responses) == answers

    monkeypatch.setattr(FormSubmitter, "_submit_single_form", fake_submit)

    data = started(submission_mode="dom_fill", seed=5).get_json()
    rows = run_store.load_rows(data["run_id"])

    assert all(row["status"] == "success" for row in rows)
    assert _sent_counter(sent) == _sent_counter(row["answers"] for row in rows)


def test_same_seed_plans_the_same_rows(started, run_store, monkeypatch):
    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", lambda self, driver, url: True)

    first = started(seed=9).get_json()["run_id"]
    second = started(seed=9).get_json()["run_id"]

    answers = lambda run_id: [row["answers"] for row in run_store.load_rows(run_id)]  # noqa: E731
    assert answers(first) == answers(second)


def test_failed_rows_are_recorded_with_an_error(started, run_store, monkeypatch):
    calls = Counter()
    lock = threading.Lock()

    def flaky(self, driver, url):
        with lock:
            calls["n"] += 1
            return calls["n"] % 2 == 0

    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", flaky)

    data = started(num_submissions=6, concurrent_threads=1, seed=1).get_json()
    rows = run_store.load_rows(data["run_id"])

    assert Counter(row["status"] for row in rows) == {"success": 3, "failed": 3}
    assert all(row["error"] == "submit_failed" for row in rows if row["status"] == "failed")
    assert all(row["attempts"] == 1 and row["finished_at"] for row in rows)
    assert run_store.get_run(data["run_id"])["status"] == "completed"


def test_stopping_leaves_unsent_rows_planned(started, run_store, monkeypatch):
    def stop_after_first(self, driver, url):
        self.stop_flag.set()
        return True

    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", stop_after_first)

    data = started(num_submissions=5, concurrent_threads=1, seed=1).get_json()
    rows = run_store.load_rows(data["run_id"])

    assert [row["status"] for row in rows].count("success") == 1
    assert [row["status"] for row in rows].count("planned") == 4
    assert run_store.get_run(data["run_id"])["status"] == "stopped"


@pytest.mark.parametrize("seed", [-1, "abc", True, 2 ** 60])
def test_invalid_seed_is_rejected(started, seed):
    response = started(seed=seed)

    assert response.status_code == 400
    assert "Seed" in response.get_json()["error"]


def test_form_saved_by_version_one_runs(started, run_store, monkeypatch):
    legacy = Form.model_validate({
        "id": "form_run", "title": "Legacy", "description": "",
        "url": "https://docs.google.com/forms/d/e/LEGACY/viewform",
        "created_at": "2025-05-01T10:00:00", "last_used": None,
        "response_config": {"pages": [{"page_id": "p1", "questions": [
            {"question_id": "q1", "type": "multiple_choice", "text": "Pick",
             "answer_config": {"fill_percentage": 100, "answers": None,
                               "options": [{"text": "Yes", "percentage": 100.0, "next_page_id": None}]}},
        ]}]},
        "submissions": [],
    })
    started.storage.form = legacy
    monkeypatch.setattr(FormSubmitter, "_submit_single_form", lambda self, driver: True)

    data = started(submission_mode="dom_fill", num_submissions=2, concurrent_threads=1).get_json()

    rows = run_store.load_rows(data["run_id"])
    assert [row["answers"] for row in rows] == [{"q1": "Yes"}, {"q1": "Yes"}]
    assert run_store.get_run(data["run_id"])["status"] == "completed"


def test_unprefillable_form_fails_without_leaving_a_run(started, run_store):
    question = started.storage.form.response_config.pages[0].questions[0]
    question.question_id = "name_without_entry"
    question.entry_id = None

    response = started(num_submissions=2, concurrent_threads=1)

    assert response.status_code == 500
    assert run_store.list_runs() == []
    assert "form_run" not in submission_manager.active_submitters


def test_exception_during_a_row_records_unknown_not_failed(started, run_store, monkeypatch):
    def explode(self, driver, url):
        raise RuntimeError("browser crashed mid-submit")

    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", explode)

    data = started(num_submissions=2, concurrent_threads=1, seed=1).get_json()
    rows = run_store.load_rows(data["run_id"])

    assert [row["status"] for row in rows] == ["unknown", "unknown"]
    assert rows[0]["error"] == "RuntimeError"


def test_status_includes_run_id(started, client, monkeypatch):
    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", lambda self, driver, url: True)

    run_id = started(num_submissions=2, concurrent_threads=1).get_json()["run_id"]

    assert client.get("/submission_status?form_id=form_run").get_json()["run_id"] == run_id
    all_status = client.get("/submission_status").get_json()["active_submissions"]
    assert all_status["form_run"]["run_id"] == run_id


def test_submitter_module_constants_match_plan_modes():
    assert form_submitter_module.SUBMISSION_MODE_PREFILL == "prefill_link"
    assert form_submitter_module.SUBMISSION_MODE_DOM_FILL == "dom_fill"

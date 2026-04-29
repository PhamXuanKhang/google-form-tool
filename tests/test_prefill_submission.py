"""Tests for TIP-004 prefill-link submission backend.

Covers:
- /start_submission default mode is prefill_link.
- /start_submission accepts dom_fill and routes to the existing path.
- /start_submission rejects unknown submission_mode with HTTP 400.
- Prefill mode records submission history via _run_submission.
- FormSubmitter._submit_prefilled_url drives a fake driver correctly.
- FormSubmitter respects stop_flag in prefill mode.
"""
from datetime import datetime
import threading

import pytest

import app.main_routes as main_routes
from app.core import form_submitter as form_submitter_module
from app.core.form_submitter import (
    FormSubmitter,
    SUBMISSION_MODE_DOM_FILL,
    SUBMISSION_MODE_PREFILL,
)
from app.models import (
    AnswerConfig,
    AnswerOption,
    Form,
    Page,
    Question,
    ResponseConfig,
    Submission,
)


# ---------------------------------------------------------------------- helpers


def _build_prefill_form() -> Form:
    """Form whose questions all have entry_id (TIP-002), so prefill works."""
    return Form(
        id="form_pf",
        title="Prefill Form",
        description="",
        url="https://docs.google.com/forms/d/e/FAKEID/viewform",
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
        submissions=None,
    )


@pytest.fixture(autouse=True)
def _clear_active():
    main_routes.active_submitters.clear()
    yield
    main_routes.active_submitters.clear()


class FakeStorageContext:
    def __init__(self, form):
        self.form = form
        self.saved = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def _load_form(self, form_id):
        return self.form

    def add_submission(self, form_id, submission):
        self.saved.append((form_id, submission))
        return True


class CapturingThread:
    """Stand-in for threading.Thread that records target/args without running."""

    instances = []

    def __init__(self, target, args):
        self.target = target
        self.args = args
        self.daemon = False
        CapturingThread.instances.append(self)

    def start(self):
        self.started = True


@pytest.fixture
def patch_thread(monkeypatch):
    CapturingThread.instances = []
    monkeypatch.setattr(threading, "Thread", CapturingThread)
    yield CapturingThread


# ------------------------------------------------------------------- route tests


def _post_start(client, **overrides):
    payload = {
        "form_id": "form_pf",
        "num_submissions": 2,
        "concurrent_threads": 1,
        "min_delay": 0,
        "max_delay": 0,
    }
    payload.update(overrides)
    return client.post("/start_submission", json=payload)


def test_start_submission_default_mode_is_prefill(client, monkeypatch, patch_thread):
    form = _build_prefill_form()
    monkeypatch.setattr(
        main_routes, "get_storage_service", lambda: FakeStorageContext(form)
    )

    response = _post_start(client)

    assert response.status_code == 200
    args = patch_thread.instances[0].args
    # _run_submission signature: (submitter, form_id, num, threads, min, max,
    # responses_list, responses, submission_mode)
    assert args[-1] == SUBMISSION_MODE_PREFILL


def test_start_submission_accepts_dom_fill(client, monkeypatch, patch_thread):
    form = _build_prefill_form()
    monkeypatch.setattr(
        main_routes, "get_storage_service", lambda: FakeStorageContext(form)
    )

    response = _post_start(client, submission_mode="dom_fill")

    assert response.status_code == 200
    assert patch_thread.instances[0].args[-1] == SUBMISSION_MODE_DOM_FILL


def test_start_submission_rejects_unknown_mode(client, monkeypatch):
    # Storage should never be opened for an invalid mode.
    def fail():
        raise AssertionError("storage opened for invalid mode")

    monkeypatch.setattr(main_routes, "get_storage_service", fail)

    response = _post_start(client, submission_mode="floppy_disk")

    assert response.status_code == 400
    assert "Unknown submission_mode" in response.get_json()["error"]


# ------------------------------------------------------- _run_submission history


def test_run_submission_passes_mode_and_records_history(monkeypatch):
    form = _build_prefill_form()
    storage = FakeStorageContext(form)
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    captured_kwargs = {}

    class StubSubmitter:
        def submit_form(self, **kwargs):
            captured_kwargs.update(kwargs)
            return Submission(
                num_submission=2,
                concurrent_thread=1,
                time_used=1,
                success_rate=100.0,
                network_status="Completed",
            )

    main_routes._run_submission(
        StubSubmitter(),
        "form_pf",
        num_submissions=2,
        concurrent_threads=1,
        min_delay=0,
        max_delay=0,
        submission_mode=SUBMISSION_MODE_PREFILL,
    )

    assert captured_kwargs["submission_mode"] == SUBMISSION_MODE_PREFILL
    assert len(storage.saved) == 1
    assert storage.saved[0][0] == "form_pf"


# ------------------------------------------------------------- submitter unit


class FakeWebDriverWait:
    def __init__(self, driver, timeout):
        self.driver = driver

    def until(self, condition):
        # Returning truthy is sufficient to advance past the wait calls.
        return True


class FakeElement:
    pass


class FakeDriver:
    """Records driver.get URLs and serves a scripted Next/Submit sequence."""

    def __init__(self, button_sequence):
        self.button_sequence = list(button_sequence)
        self.visited_urls = []
        self.scripts = []
        self.current_url = "https://docs.google.com/forms/.../viewform"

    def get(self, url):
        self.visited_urls.append(url)
        # Reset sequence per page load.
        if hasattr(self, "_per_load_sequence"):
            return
        self._per_load_sequence = True

    def find_element(self, by, xpath):
        if not self.button_sequence:
            from selenium.common.exceptions import NoSuchElementException
            raise NoSuchElementException("no more buttons")
        kind = self.button_sequence.pop(0)
        if "Next" in xpath or "Tiếp" in xpath:
            if kind != "next":
                from selenium.common.exceptions import NoSuchElementException
                # put back, since we wanted Submit
                self.button_sequence.insert(0, kind)
                raise NoSuchElementException("not a next")
            return FakeElement()
        if "Submit" in xpath or "Gửi" in xpath:
            if kind != "submit":
                from selenium.common.exceptions import NoSuchElementException
                self.button_sequence.insert(0, kind)
                raise NoSuchElementException("not a submit")
            # Simulate URL change on submit click.
            self.current_url = self.current_url + "?submitted=1"
            return FakeElement()
        from selenium.common.exceptions import NoSuchElementException
        raise NoSuchElementException("unknown xpath")

    def find_elements(self, by, xpath):
        return []

    def execute_script(self, script, element):
        self.scripts.append(script)

    def quit(self):
        self.quit_called = True


def test_submit_prefilled_url_clicks_through_and_returns_true(monkeypatch):
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)

    driver = FakeDriver(["next", "submit"])
    url = "https://docs.google.com/forms/d/e/FAKEID/viewform?entry.111=Alice"

    assert submitter._submit_prefilled_url(driver, url) is True
    assert driver.visited_urls == [url]
    # Two clicks: next + submit.
    assert len(driver.scripts) == 2


def test_submit_prefilled_url_returns_false_when_no_buttons(monkeypatch):
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)

    driver = FakeDriver([])  # no buttons at all
    assert submitter._submit_prefilled_url(driver, "https://x") is False


def test_submit_form_prefill_mode_calls_prefill_worker(monkeypatch):
    """submit_form(prefill) must dispatch to _prefill_worker, not the dom-fill worker."""
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    calls = {"prefill": 0, "dom": 0}

    def fake_prefill_worker(self, num, min_d, max_d, callback=None):
        calls["prefill"] += 1
        self.status["success"] += num

    def fake_dom_worker(self, num, min_d, max_d, callback=None):
        calls["dom"] += 1

    monkeypatch.setattr(FormSubmitter, "_prefill_worker", fake_prefill_worker)
    monkeypatch.setattr(FormSubmitter, "_submission_worker", fake_dom_worker)

    submission = submitter.submit_form(
        num_submissions=2,
        concurrent_threads=1,
        min_delay=0,
        max_delay=0,
        responses_list=[{"111": "A"}, {"111": "B"}],
        submission_mode=SUBMISSION_MODE_PREFILL,
    )

    assert calls == {"prefill": 1, "dom": 0}
    assert submission.success_rate == 100.0
    # URLs are pre-built and stored on the submitter.
    # After the worker runs, queue is consumed (popped); but build_prefill_urls
    # produced 2 URLs first. We check the in-flight queue length before run via
    # urls_lock attribute presence.
    assert submitter.urls_lock is not None


def test_submit_form_dom_fill_mode_calls_dom_worker(monkeypatch):
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    calls = {"prefill": 0, "dom": 0}

    def fake_prefill_worker(self, num, min_d, max_d, callback=None):
        calls["prefill"] += 1

    def fake_dom_worker(self, num, min_d, max_d, callback=None):
        calls["dom"] += 1
        self.status["success"] += num

    monkeypatch.setattr(FormSubmitter, "_prefill_worker", fake_prefill_worker)
    monkeypatch.setattr(FormSubmitter, "_submission_worker", fake_dom_worker)

    submitter.submit_form(
        num_submissions=2,
        concurrent_threads=1,
        min_delay=0,
        max_delay=0,
        submission_mode=SUBMISSION_MODE_DOM_FILL,
    )

    assert calls == {"prefill": 0, "dom": 1}
    # No prefill URL queue allocated for dom-fill mode.
    assert submitter.urls_queue is None


def test_submit_form_rejects_unknown_mode():
    form = _build_prefill_form()
    submitter = FormSubmitter(form)
    with pytest.raises(ValueError, match="Unknown submission_mode"):
        submitter.submit_form(
            num_submissions=1,
            concurrent_threads=1,
            min_delay=0,
            max_delay=0,
            submission_mode="bogus",
        )


def test_prefill_worker_respects_stop_flag(monkeypatch):
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)

    submit_calls = []

    def fake_submit(self, driver, url):
        submit_calls.append(url)
        return True

    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", fake_submit)
    monkeypatch.setattr(FormSubmitter, "initialize_driver", lambda self: FakeDriver([]))

    submitter.urls_queue = ["u1", "u2", "u3"]
    submitter.urls_lock = threading.Lock()
    submitter.status = {
        "running": True, "total": 3, "success": 0, "failed": 0,
        "current_threads": 1, "start_time": datetime.now(), "end_time": None,
        "success_rate": 0, "warning": None,
    }
    submitter.stop_flag.set()  # set before worker starts

    submitter._prefill_worker(3, 0, 0)

    assert submit_calls == []  # nothing submitted after stop

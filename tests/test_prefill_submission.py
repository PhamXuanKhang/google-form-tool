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
    main_routes._upload_cache.clear()
    yield
    main_routes.active_submitters.clear()
    main_routes._upload_cache.clear()


class FakeStorageContext:
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
    # _run_submission signature ends with submission_mode, upload_id.
    assert args[-2] == SUBMISSION_MODE_PREFILL
    assert args[-1] is None


def test_start_submission_uses_cached_upload_id(client, monkeypatch, patch_thread):
    form = _build_prefill_form()
    monkeypatch.setattr(
        main_routes, "get_storage_service", lambda: FakeStorageContext(form)
    )
    main_routes._upload_cache["abc123"] = {
        "responses": [{"111": "Alice"}, {"111": "Bob"}],
        "created_at": main_routes.time.monotonic(),
    }

    response = _post_start(client, upload_id="abc123", num_submissions=2)

    assert response.status_code == 200
    args = patch_thread.instances[0].args
    assert args[6] == [{"111": "Alice"}, {"111": "Bob"}]
    assert args[-1] == "abc123"


def test_start_submission_rejects_missing_upload_id(client, monkeypatch, patch_thread):
    form = _build_prefill_form()
    monkeypatch.setattr(
        main_routes, "get_storage_service", lambda: FakeStorageContext(form)
    )

    response = _post_start(client, upload_id="missing")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Upload expired or not found. Please re-upload."


def test_start_submission_prefill_prepares_queue_before_thread(client, monkeypatch, patch_thread):
    form = _build_prefill_form()
    monkeypatch.setattr(
        main_routes, "get_storage_service", lambda: FakeStorageContext(form)
    )

    captured = {}

    class CapturingSubmitter(FormSubmitter):
        def prepare_prefill_queue(self, *args, **kwargs):
            captured["called"] = True
            captured["args"] = args
            captured["kwargs"] = kwargs
            return 2, {}, "https://docs.google.com/forms/d/e/FAKEID/viewform?usp=pp_url&entry.111=Alice"

    monkeypatch.setattr(form_submitter_module, "FormSubmitter", CapturingSubmitter)

    response = _post_start(client)
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["prepared_count"] == 2
    assert captured["called"] is True
    assert patch_thread.instances[0].started is True


def test_prepare_prefill_queue_keeps_rank_question():
    form = _build_prefill_form()
    form.response_config.pages[0].questions.append(
        Question(
            question_id="333",
            entry_id="entry.333",
            type="rank",
            text="Rank?",
            answer_config=AnswerConfig(
                fill_percentage=None,
                answers=None,
                options=[
                    AnswerOption(text="1", percentage=100),
                    AnswerOption(text="2", percentage=0),
                ],
            ),
        )
    )
    submitter = FormSubmitter(form)

    prepared_count, skipped_summary, debug_sample = submitter.prepare_prefill_queue(
        1, responses=None, responses_list=None, include_debug_sample=True
    )

    assert prepared_count == 1
    assert skipped_summary == {}
    assert "entry.333=1" in submitter.urls_queue[0]
    assert debug_sample != submitter.urls_queue[0]
    assert "entry.333=%5BREDACTED%5D" in debug_sample
    assert "entry.333=1" in submitter.urls_queue[0]


def test_start_submission_accepts_dom_fill(client, monkeypatch, patch_thread):
    form = _build_prefill_form()
    monkeypatch.setattr(
        main_routes, "get_storage_service", lambda: FakeStorageContext(form)
    )

    response = _post_start(client, submission_mode="dom_fill")

    assert response.status_code == 200
    assert patch_thread.instances[0].args[-2] == SUBMISSION_MODE_DOM_FILL
    assert patch_thread.instances[0].args[-1] is None


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
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support import expected_conditions as EC

        # staleness_of is always True in tests (page navigates after Submit click).
        if isinstance(EC.staleness_of, type) and isinstance(condition, EC.staleness_of):
            return True
        if getattr(condition, "__qualname__", "") == "staleness_of.<locals>._predicate":
            return True

        try:
            result = condition(self.driver)
            if not result:
                raise TimeoutException("Condition returned falsy")
            return result
        except TimeoutException:
            raise
        except Exception:
            raise TimeoutException("Condition threw exception")


class FakeElement:
    def __init__(self, text="", kind=None):
        self.text = text
        self.kind = kind

    def is_enabled(self):
        return True

    def is_displayed(self):
        return True


class FakeTextDriver:
    def __init__(self, containers=None, elements=None):
        self.containers = containers or []
        self.elements = elements or []

    def find_elements(self, by, xpath):
        if xpath == "//div[@data-params]":
            return self.containers
        if xpath == "//div[@role='button']":
            return self.elements
        if "required" in xpath or "bắt buộc" in xpath:
            return self.elements
        return []


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
        if xpath == "//div[@role='button']":
            if not self.button_sequence:
                return []
            kind = self.button_sequence[0]
            if kind == "next":
                return [FakeElement("Tiếp", kind="next")]
            if kind == "submit":
                return [FakeElement("Gửi", kind="submit")]
        return []

    def execute_script(self, script, element):
        self.scripts.append(script)
        if "click" in script and getattr(element, "kind", None):
            if self.button_sequence and self.button_sequence[0] == element.kind:
                self.button_sequence.pop(0)
            if element.kind == "submit":
                self.current_url = self.current_url + "?submitted=1"

    def quit(self):
        self.quit_called = True


class FakeChoiceElement:
    def __init__(self, role=None, checked=False, children=None):
        self.role = role
        self.checked = checked
        self.children = children or []

    def find_elements(self, by, xpath):
        if "@aria-checked='true'" in xpath:
            return [child for child in self.children if child.checked]
        if "@role='radio'" in xpath:
            return [child for child in self.children if child.role == "radio"]
        if "@role='checkbox'" in xpath:
            return [child for child in self.children if child.role == "checkbox"]
        return []

    def find_element(self, by, xpath):
        elements = self.find_elements(by, xpath)
        if not elements:
            from selenium.common.exceptions import NoSuchElementException
            raise NoSuchElementException("not found")
        return elements[0]


class FakeChoiceDriver:
    def __init__(self):
        self.radio_blank = FakeChoiceElement(children=[
            FakeChoiceElement(role="radio"),
            FakeChoiceElement(role="radio"),
        ])
        self.radio_prefilled = FakeChoiceElement(children=[
            FakeChoiceElement(role="radio", checked=True),
            FakeChoiceElement(role="radio"),
        ])
        self.checkbox_blank = FakeChoiceElement(children=[
            FakeChoiceElement(role="checkbox"),
            FakeChoiceElement(role="checkbox"),
        ])
        self.checkbox_prefilled = FakeChoiceElement(children=[
            FakeChoiceElement(role="checkbox", checked=True),
            FakeChoiceElement(role="checkbox"),
        ])
        self.clicked = []

    def find_elements(self, by, xpath):
        if "@role='radiogroup'" in xpath:
            return [self.radio_blank, self.radio_prefilled]
        if "@data-params" in xpath and "@role='checkbox'" in xpath:
            return [self.checkbox_blank, self.checkbox_prefilled]
        return []

    def execute_script(self, script, element):
        element.checked = True
        self.clicked.append(element)


def test_fill_unanswered_choice_controls_preserves_prefilled_choices():
    submitter = FormSubmitter(_build_prefill_form())
    driver = FakeChoiceDriver()

    submitter._fill_unanswered_choice_controls(driver)

    assert len(driver.clicked) == 2
    assert driver.radio_blank.children[0].checked is True
    assert driver.radio_prefilled.children[0].checked is True
    assert driver.radio_prefilled.children[1].checked is False
    assert driver.checkbox_blank.children[0].checked is True
    assert driver.checkbox_prefilled.children[0].checked is True
    assert driver.checkbox_prefilled.children[1].checked is False


def test_submit_prefilled_url_clicks_through_and_returns_true(monkeypatch):
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)

    driver = FakeDriver(["next", "submit"])
    url = "https://docs.google.com/forms/d/e/FAKEID/viewform?entry.111=Alice"

    assert submitter._submit_prefilled_url(driver, url) is True
    assert driver.visited_urls == [url]
    # Four execute_script calls: scrollIntoView + click for next, scrollIntoView + click for submit.
    assert len(driver.scripts) == 4


def test_submit_prefilled_url_returns_false_when_no_buttons(monkeypatch):
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)

    driver = FakeDriver([])  # no buttons at all
    assert submitter._submit_prefilled_url(driver, "https://x") is False


class FakeValidationDriver(FakeDriver):
    def __init__(self):
        super().__init__(["submit"])

    def find_element(self, by, xpath):
        if "Submit" in xpath or "Gửi" in xpath:
            if not self.button_sequence:
                from selenium.common.exceptions import NoSuchElementException
                raise NoSuchElementException("no submit")
            self.button_sequence.pop(0)
            return FakeElement()
        return super().find_element(by, xpath)

    def find_elements(self, by, xpath):
        if xpath == "//div[@role='button']":
            return [FakeElement("G", kind="submit")]
        if "required" in xpath or "bắt buộc" in xpath:
            return [FakeElement("This is a required question")]
        return []


def test_submit_prefilled_url_returns_false_on_validation_error(monkeypatch):
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)

    driver = FakeValidationDriver()

    assert submitter._submit_prefilled_url(driver, "https://x") is False


def test_find_form_button_matches_decomposed_vietnamese_and_g_fallback():
    submitter = FormSubmitter(_build_prefill_form())

    next_driver = FakeTextDriver(elements=[FakeElement("Gu\u031bi", kind="submit")])
    assert submitter._find_form_button(next_driver, ("submit", "gui")).text == "Gu\u031bi"

    g_driver = FakeTextDriver(elements=[FakeElement("G", kind="submit")])
    assert (
        submitter._find_form_button(g_driver, ("submit", "gui"), fallback_initials=("g",)).text
        == "G"
    )


def test_prefill_diagnostics_ignore_required_legend_text():
    submitter = FormSubmitter(_build_prefill_form())
    driver = FakeTextDriver(elements=[FakeElement("* Biểu thị câu hỏi bắt buộc")])

    assert submitter._collect_prefill_submit_diagnostics(driver) == ""


def test_prefill_diagnostics_include_question_title_for_required_error():
    submitter = FormSubmitter(_build_prefill_form())
    driver = FakeTextDriver(
        containers=[
            FakeElement("Test rank\n1\n2\n3\nĐây là một câu hỏi bắt buộc")
        ]
    )

    assert (
        submitter._collect_prefill_submit_diagnostics(driver)
        == "Test rank: Đây là một câu hỏi bắt buộc"
    )


def test_format_prefill_url_for_log_redacts_answer_values():
    url = (
        "https://docs.google.com/forms/d/e/FAKEID/viewform?"
        "usp=pp_url&entry.111=Alice&entry.222=Blue&emailAddress=a@example.com"
    )

    formatted = FormSubmitter._format_prefill_url_for_log(url)

    assert "usp=pp_url" in formatted
    assert "entry.111=%5BREDACTED%5D" in formatted
    assert "entry.222=%5BREDACTED%5D" in formatted
    assert "emailAddress=%5BREDACTED%5D" in formatted
    assert "Alice" not in formatted
    assert "Blue" not in formatted
    assert "a%40example.com" not in formatted


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


def test_submit_prefilled_urls_uses_caller_provided_urls(monkeypatch):
    """submit_prefilled_urls(["u1","u2"]) must submit exactly u1 and u2 in order
    and must NOT invoke PrefillLinkGenerator (the URLs are already prepared)."""
    form = _build_prefill_form()
    submitter = FormSubmitter(form)

    # Fail loudly if the generator is touched.
    class ExplodingGenerator:
        def __init__(self, *a, **kw):
            raise AssertionError(
                "PrefillLinkGenerator must not be called when caller "
                "supplies URLs to submit_prefilled_urls"
            )

    monkeypatch.setattr(
        form_submitter_module, "PrefillLinkGenerator", ExplodingGenerator
    )
    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)
    monkeypatch.setattr(
        FormSubmitter, "initialize_driver", lambda self: FakeDriver([])
    )

    received = []

    def fake_submit(self, driver, url):
        received.append(url)
        return True

    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", fake_submit)

    submission = submitter.submit_prefilled_urls(
        ["u1", "u2"], concurrent_threads=1, min_delay=0, max_delay=0
    )

    assert received == ["u1", "u2"]
    assert submission.num_submission == 2
    assert submission.success_rate == 100.0


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

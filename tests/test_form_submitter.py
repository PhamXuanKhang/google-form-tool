from datetime import datetime

from app.core import form_submitter as form_submitter_module
from app.core.form_submitter import FormSubmitter
from app.models import Form, ResponseConfig, Submission


class FakeDriver:
    def __init__(self):
        self.get_url = None

    def get(self, url):
        self.get_url = url


class FakeWebDriverWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, condition):
        return True


def test_submit_single_form_passes_plain_string_url_to_driver(monkeypatch):
    form = Form(
        id="form_001",
        title="Test Form",
        description="Test description",
        url="https://example.com/test-form",
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(pages=[]),
        submissions=None,
    )
    submitter = FormSubmitter(form)
    driver = FakeDriver()

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)
    monkeypatch.setattr(submitter, "_fill_page", lambda driver, page_num: False)

    result = submitter._submit_single_form(driver)

    assert result is False
    assert isinstance(driver.get_url, str)
    assert driver.get_url == "https://example.com/test-form"


def test_submit_form_distributes_remainder_for_direct_usage(monkeypatch):
    form = Form(
        id="form_001",
        title="Test Form",
        description="Test description",
        url="https://example.com/test-form",
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(pages=[]),
        submissions=None,
    )
    submitter = FormSubmitter(form)
    captured = []

    def fake_worker(count, min_delay, max_delay, callback=None):
        captured.append(count)

    class ImmediateThread:
        def __init__(self, target, args):
            self.target = target
            self.args = args

        def start(self):
            self.target(*self.args)

        def join(self):
            return None

    monkeypatch.setattr(form_submitter_module.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(submitter, "_prefill_worker", fake_worker)
    monkeypatch.setattr(submitter, "prepare_prefill_queue", lambda *args, **kwargs: (7, {}, None))
    submitter.urls_queue = [f"https://example.com/{i}" for i in range(7)]
    submitter.urls_lock = form_submitter_module.threading.Lock()

    submission = submitter.submit_form(num_submissions=7, concurrent_threads=3)

    assert captured == [3, 2, 2]
    assert submission.num_submission == 7
    assert submitter.get_status()["running"] is False


def test_submit_form_marks_failed_worker_crash_as_finished(monkeypatch):
    form = Form(
        id="form_001",
        title="Test Form",
        description="Test description",
        url="https://example.com/test-form",
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(pages=[]),
        submissions=None,
    )
    submitter = FormSubmitter(form)

    def crashing_worker(count, min_delay, max_delay, callback=None):
        submitter._increment_status("failed", count)
        submitter._increment_status("current_threads", -1)
        raise RuntimeError("worker crash")

    class CapturingThread:
        def __init__(self, target, args):
            self.target = target
            self.args = args
            self.error = None

        def start(self):
            try:
                self.target(*self.args)
            except RuntimeError as exc:
                self.error = exc

        def join(self):
            return None

    monkeypatch.setattr(form_submitter_module.threading, "Thread", CapturingThread)
    monkeypatch.setattr(submitter, "_prefill_worker", crashing_worker)
    submitter.urls_queue = [f"https://example.com/{i}" for i in range(5)]
    submitter.urls_lock = form_submitter_module.threading.Lock()

    submitter.submit_form(num_submissions=5, concurrent_threads=2)
    status = submitter.get_status()

    assert status["running"] is False
    assert status["current_threads"] == 0
    assert status["failed"] == 5

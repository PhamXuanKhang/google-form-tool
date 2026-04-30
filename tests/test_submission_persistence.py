import threading

import pytest

import app.main_routes as main_routes
from app.models import Submission


@pytest.fixture(autouse=True)
def clear_active_submitters():
    main_routes.active_submitters.clear()
    yield
    main_routes.active_submitters.clear()


class FakeStorageContext:
    def __init__(self, form=None, save_result=True):
        self.form = form
        self.save_result = save_result
        self.saved = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True
        return None

    def _load_form(self, form_id):
        return self.form

    def add_submission(self, form_id, submission):
        self.saved.append((form_id, submission))
        return self.save_result


class FakeSubmitter:
    def __init__(self, submission=None):
        self.submission = submission or Submission(
            num_submission=1,
            concurrent_thread=1,
            time_used=1,
            success_rate=100,
            network_status="Completed",
        )
        self.status = {"running": False}
        self.stopped = False

    def submit_form(self, **kwargs):
        return self.submission

    def stop(self):
        self.stopped = True

    def prepare_prefill_queue(self, num_submissions, responses, responses_list, include_debug_sample=False):
        return num_submissions, {}, None


def test_run_submission_opens_fresh_storage_for_history(monkeypatch):
    storage = FakeStorageContext()
    submitter = FakeSubmitter()

    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    main_routes._run_submission(
        submitter,
        "form_001",
        num_submissions=1,
        concurrent_threads=1,
        min_delay=1,
        max_delay=1,
    )

    assert storage.saved == [("form_001", submitter.submission)]
    assert storage.closed is True


def test_run_submission_logs_warning_when_history_save_fails(monkeypatch, caplog):
    storage = FakeStorageContext(save_result=False)
    submitter = FakeSubmitter()

    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    main_routes._run_submission(
        submitter,
        "missing_form",
        num_submissions=1,
        concurrent_threads=1,
        min_delay=1,
        max_delay=1,
    )

    assert "Submission history was not saved because form missing_form was not found" in caplog.text


def test_start_submission_does_not_pass_route_storage_to_thread(client, sample_form, monkeypatch):
    route_storage = FakeStorageContext(form=sample_form)
    captured = {}

    class CapturingThread:
        def __init__(self, target, args):
            captured["target"] = target
            captured["args"] = args
            self.daemon = False

        def start(self):
            captured["started"] = True

    class RouteSubmitter(FakeSubmitter):
        def __init__(self, **kwargs):
            super().__init__()
            self.form = kwargs["form"]

    monkeypatch.setattr(main_routes, "get_storage_service", lambda: route_storage)
    monkeypatch.setattr(threading, "Thread", CapturingThread)
    monkeypatch.setattr("app.core.form_submitter.FormSubmitter", RouteSubmitter)

    response = client.post(
        "/start_submission",
        json={
            "form_id": sample_form.id,
            "num_submissions": 1,
            "concurrent_threads": 1,
            "min_delay": 1,
            "max_delay": 1,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert captured["target"] is main_routes._run_submission
    assert captured["started"] is True
    assert route_storage not in captured["args"]
    assert captured["args"][1] == sample_form.id


def post_invalid_submission_request(client, monkeypatch, sample_form, payload):
    def fail_if_storage_opens():
        raise AssertionError("storage should not be opened for invalid submission settings")

    monkeypatch.setattr(main_routes, "get_storage_service", fail_if_storage_opens)

    response = client.post(
        "/start_submission",
        json={"form_id": sample_form.id, **payload},
    )

    assert response.status_code == 400
    return response.get_json()["error"]


def test_start_submission_rejects_too_many_submissions(client, sample_form, monkeypatch):
    error = post_invalid_submission_request(
        client,
        monkeypatch,
        sample_form,
        {"num_submissions": 501, "concurrent_threads": 1},
    )

    assert "Number of submissions must be between 1 and 500" in error


def test_start_submission_rejects_too_many_threads(client, sample_form, monkeypatch):
    error = post_invalid_submission_request(
        client,
        monkeypatch,
        sample_form,
        {"num_submissions": 20, "concurrent_threads": 11},
    )

    assert "Concurrent threads must be between 1 and 10" in error


def test_start_submission_rejects_threads_greater_than_submissions(client, sample_form, monkeypatch):
    error = post_invalid_submission_request(
        client,
        monkeypatch,
        sample_form,
        {"num_submissions": 2, "concurrent_threads": 3},
    )

    assert "Concurrent threads cannot be greater than the number of submissions" in error


def test_start_submission_rejects_invalid_delay_range(client, sample_form, monkeypatch):
    error = post_invalid_submission_request(
        client,
        monkeypatch,
        sample_form,
        {"num_submissions": 2, "concurrent_threads": 1, "min_delay": 5, "max_delay": 1},
    )

    assert "Maximum delay must be greater than or equal to minimum delay" in error


def test_start_submission_rejects_float_count_fields(client, sample_form, monkeypatch):
    error = post_invalid_submission_request(
        client,
        monkeypatch,
        sample_form,
        {"num_submissions": 1.5, "concurrent_threads": 1},
    )

    assert "Number of submissions must be an integer" in error


def test_start_submission_accepts_simple_string_values(client, sample_form, monkeypatch):
    route_storage = FakeStorageContext(form=sample_form)
    captured = {}

    class CapturingThread:
        def __init__(self, target, args):
            captured["args"] = args
            self.daemon = False

        def start(self):
            captured["started"] = True

    class RouteSubmitter(FakeSubmitter):
        def __init__(self, **kwargs):
            super().__init__()

    monkeypatch.setattr(main_routes, "get_storage_service", lambda: route_storage)
    monkeypatch.setattr(threading, "Thread", CapturingThread)
    monkeypatch.setattr("app.core.form_submitter.FormSubmitter", RouteSubmitter)

    response = client.post(
        "/start_submission",
        json={
            "form_id": sample_form.id,
            "num_submissions": "5",
            "concurrent_threads": "2",
            "min_delay": "0.5",
            "max_delay": "2",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert captured["started"] is True
    assert captured["args"][2:6] == (5, 2, 0.5, 2.0)

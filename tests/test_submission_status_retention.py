"""Tests for A-3 (409 duplicate) and A-4 (status retention TTL).

A-3: /start_submission returns 409 when a submission is already running
     for the same form_id; does NOT stop the existing submitter.

A-4: After submission ends, get_status() is still reachable for
     FINISHED_STATUS_TTL seconds. After the TTL, cleanup removes the
     submitter and /submission_status returns the "No submission" sentinel.
"""
import time

import pytest

import app.main_routes as main_routes
from app.main_routes import FINISHED_STATUS_TTL


# ------------------------------------------------------------------ helpers

def _make_mock_submitter(running: bool, finished_at: float | None = None):
    class MockSubmitter:
        def get_status(self):
            return {
                "running": running,
                "total": 5,
                "completed": 5 if not running else 0,
                "success": 5 if not running else 0,
                "failed": 0,
                "current_threads": 0,
                "elapsed_time": 10,
                "success_rate": 100.0 if not running else 0.0,
                "warning": None,
            }

    sub = MockSubmitter()
    if finished_at is not None:
        sub._finished_at = finished_at
    return sub


@pytest.fixture(autouse=True)
def _clear_submitters():
    main_routes.active_submitters.clear()
    yield
    main_routes.active_submitters.clear()


# ------------------------------------------------------------------ A-3 tests

def test_duplicate_start_returns_409(client, monkeypatch):
    """Second /start_submission for the same form while running → 409."""
    running_sub = _make_mock_submitter(running=True)
    monkeypatch.setattr(main_routes, "active_submitters", {"form_dup": running_sub})

    resp = client.post(
        "/start_submission",
        json={
            "form_id": "form_dup",
            "num_submissions": 1,
            "concurrent_threads": 1,
            "min_delay": 0,
            "max_delay": 0,
        },
    )
    assert resp.status_code == 409
    assert "already running" in resp.get_json()["error"]


def test_duplicate_start_does_not_stop_existing(client, monkeypatch):
    """The existing running submitter must NOT be stopped on 409."""
    stop_called = {"flag": False}

    class RunningSubmitter:
        def get_status(self):
            return {"running": True}

        def stop(self):
            stop_called["flag"] = True

    monkeypatch.setattr(main_routes, "active_submitters", {"form_x": RunningSubmitter()})

    client.post(
        "/start_submission",
        json={"form_id": "form_x", "num_submissions": 1, "concurrent_threads": 1,
              "min_delay": 0, "max_delay": 0},
    )
    assert stop_called["flag"] is False


# ------------------------------------------------------------------ A-4 tests

def test_status_retained_immediately_after_finish(client, monkeypatch):
    """Poll right after finish → final status still present."""
    finished_sub = _make_mock_submitter(running=False, finished_at=time.monotonic())
    monkeypatch.setattr(main_routes, "active_submitters", {"form_ret": finished_sub})

    resp = client.get("/submission_status?form_id=form_ret")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["running"] is False
    assert data["total"] == 5
    assert data["success"] == 5


def test_status_cleared_after_ttl(client, monkeypatch):
    """Poll after TTL has expired → submitter cleaned up → 'No submission'."""
    old_time = time.monotonic() - (FINISHED_STATUS_TTL + 1)
    stale_sub = _make_mock_submitter(running=False, finished_at=old_time)
    submitters = {"form_stale": stale_sub}
    monkeypatch.setattr(main_routes, "active_submitters", submitters)

    main_routes._cleanup_finished_submitters()

    resp = client.get("/submission_status?form_id=form_stale")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["running"] is False
    assert "No submission" in data.get("message", "")


def test_running_submitter_not_cleaned_up(monkeypatch):
    """A still-running submitter must never be removed by cleanup."""
    running_sub = _make_mock_submitter(running=True)
    submitters = {"form_live": running_sub}
    monkeypatch.setattr(main_routes, "active_submitters", submitters)

    main_routes._cleanup_finished_submitters()

    assert "form_live" in submitters


def test_run_submission_sets_finished_at(monkeypatch):
    """_run_submission must set _finished_at on the submitter after it ends."""
    from app.models import Submission

    class StubSubmitter:
        pass  # no _finished_at initially

    storage_stub = type("S", (), {
        "__enter__": lambda s: s,
        "__exit__": lambda s, *a: None,
        "add_submission": lambda s, fid, sub: True,
    })()
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage_stub)

    sub = StubSubmitter()

    def fake_submit_form(**kwargs):
        return Submission(num_submission=1, concurrent_thread=1,
                          time_used=1, success_rate=100.0, network_status="ok")

    sub.submit_form = fake_submit_form

    assert not hasattr(sub, "_finished_at")

    main_routes._run_submission(
        sub, "form_fa", num_submissions=1, concurrent_threads=1,
        min_delay=0, max_delay=0,
    )

    assert hasattr(sub, "_finished_at")
    assert sub._finished_at <= time.monotonic()

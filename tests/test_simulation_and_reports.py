"""Simulation before a run, and reports, exports and retries after it."""
import csv
import io
import threading
from datetime import datetime

import pytest

import app.services.submission_manager as submission_manager
from app.adapters.browser import form_submitter as form_submitter_module
from app.adapters.browser.form_submitter import FormSubmitter
from app.domain.response_plan import target_snapshot
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig
from app.services import set_run_store_provider
from app.services.run_store import RunStore

_REAL_THREAD = threading.Thread


def _form():
    return Form(
        id="form_rep",
        title="Report form",
        description="",
        url="https://docs.google.com/forms/d/e/REP/viewform",
        created_at=datetime(2026, 1, 1),
        last_used=None,
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
            Question(question_id="111", entry_id="entry.111", type="input_text", text="Name",
                     answer_config=AnswerConfig(fill_percentage=100, answers=["Ann", "=HYPERLINK(\"x\")"])),
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

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def get_form_by_id(self, form_id):
        return self.form if self.form and form_id == self.form.id else None

    def add_submission(self, form_id, submission):
        return True


class FakeDriver:
    def quit(self):
        pass


class InlineThread:
    """Runs the background job right away so tests can inspect its result."""

    def __init__(self, target, args):
        self.target = target
        self.args = args
        self.daemon = False

    def start(self):
        threading.Thread = _REAL_THREAD
        try:
            self.target(*self.args)
        finally:
            threading.Thread = InlineThread


@pytest.fixture
def store(tmp_path):
    run_store = RunStore(str(tmp_path / "db.json"), str(tmp_path / "runs"))
    set_run_store_provider(lambda: run_store)
    return run_store


@pytest.fixture
def env(client, storage_stub, store, monkeypatch):
    storage_stub(FakeStorage(_form()))
    monkeypatch.setattr(FormSubmitter, "initialize_driver", lambda self: FakeDriver())
    monkeypatch.setattr(threading, "Thread", InlineThread)
    submission_manager.active_submitters.clear()
    yield client
    submission_manager.active_submitters.clear()


def _simulate(client, **payload):
    body = {"form_id": "form_rep", "num_submissions": 10}
    body.update(payload)
    return client.post("/simulate", json=body)


# ------------------------------------------------------------- simulation


def test_simulate_never_creates_a_driver_or_a_run(env, store, monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("simulation must not start a browser")

    monkeypatch.setattr(FormSubmitter, "__init__", forbidden)
    monkeypatch.setattr(form_submitter_module.webdriver, "Chrome", forbidden)

    response = _simulate(env, seed=4)
    data = response.get_json()

    assert response.status_code == 200
    assert data["seed"] == 4
    assert data["total"] == 10
    color = next(q for q in data["questions"] if q["question_id"] == "222")
    assert {o["text"]: o["count"] for o in color["options"]} == {"Red": 7, "Blue": 3}
    assert {o["text"]: o["target"] for o in color["options"]} == {"Red": 70.0, "Blue": 30.0}
    assert len(data["sample_rows"]) == 10
    assert store.list_runs() == []
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("mode", ["prefill_link", "dom_fill"])
def test_simulation_matches_the_rows_a_run_stores(env, store, monkeypatch, mode):
    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", lambda self, driver, url: True)
    monkeypatch.setattr(FormSubmitter, "_submit_single_form", lambda self, driver: True)

    simulated = _simulate(env, seed=123, submission_mode=mode, num_submissions=12).get_json()
    started = env.post("/start_submission", json={
        "form_id": "form_rep", "num_submissions": 12, "concurrent_threads": 3,
        "min_delay": 0, "max_delay": 0, "seed": simulated["seed"], "submission_mode": mode,
    }).get_json()

    stored = store.load_rows(started["run_id"])
    assert [row["answers"] for row in stored] == [row["answers"] for row in simulated["sample_rows"]]
    assert all(row["status"] == "success" for row in stored)


def test_simulate_rejects_more_than_the_batch_limit(env):
    response = _simulate(env, num_submissions=501)

    assert response.status_code == 400


def test_simulate_unknown_form_and_mode(env):
    assert _simulate(env, form_id="missing").status_code == 404
    assert _simulate(env, submission_mode="bogus").status_code == 400
    assert env.post("/simulate", json={}).status_code == 400


# ----------------------------------------------------------------- report


def _seed_run(store, statuses, errors=None):
    form = _form()
    rows = [
        {"index": i, "answers": {"111": "Ann", "222": "Red" if i % 2 == 0 else "Blue"}, "skipped": []}
        for i in range(len(statuses))
    ]
    header = store.create_run(form_id=form.id, mode="prefill_link", seed=1, threads=2,
                              min_delay=0, max_delay=0, rows=rows, target_snapshot=target_snapshot(form))
    for i, status in enumerate(statuses):
        store.record_result(header["run_id"], i, "in_flight", started_at=f"2026-11-17T10:00:{i:02d}")
        if status != "in_flight":
            store.record_result(header["run_id"], i, status, error=(errors or {}).get(i),
                                started_at=f"2026-11-17T10:00:{i:02d}",
                                finished_at=f"2026-11-17T10:00:{i + 1:02d}")
    store.update_run(header["run_id"], status="completed")
    return header["run_id"]


def test_report_counts_outcomes_and_actual_against_target(env, store):
    run_id = _seed_run(store, ["success"] * 7 + ["failed"] * 3, errors={7: "submit_failed", 8: "submit_failed"})

    data = env.get(f"/runs/{run_id}").get_json()
    summary = data["summary"]

    assert data["run"]["run_id"] == run_id
    assert "target_snapshot" not in data["run"]
    assert (summary["success"], summary["failed"], summary["total"]) == (7, 3, 10)
    assert summary["success_rate"] == 70.0
    assert summary["duration_seconds"] == 10
    color = next(q for q in summary["questions"] if q["question_id"] == "222")
    # Only the 7 successful rows (indexes 0-6) count: 4 Red, 3 Blue.
    assert {o["text"]: o["count"] for o in color["options"]} == {"Red": 4, "Blue": 3}
    assert summary["failure_reasons"] == [
        {"reason": "submit_failed", "count": 2}, {"reason": "unknown_error", "count": 1},
    ]


def test_runs_list_and_rows_paging(env, store):
    run_id = _seed_run(store, ["success", "failed", "success"])

    runs = env.get("/runs?form_id=form_rep").get_json()["runs"]
    assert [run["run_id"] for run in runs] == [run_id]
    assert "target_snapshot" not in runs[0]

    page = env.get(f"/runs/{run_id}/rows?status=success&limit=1&offset=1").get_json()
    assert page["total"] == 2
    assert [row["index"] for row in page["rows"]] == [2]
    recent = env.get(f"/runs/{run_id}/rows?sort=recent").get_json()["rows"]
    assert [row["index"] for row in recent] == [2, 1, 0]

    assert env.get(f"/runs/{run_id}/rows?limit=101").status_code == 400
    assert env.get(f"/runs/{run_id}/rows?status=bogus").status_code == 400
    assert env.get("/runs").status_code == 400


def test_in_flight_rows_of_a_dead_run_read_as_unknown(env, store):
    run_id = _seed_run(store, ["success", "in_flight"])
    store.update_run(run_id, status="running")

    data = env.get(f"/runs/{run_id}").get_json()

    assert data["run"]["status"] == "interrupted"
    assert data["summary"]["unknown"] == 1


@pytest.mark.parametrize("bad_id", ["..%2Fdb", "NOT_HEX", "abc"])
def test_invalid_run_ids_are_rejected_before_any_lookup(env, bad_id):
    assert env.get(f"/runs/{bad_id}").status_code in (400, 404)
    assert env.get(f"/runs/{bad_id}/rows").status_code in (400, 404)


def test_invalid_and_unknown_run_ids(env):
    assert env.get("/runs/abc").status_code == 400
    assert env.get("/runs/" + "f" * 32).status_code == 404
    assert env.post("/runs/" + "f" * 32 + "/retry", json={}).status_code == 404
    assert env.get("/runs/" + "f" * 32 + "/view").status_code == 404


def test_export_csv_and_json_neutralize_formula_cells(env, store):
    form = _form()
    header = store.create_run(form_id=form.id, mode="prefill_link", seed=1, threads=1, min_delay=0,
                              max_delay=0, target_snapshot=target_snapshot(form),
                              rows=[{"index": 0, "answers": {"111": "=HYPERLINK(\"x\")", "222": "Red"}}])
    store.record_result(header["run_id"], 0, "failed", error="+boom")

    csv_response = env.get(f"/runs/{header['run_id']}/export?format=csv")
    rows = list(csv.reader(io.StringIO(csv_response.get_data(as_text=True))))

    assert csv_response.status_code == 200
    assert csv_response.mimetype == "text/csv"
    assert rows[0] == ["index", "status", "error", "started_at", "finished_at", "Name", "Color"]
    assert rows[1][2] == "'+boom"
    assert rows[1][5] == "'=HYPERLINK(\"x\")"
    assert rows[1][6] == "Red"

    json_response = env.get(f"/runs/{header['run_id']}/export?format=json")
    assert json_response.get_json()["rows"][0]["answers"]["111"] == "=HYPERLINK(\"x\")"
    assert env.get(f"/runs/{header['run_id']}/export?format=xml").status_code == 400


def test_history_export_neutralizes_formula_cells():
    from app.services.history_export import csv_safe

    assert csv_safe("=1+1") == "'=1+1"
    assert csv_safe("@SUM") == "'@SUM"
    assert csv_safe("-2") == "'-2"
    assert csv_safe("Completed") == "Completed"
    assert csv_safe(-2) == -2


# ------------------------------------------------------------------ retry


def _retry(client, run_id, **body):
    return client.post(f"/runs/{run_id}/retry", json=body)


def test_retry_sends_only_failed_rows_with_identical_answers(env, store, monkeypatch):
    sent = []
    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", lambda self, driver, url: sent.append(url) or True)
    run_id = _seed_run(store, ["success"] * 7 + ["failed"] * 3)

    data = _retry(env, run_id).get_json()

    assert data["retry_of"] == run_id
    assert data["total"] == 3
    retry_rows = store.load_rows(data["run_id"])
    original = {row["index"]: row["answers"] for row in store.load_rows(run_id)}
    assert [row["index"] for row in retry_rows] == [7, 8, 9]
    assert all(row["answers"] == original[row["index"]] for row in retry_rows)
    assert all(row["status"] == "success" for row in retry_rows)
    assert len(sent) == 3
    assert store.get_run(data["run_id"])["retry_of"] == run_id


def test_second_retry_never_resends_rows_a_retry_already_sent(env, store, monkeypatch):
    outcomes = iter([True, False, True])
    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", lambda self, driver, url: next(outcomes))
    run_id = _seed_run(store, ["success"] * 7 + ["failed"] * 3)
    first = _retry(env, run_id).get_json()
    assert sorted(row["status"] for row in store.load_rows(first["run_id"])) == ["failed", "success", "success"]

    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", lambda self, driver, url: True)
    second = _retry(env, first["run_id"]).get_json()

    assert second["retry_of"] == run_id
    assert second["total"] == 1
    assert _retry(env, run_id).status_code == 400


def test_unknown_rows_are_resent_only_on_request(env, store, monkeypatch):
    monkeypatch.setattr(FormSubmitter, "_submit_prefilled_url", lambda self, driver, url: True)
    run_id = _seed_run(store, ["success", "unknown"])

    assert _retry(env, run_id).status_code == 400
    data = _retry(env, run_id, include_unknown=True).get_json()
    assert data["total"] == 1


def test_retry_is_refused_while_the_form_is_running(env, store):
    run_id = _seed_run(store, ["failed"])

    class Running:
        run_id = None

        def get_status(self):
            return {"running": True}

    submission_manager.active_submitters["form_rep"] = Running()

    assert _retry(env, run_id).status_code == 409


def test_report_page_renders(env, store):
    run_id = _seed_run(store, ["success"])

    response = env.get(f"/runs/{run_id}/view")

    assert response.status_code == 200
    assert f'data-run-id="{run_id}"' in response.get_data(as_text=True)

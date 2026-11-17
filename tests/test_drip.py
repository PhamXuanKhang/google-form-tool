"""Scheduled runs with a fake clock and a fake sender; nothing sleeps for real."""
import random
from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

import app.services.submission_manager as submission_manager
from app.domain.drip_schedule import build_schedule, due_rows, respread
from app.services.drip_runner import DripRunner, recover_interrupted_runs, schedule_times
from app.services.run_store import RunStore

START = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)
SIX_HOURS = 6 * 3600


class FakeClock:
    def __init__(self, now=START):
        self.now = now

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += timedelta(seconds=seconds)


class FakeSender:
    """Records every send; marks rows success through the runner's callback."""

    def __init__(self, clock, on_send=None):
        self.clock = clock
        self.sent = []
        self.batches = []
        self.on_send = on_send

    def __call__(self, rows, on_row_result):
        self.batches.append([row["index"] for row in rows])
        for row in rows:
            stamp = self.clock().isoformat()
            self.sent.append((row["index"], self.clock()))
            on_row_result(row["index"], "success", None, stamp, stamp)
            if self.on_send:
                self.on_send(len(self.sent))


@pytest.fixture
def store(tmp_path):
    return RunStore(str(tmp_path / "db.json"), str(tmp_path / "runs"))


def _scheduled_run(store, count=200, window=SIX_HOURS, threads=2, min_delay=30):
    times = build_schedule(count, START, window, random.Random(7))
    rows = [{"index": i, "answers": {"q": str(i)}, "due_at": when.isoformat()} for i, when in enumerate(times)]
    return store.create_run(
        form_id="f", mode="prefill_link", seed=7, threads=threads, min_delay=min_delay, max_delay=60, rows=rows,
        extra={"schedule": {"window_seconds": window, "window_end": (START + timedelta(seconds=window)).isoformat()}},
    )


def _runner(store, header, clock, sender):
    return DripRunner(store=store, header=header, send_batch=sender, clock=clock, sleep=clock.sleep, tick_seconds=60)


# --------------------------------------------------------------- schedule


@pytest.mark.domain
def test_schedule_spreads_every_send_inside_the_window():
    times = build_schedule(200, START, SIX_HOURS, random.Random(1))

    assert all(START <= when <= START + timedelta(seconds=SIX_HOURS) for when in times)
    assert times == sorted(times)
    slot = SIX_HOURS / 200
    per_ten_minutes = Counter(int((when - START).total_seconds() // 600) for when in times)
    assert max(per_ten_minutes.values()) <= 600 / slot + 1
    assert len(set(times)) == 200


@pytest.mark.domain
def test_due_rows_respects_the_cap_and_order():
    rows = [{"index": i, "status": "planned", "due_at": (START + timedelta(seconds=i)).isoformat()} for i in range(5)]
    rows[1]["status"] = "success"

    due = due_rows(rows, START + timedelta(seconds=10), 2)

    assert [row["index"] for row in due] == [0, 2]


@pytest.mark.domain
def test_respread_after_the_window_keeps_the_minimum_gap():
    now = START + timedelta(hours=10)
    times = respread(5, now, START + timedelta(hours=6), 45, random.Random(1))

    gaps = [(b - a).total_seconds() for a, b in zip([now] + times, times)]
    assert all(gap >= 45 for gap in gaps)


# ----------------------------------------------------------------- runner


def test_all_200_responses_are_sent_once_within_the_window(store):
    header = _scheduled_run(store)
    clock = FakeClock()
    sender = FakeSender(clock)

    final = _runner(store, header, clock, sender).run()

    assert final == "completed"
    assert sorted(index for index, _ in sender.sent) == list(range(200))
    assert all(len(batch) <= 2 for batch in sender.batches)
    assert all(when <= START + timedelta(seconds=SIX_HOURS, minutes=1) for _, when in sender.sent)
    assert store.get_run(header["run_id"])["status"] == "completed"


def test_pause_stops_new_sends_and_resume_finishes_the_rest(store):
    header = _scheduled_run(store)
    clock = FakeClock()
    runner_holder = {}
    sender = FakeSender(clock, on_send=lambda n: n == 80 and runner_holder["runner"].pause())
    runner_holder["runner"] = _runner(store, header, clock, sender)

    assert runner_holder["runner"].run() == "paused"
    sent_when_paused = len(sender.sent)
    clock.sleep(3600)
    assert len(sender.sent) == sent_when_paused
    assert store.get_run(header["run_id"])["status"] == "paused"

    rows = store.load_rows(header["run_id"])
    store.record_schedule(header["run_id"], schedule_times(header, rows, clock(), random.Random(2)))
    sender.on_send = None
    assert _runner(store, store.get_run(header["run_id"]), clock, sender).run() == "completed"

    assert sorted(index for index, _ in sender.sent) == list(range(200))


def test_restart_marks_the_run_interrupted_and_never_resends(store):
    header = _scheduled_run(store)
    clock = FakeClock()
    runner_holder = {}
    sender = FakeSender(clock, on_send=lambda n: n == 100 and runner_holder["runner"].pause())
    runner_holder["runner"] = _runner(store, header, clock, sender)
    runner_holder["runner"].run()
    # Simulate a hard kill while row 150 was being sent.
    store.record_result(header["run_id"], 150, "in_flight", started_at=clock().isoformat())
    store.update_run(header["run_id"], status="running")

    second_engine_store = RunStore(store.db_path, str(store.runs_dir))
    recovered = recover_interrupted_runs(second_engine_store)

    assert recovered == [header["run_id"]]
    assert second_engine_store.get_run(header["run_id"])["status"] == "interrupted"
    rows = {row["index"]: row for row in second_engine_store.load_rows(header["run_id"])}
    assert rows[150]["status"] == "unknown"
    sent_before = len(sender.sent)
    clock.sleep(SIX_HOURS)
    assert len(sender.sent) == sent_before

    clock.sleep(3600)  # resume after the window ended
    new_times = schedule_times(header, list(rows.values()), clock(), random.Random(3))
    second_engine_store.record_schedule(header["run_id"], new_times)
    sender.on_send = None
    _runner(second_engine_store, second_engine_store.get_run(header["run_id"]), clock, sender).run()

    counts = Counter(index for index, _ in sender.sent)
    assert all(count == 1 for count in counts.values())
    assert 150 not in counts
    assert set(counts) == set(range(200)) - {150}
    assert len(set(new_times.values())) == len(new_times)
    resumed = sorted(datetime.fromisoformat(when) for when in new_times.values())
    assert all((b - a).total_seconds() >= 30 for a, b in zip(resumed, resumed[1:]))


def test_a_long_sleep_does_not_send_a_burst(store):
    header = _scheduled_run(store, count=50, window=3600)
    clock = FakeClock(START + timedelta(hours=2))  # everything is already overdue
    sender = FakeSender(clock)

    _runner(store, header, clock, sender).run()

    assert all(len(batch) <= 2 for batch in sender.batches)
    first_ticks = [when for _, when in sender.sent[:10]]
    assert first_ticks[-1] > first_ticks[0]
    assert sorted(index for index, _ in sender.sent) == list(range(50))


def test_stop_leaves_waiting_rows_planned(store):
    header = _scheduled_run(store)
    clock = FakeClock()
    runner_holder = {}
    sender = FakeSender(clock, on_send=lambda n: n == 10 and runner_holder["runner"].stop())
    runner_holder["runner"] = _runner(store, header, clock, sender)

    assert runner_holder["runner"].run() == "stopped"

    statuses = Counter(row["status"] for row in store.load_rows(header["run_id"]))
    assert statuses["success"] == 10
    assert statuses["planned"] == 190
    assert store.get_run(header["run_id"])["status"] == "stopped"


def test_a_batch_that_sends_nothing_ends_the_run_instead_of_retrying(store):
    header = _scheduled_run(store, count=5)
    clock = FakeClock(START + timedelta(seconds=SIX_HOURS))
    calls = []

    final = _runner(store, header, clock, lambda rows, cb: calls.append(len(rows))).run()

    assert final == "interrupted"
    assert len(calls) == 1
    assert all(row["status"] == "planned" for row in store.load_rows(header["run_id"]))
    assert store.get_run(header["run_id"])["status"] == "interrupted"


def test_recovery_leaves_live_and_finished_runs_alone(store):
    live = _scheduled_run(store, count=2)
    done = _scheduled_run(store, count=2)
    store.update_run(live["run_id"], status="running")
    store.update_run(done["run_id"], status="completed")

    assert recover_interrupted_runs(store, {live["run_id"]}) == []
    assert store.get_run(live["run_id"])["status"] == "running"


# ----------------------------------------------------------------- routes


from datetime import datetime as _dt  # noqa: E402

from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig  # noqa: E402
from app.services import set_run_store_provider  # noqa: E402


class MemoryStorage:
    def __init__(self):
        self.form = Form(
            id="f_drip", title="Drip", description="", url="https://docs.google.com/forms/d/e/DRIP/viewform",
            created_at=_dt(2026, 1, 1), last_used=None, submissions=None,
            response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
                Question(question_id="1", entry_id="entry.1", type="multiple_choice", text="Pick",
                         answer_config=AnswerConfig(fill_percentage=100, options=[AnswerOption(text="A", percentage=100.0)])),
            ])]),
        )
        self.saved = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def get_form_by_id(self, form_id):
        return self.form if form_id == self.form.id else None

    def add_submission(self, form_id, submission):
        self.saved.append(submission)
        return True


@pytest.fixture
def route_env(client, storage_stub, store, monkeypatch):
    storage_stub(MemoryStorage())
    set_run_store_provider(lambda: store)
    started = []
    monkeypatch.setattr(submission_manager, "start_drip_thread", lambda form, runner: started.append(runner))
    monkeypatch.setattr(submission_manager, "send_batch_factory", lambda form, header: lambda rows, cb: None)
    submission_manager.active_submitters.clear()
    yield client, started
    submission_manager.active_submitters.clear()


def _start(client, **overrides):
    body = {"form_id": "f_drip", "num_submissions": 6, "concurrent_threads": 1, "min_delay": 0, "max_delay": 0,
            "schedule": {"window_minutes": 60}}
    body.update(overrides)
    return client.post("/start_submission", json=body)


@pytest.mark.parametrize("schedule", [{"window_minutes": 0}, {"window_minutes": 10081}, {"window_minutes": "60"},
                                      {"window_minutes": True}, "60", {}])
def test_invalid_windows_are_rejected(route_env, schedule):
    client, started = route_env

    assert _start(client, schedule=schedule).status_code == 400
    assert started == []


def test_scheduled_start_registers_a_runner_and_stores_send_times(route_env, store):
    client, started = route_env

    data = _start(client).get_json()

    header = store.get_run(data["run_id"])
    rows = store.load_rows(data["run_id"])
    assert data["schedule"]["window_seconds"] == 3600
    assert header["schedule"] == data["schedule"]
    assert all(row["due_at"] for row in rows)
    assert len({row["due_at"] for row in rows}) == 6
    assert started and started[0].run_id == data["run_id"]
    status = client.get("/submission_status?form_id=f_drip").get_json()
    assert status["scheduled"] is True and status["next_due_at"] and status["run_id"] == data["run_id"]
    assert _start(client).status_code == 409


def test_scheduled_start_sends_up_to_the_chosen_threads_per_tick(route_env):
    client, started = route_env

    _start(client, concurrent_threads=4)

    assert started[0].max_per_tick == 4


def test_pausing_a_finished_scheduled_run_is_refused(route_env):
    client, started = route_env
    run_id = _start(client).get_json()["run_id"]
    started[0].final_status = "completed"

    assert client.post(f"/runs/{run_id}/pause").status_code == 409
    assert not started[0]._pause.is_set()


def test_pause_and_resume_routes(route_env, store):
    client, started = route_env
    run_id = _start(client).get_json()["run_id"]
    runner = started[0]

    assert client.post(f"/runs/{run_id}/pause").get_json()["status"] == "paused"
    assert runner._pause.is_set()
    # The runner thread would now end with status paused.
    store.update_run(run_id, status="paused")
    runner.final_status = "paused"
    runner._run_live = False

    assert client.get(f"/runs/{run_id}").get_json()["run"]["status"] == "paused"
    resumed = client.post(f"/runs/{run_id}/resume").get_json()
    assert resumed["status"] == "running" and resumed["pending"] == 6
    assert client.post(f"/runs/{run_id}/resume").status_code == 409
    assert client.post(f"/runs/{run_id}/pause").status_code == 200


def test_a_failed_resume_does_not_leave_the_form_busy(route_env, store, monkeypatch):
    client, started = route_env
    run_id = _start(client).get_json()["run_id"]
    store.update_run(run_id, status="interrupted")
    started[0].abandon()

    def broken_update(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(store, "update_run", broken_update)

    assert client.post(f"/runs/{run_id}/resume").status_code == 500
    assert not submission_manager.form_has_running_submission("f_drip")


def test_resume_needs_a_scheduled_paused_or_interrupted_run(route_env, store):
    client, _ = route_env
    normal = store.create_run(form_id="f_drip", mode="prefill_link", seed=1, threads=1, min_delay=0, max_delay=0,
                              rows=[{"index": 0, "answers": {}}])
    store.update_run(normal["run_id"], status="interrupted")

    assert client.post(f"/runs/{normal['run_id']}/resume").status_code == 400
    assert client.post(f"/runs/{normal['run_id']}/pause").status_code == 409
    assert client.post("/runs/" + "f" * 32 + "/pause").status_code == 404
    assert client.get("/runs?status=interrupted").get_json()["runs"][0]["run_id"] == normal["run_id"]

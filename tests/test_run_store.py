import threading

import pytest
from tinydb import TinyDB

from app.services.run_store import RunStore, is_valid_run_id


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "db.json"
    with TinyDB(str(db_path)) as db:
        db.insert({"id": "form_1", "title": "Saved form"})
    return RunStore(str(db_path), str(tmp_path / "runs"))


def _rows(count):
    return [{"index": i, "answers": {"q": f"a{i}"}, "skipped": []} for i in range(count)]


def _create(store, count=3, **extra):
    return store.create_run(
        form_id="form_1", mode="prefill_link", seed=42, threads=2,
        min_delay=0, max_delay=1, rows=_rows(count), **extra,
    )


def test_create_run_writes_header_and_planned_rows(store):
    header = _create(store, 3, target_snapshot={"q": {"a0": 100}})

    assert is_valid_run_id(header["run_id"])
    saved = store.get_run(header["run_id"])
    assert saved["status"] == "pending"
    assert saved["total"] == 3
    assert saved["seed"] == 42
    assert saved["target_snapshot"] == {"q": {"a0": 100}}
    rows = store.load_rows(header["run_id"])
    assert [row["index"] for row in rows] == [0, 1, 2]
    assert all(row["status"] == "planned" for row in rows)
    assert rows[1]["answers"] == {"q": "a1"}


def test_run_header_does_not_disturb_saved_forms(store):
    _create(store)

    with TinyDB(store.db_path) as db:
        assert db.all() == [{"id": "form_1", "title": "Saved form"}]


def test_latest_result_line_wins(store):
    run_id = _create(store)["run_id"]

    store.record_result(run_id, 1, "in_flight", started_at="t0")
    store.record_result(run_id, 1, "failed", error="timeout", started_at="t0", finished_at="t1")
    store.record_result(run_id, 1, "in_flight", started_at="t2")
    store.record_result(run_id, 1, "success", started_at="t2", finished_at="t3")

    row = store.load_rows(run_id)[1]
    assert row["status"] == "success"
    assert row["error"] is None
    assert row["started_at"] == "t2"
    assert row["finished_at"] == "t3"
    assert row["attempts"] == 2


def test_five_hundred_rows_from_ten_threads_leave_db_json_untouched(store):
    run_id = _create(store, 500)["run_id"]
    before = open(store.db_path, "rb").read()

    def worker(start):
        for index in range(start, 500, 10):
            store.record_result(run_id, index, "success", started_at="s", finished_at="f")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    rows = store.load_rows(run_id)
    assert len(rows) == 500
    assert len({row["index"] for row in rows}) == 500
    assert all(row["status"] == "success" and row["finished_at"] == "f" for row in rows)
    assert open(store.db_path, "rb").read() == before


def test_truncated_last_line_is_ignored_and_later_writes_still_load(store):
    run_id = _create(store, 3)["run_id"]
    store.record_result(run_id, 0, "success")
    path = store.runs_dir / f"{run_id}.jsonl"
    with path.open("ab") as handle:
        handle.write(b'{"kind": "result", "index": 1, "sta')

    rows = store.load_rows(run_id)
    assert [row["status"] for row in rows] == ["success", "planned", "planned"]

    store.record_result(run_id, 2, "failed", error="boom")
    rows = store.load_rows(run_id)
    assert [row["status"] for row in rows] == ["success", "planned", "failed"]


def test_update_run_changes_status_and_rejects_unknown_values(store):
    run_id = _create(store)["run_id"]

    assert store.update_run(run_id, status="running") is True
    assert store.get_run(run_id)["status"] == "running"
    with pytest.raises(ValueError):
        store.update_run(run_id, status="exploded")
    assert store.update_run("f" * 32, status="running") is False


def test_list_runs_filters_by_form_newest_first(store):
    first = _create(store)
    second = _create(store)
    store.create_run(form_id="other", mode="dom_fill", seed=1, threads=1,
                     min_delay=0, max_delay=0, rows=_rows(1))

    runs = store.list_runs("form_1")

    assert {run["run_id"] for run in runs} == {first["run_id"], second["run_id"]}
    assert runs[0]["created_at"] >= runs[1]["created_at"]


@pytest.mark.parametrize("bad_id", ["../db", "ABC", "", None, "x" * 32])
def test_invalid_run_ids_never_touch_the_filesystem(store, bad_id):
    assert store.get_run(bad_id) is None
    with pytest.raises(ValueError):
        store.load_rows(bad_id)
    with pytest.raises(ValueError):
        store.record_result(bad_id, 0, "success")

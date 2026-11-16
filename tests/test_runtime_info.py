import json
import os

from app.runtime_info import read_runtime_info, runtime_file_path, write_runtime_info


def test_write_then_read_runtime_info(tmp_path):
    path = write_runtime_info(5123, "2.0.0", app_data_path=str(tmp_path))

    assert path == runtime_file_path(str(tmp_path))
    info = read_runtime_info(str(tmp_path))
    assert info["port"] == 5123
    assert info["pid"] == os.getpid()
    assert info["version"] == "2.0.0"
    assert info["started_at"]
    assert [p.name for p in tmp_path.iterdir()] == ["runtime.json"]


def test_rewrite_replaces_previous_info(tmp_path):
    write_runtime_info(5000, app_data_path=str(tmp_path))
    write_runtime_info(5123, app_data_path=str(tmp_path))

    assert read_runtime_info(str(tmp_path))["port"] == 5123


def test_missing_or_broken_file_reads_as_none(tmp_path):
    assert read_runtime_info(str(tmp_path)) is None

    runtime_file_path(str(tmp_path)).write_text("{not json", encoding="utf-8")
    assert read_runtime_info(str(tmp_path)) is None

    runtime_file_path(str(tmp_path)).write_text(json.dumps({"port": "x"}), encoding="utf-8")
    assert read_runtime_info(str(tmp_path)) is None

"""MCP server: each tool proxies one backend route; errors become tool errors."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import anyio
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

import app.mcp_server as mcp_server
import app.runtime_info as runtime_info
from app import create_app
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig
from app.services import set_run_store_provider
from app.services.run_store import RunStore

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TOOLS = {
    "app_status", "list_forms", "extract_form", "get_form", "set_answer_config", "simulate",
    "start_run", "run_status", "stop_run", "list_runs", "get_report", "retry_failed",
    "apply_preset", "export_config", "import_config", "list_templates",
}

FORM_JSON = {
    "id": "f1", "title": "T", "url": "https://docs.google.com/forms/d/e/X/viewform",
    "response_config": {"pages": [{"page_id": "p1", "questions": [
        {"question_id": "q1", "type": "multiple_choice", "text": "Pick",
         "answer_config": {"fill_percentage": 100, "answers": None,
                           "options": [{"text": "A", "percentage": 60, "next_page_id": None},
                                       {"text": "B", "percentage": 40, "next_page_id": "__submit__"}]}},
    ]}]},
}


class FakeBackend:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))
        for (m, prefix), reply in self.responses.items():
            if m == method and path.startswith(prefix):
                return reply
        return 200, {"success": True}


def _call(server, name, arguments=None):
    async def go():
        async with create_connected_server_and_client_session(server) as session:
            result = await session.call_tool(name, arguments or {})
            return result
    return anyio.run(go)


def _payload(result):
    assert not result.isError, result.content
    return json.loads(result.content[0].text)


def _error_text(result):
    assert result.isError
    return result.content[0].text


def test_all_tools_are_listed_with_strict_inputs():
    async def go():
        async with create_connected_server_and_client_session(mcp_server.create_server(FakeBackend())) as session:
            return (await session.list_tools()).tools
    tools = {tool.name: tool for tool in anyio.run(go)}

    assert set(tools) == EXPECTED_TOOLS
    assert all(tool.description for tool in tools.values())
    assert tools["stop_run"].inputSchema["required"] == ["form_id"]
    assert set(tools["start_run"].inputSchema["required"]) == {"form_id", "num_submissions"}
    assert tools["start_run"].inputSchema["properties"]["num_submissions"]["maximum"] == 500
    assert tools["start_run"].inputSchema["properties"]["concurrent_threads"]["maximum"] == 10
    assert tools["start_run"].inputSchema["properties"]["concurrent_threads"]["default"] == 1


def test_stop_run_without_form_id_is_rejected_before_the_backend():
    backend = FakeBackend()

    result = _call(mcp_server.create_server(backend), "stop_run", {})

    assert result.isError
    assert backend.calls == []


@pytest.mark.parametrize("name,arguments,method,path,body", [
    ("list_forms", {}, "GET", "/forms", None),
    ("get_form", {"form_id": "f 1"}, "GET", "/forms/f%201", None),
    ("simulate", {"form_id": "f1", "num_submissions": 5, "seed": 3}, "POST", "/simulate",
     {"form_id": "f1", "num_submissions": 5, "submission_mode": "prefill_link", "seed": 3}),
    ("start_run", {"form_id": "f1", "num_submissions": 5}, "POST", "/start_submission",
     {"form_id": "f1", "num_submissions": 5, "concurrent_threads": 1, "min_delay": 1, "max_delay": 5,
      "submission_mode": "prefill_link"}),
    ("run_status", {"form_id": "f1"}, "GET", "/submission_status?form_id=f1", None),
    ("stop_run", {"form_id": "f1"}, "POST", "/stop_submission", {"form_id": "f1"}),
    ("list_runs", {"form_id": "f1"}, "GET", "/runs?form_id=f1", None),
    ("get_report", {"run_id": "abc"}, "GET", "/runs/abc", None),
    ("retry_failed", {"run_id": "abc"}, "POST", "/runs/abc/retry", {"include_unknown": False}),
])
def test_each_tool_calls_its_route(name, arguments, method, path, body):
    backend = FakeBackend({("GET", "/forms/"): (200, {"form": FORM_JSON})})

    _payload(_call(mcp_server.create_server(backend), name, arguments))

    assert backend.calls[0] == (method, path, body)


def test_extract_then_set_answers_return_the_compact_form():
    backend = FakeBackend({
        ("POST", "/form_filling/extract"): (200, {"success": True, "form_id": "f1"}),
        ("GET", "/forms/f1"): (200, {"form": FORM_JSON}),
    })
    server = mcp_server.create_server(backend)

    form = _payload(_call(server, "extract_form", {"form_url": FORM_JSON["url"]}))
    edits = {"q1": {"options": [{"text": "A", "percentage": 50}, {"text": "B", "percentage": 50}]}}
    _payload(_call(server, "set_answer_config", {"form_id": "f1", "edits": edits}))

    assert form["form_id"] == "f1"
    assert form["questions"][0]["options"][1] == {"text": "B", "percentage": 40, "submit_after": True}
    assert ("POST", "/save_edit", {"form_id": "f1", "edits": edits}) in backend.calls


def test_apply_preset_sets_fitting_questions_through_save_edit():
    form = json.loads(json.dumps(FORM_JSON))
    form["response_config"]["pages"][0]["questions"].append(
        {"question_id": "q2", "type": "linear_scale", "text": "Rate",
         "answer_config": {"fill_percentage": 100, "answers": None,
                           "options": [{"text": str(n), "percentage": 20, "next_page_id": None} for n in range(1, 6)]}})
    backend = FakeBackend({("GET", "/forms/f1"): (200, {"form": form})})
    server = mcp_server.create_server(backend)

    bell = _payload(_call(server, "apply_preset", {"form_id": "f1", "preset": "bell"}))
    uniform = _payload(_call(server, "apply_preset", {"form_id": "f1", "preset": "uniform", "question_id": "q1"}))
    none_fit = _call(server, "apply_preset", {"form_id": "f1", "preset": "bell", "question_id": "q1"})

    assert bell == {"applied_to": ["q2"], "skipped": ["q1"]}
    saved = [call for call in backend.calls if call[1] == "/save_edit"]
    assert sum(option["percentage"] for option in saved[0][2]["edits"]["q2"]["options"]) == pytest.approx(100)
    assert saved[1][2]["edits"]["q1"]["options"] == [{"text": "A", "percentage": 50.0}, {"text": "B", "percentage": 50.0}]
    assert uniform["applied_to"] == ["q1"]
    assert none_fit.isError


def test_import_config_needs_exactly_one_source_and_previews_by_default():
    backend = FakeBackend()
    server = mcp_server.create_server(backend)

    assert _call(server, "import_config", {"form_id": "f1"}).isError
    _payload(_call(server, "import_config", {"form_id": "f1", "template_id": "t1"}))

    assert backend.calls[-1] == ("POST", "/forms/f1/config/import", {"apply": False, "template_id": "t1"})


@pytest.mark.parametrize("status", [400, 404, 409])
def test_backend_errors_become_tool_errors(status):
    backend = FakeBackend({("POST", "/start_submission"): (status, {"error": f"backend says {status}"})})

    result = _call(mcp_server.create_server(backend), "start_run", {"form_id": "f1", "num_submissions": 2})

    assert _error_text(result).endswith(f"backend says {status}")


def test_app_status_reports_readiness_without_paths():
    backend = FakeBackend({
        ("GET", "/healthz"): (200, {"status": "ok"}),
        ("GET", "/diagnostics/runtime"): (200, {"mode": "frozen", "version": "2.0.0", "chrome_path": "C:/x",
                                                "chromedriver_path": None, "db_path": "C:/secret"}),
    })

    status = _payload(_call(mcp_server.create_server(backend), "app_status"))

    assert status == {"running": True, "mode": "frozen", "chrome_found": True,
                      "chromedriver_found": False, "version": "2.0.0"}


def test_tools_say_open_the_app_when_it_is_not_running(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_info.Config, "APP_DATA_PATH", str(tmp_path))

    result = _call(mcp_server.create_server(), "list_forms")
    assert _error_text(result).endswith(mcp_server.NOT_RUNNING)

    # A leftover runtime file pointing at a port nobody answers on.
    (tmp_path / "runtime.json").write_text(json.dumps({"port": 9, "pid": 1}), encoding="utf-8")
    result = _call(mcp_server.create_server(), "list_forms")
    assert _error_text(result).endswith(mcp_server.NOT_RUNNING)


def test_tools_work_against_the_real_routes(storage_stub, tmp_path):
    form = Form(
        id="f_real", title="Real", description="", url="https://docs.google.com/forms/d/e/REAL/viewform",
        created_at=datetime(2026, 1, 1), last_used=None, submissions=None,
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
            Question(question_id="q1", entry_id="entry.1", type="multiple_choice", text="Pick",
                     answer_config=AnswerConfig(fill_percentage=100, options=[
                         AnswerOption(text="A", percentage=100.0), AnswerOption(text="B", percentage=0.0)])),
        ])]),
    )

    class Storage:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

        def get_all_forms_summary(self):
            return [{"id": form.id, "title": form.title, "url": str(form.url), "created_at": "2026-01-01T00:00:00",
                     "last_used": None, "total_fill": 0}]

        def get_form_by_id(self, form_id):
            return form if form_id == form.id else None

    storage_stub(Storage())
    set_run_store_provider(lambda: RunStore(str(tmp_path / "db.json"), str(tmp_path / "runs")))

    flask_app = create_app(testing=True)

    def via_flask(method, path, body):
        # The tools run in a worker thread, so each call gets its own client.
        response = flask_app.test_client().open(path, method=method, json=body)
        return response.status_code, response.get_json()

    server = mcp_server.create_server(via_flask)
    forms = _payload(_call(server, "list_forms"))
    simulated = _payload(_call(server, "simulate", {"form_id": "f_real", "num_submissions": 4, "seed": 1}))
    missing = _call(server, "get_report", {"run_id": "f" * 32})
    too_many = _call(server, "simulate", {"form_id": "f_real", "num_submissions": 501})

    assert forms["forms"][0]["question_count"] == 1
    assert simulated["total"] == 4
    assert simulated["questions"][0]["options"][0]["count"] == 4
    assert _error_text(missing).endswith("Run not found")
    assert too_many.isError


def test_settings_page_shows_mcp_config_and_skill(client, monkeypatch):
    import app.routes.pages as pages_routes

    monkeypatch.setattr(pages_routes, "_runtime_diagnostics", lambda: {
        "app_data_path": "C:/Data", "db_path": "C:/Data/db.json", "log_path": "C:/Data/logs",
        "chrome_path": None, "chromedriver_path": None, "bundled_drivers_dir": "", "cache_drivers_dir": "",
        "mode": "frozen", "version": "2.0.0",
        "mcp": {"command": "C:/Program Files/GFT/GoogleFormToolMcp.exe", "args": [], "available": True},
    })

    text = client.get("/settings/diagnostics?lang=en").get_data(as_text=True)

    assert "Agent connection (MCP)" in text
    assert "&#34;google-form-automation&#34;" in text or '"google-form-automation"' in text
    assert "claude mcp add google-form-automation -- &#34;C:/Program Files/GFT/GoogleFormToolMcp.exe&#34;" in text
    assert "name: google-form-automation" in text


def test_skill_file_has_frontmatter_and_the_safe_workflow():
    text = (REPO_ROOT / "skills" / "google-form-automation" / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---")[1]

    assert "name: google-form-automation" in frontmatter
    assert "description:" in frontmatter
    for tool in EXPECTED_TOOLS:
        assert f"`{tool}`" in text, tool
    assert "500" in text and "10" in text


def test_dev_runtime_reports_how_to_launch_the_mcp_server(client):
    mcp = client.get("/diagnostics/runtime").get_json()["mcp"]

    assert mcp["command"] == "uv"
    assert mcp["args"][-2:] == ["-m", "app.mcp_server"]


def test_importing_the_server_keeps_flask_selenium_and_storage_out():
    code = (
        "import json, sys, app.mcp_server; "
        "print(json.dumps([m for m in ('flask', 'selenium', 'tinydb', 'app.services.storage_service') "
        "if m in sys.modules]))"
    )
    output = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, check=True)

    assert json.loads(output.stdout.strip().splitlines()[-1]) == []

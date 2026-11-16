"""MCP server for Google Form Automation Tool.

A stdio MCP server that lets an agent extract, configure, simulate, run, stop
and review form batches. It is only a proxy: every tool calls the running
desktop backend over HTTP on 127.0.0.1, found through ``runtime.json``. It
never opens the database or starts the backend, so the same validation,
limits (500 responses, 10 threads) and conflict checks apply as in the app.

Run from source with ``python -m app.mcp_server``. Nothing but the MCP
protocol may be written to stdout; logs go to stderr.
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from app.domain.distribution_presets import ORDERED_TYPES, presets_for
from app.domain.distribution_presets import apply_preset as apply_distribution_preset
from app.runtime_info import read_runtime_info

logger = logging.getLogger("google_form_tool.mcp")

NOT_RUNNING = "Google Form Automation Tool is not running. Open the app, then try again."
HEALTH_TIMEOUT = 2
REQUEST_TIMEOUT = 300  # extraction can take a while
MAX_LIST_ITEMS = 50
MAX_SAMPLE_ROWS = 10
MAX_TEXT_ANSWERS = 20

# (method, path, json body or None) -> (HTTP status, parsed JSON body)
RequestFn = Callable[[str, str, Optional[Dict[str, Any]]], Tuple[int, Dict[str, Any]]]

SubmissionMode = Literal["prefill_link", "dom_fill"]


class BackendUnavailable(Exception):
    pass


# ----------------------------------------------------------------- backend


_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http(method: str, url: str, body: Optional[Dict[str, Any]], timeout: float) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with _opener.open(request, timeout=timeout) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    try:
        parsed = json.loads(raw.decode("utf-8") or "{}")
    except ValueError:
        parsed = {}
    return status, parsed if isinstance(parsed, dict) else {"data": parsed}


def _backend_base_url() -> str:
    info = read_runtime_info()
    if not info:
        raise BackendUnavailable(NOT_RUNNING)
    base = f"http://127.0.0.1:{info['port']}"
    try:
        status, body = _http("GET", f"{base}/healthz", None, HEALTH_TIMEOUT)
    except (OSError, urllib.error.URLError):
        raise BackendUnavailable(NOT_RUNNING)
    if status != 200 or body.get("status") != "ok":
        raise BackendUnavailable(NOT_RUNNING)
    return base


def http_request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
    """Call the running backend; raises BackendUnavailable when it is not running."""
    base = _backend_base_url()
    try:
        return _http(method, f"{base}{path}", body, REQUEST_TIMEOUT)
    except (OSError, urllib.error.URLError):
        raise BackendUnavailable(NOT_RUNNING)


# ------------------------------------------------------------------ shaping


def _compact_form(form: Dict[str, Any]) -> Dict[str, Any]:
    questions = []
    for page_number, page in enumerate((form.get("response_config") or {}).get("pages") or [], start=1):
        for question in page.get("questions") or []:
            config = question.get("answer_config") or {}
            item = {
                "question_id": question.get("question_id"),
                "page": page_number,
                "type": question.get("type"),
                "text": question.get("text"),
                "fill_percentage": config.get("fill_percentage"),
            }
            if config.get("options"):
                item["options"] = [
                    {
                        "text": option.get("text"),
                        "percentage": option.get("percentage"),
                        "submit_after": option.get("next_page_id") == "__submit__",
                    }
                    for option in config["options"]
                ]
            if config.get("answers"):
                item["answers"] = config["answers"][:MAX_TEXT_ANSWERS]
            questions.append(item)
    return {
        "form_id": form.get("id"),
        "title": form.get("title"),
        "url": form.get("url"),
        "question_count": len(questions),
        "questions": questions,
    }


# ------------------------------------------------------------------- server


def create_server(request: Optional[RequestFn] = None) -> FastMCP:
    """Build the MCP server. ``request`` replaces the HTTP client in tests."""
    call_backend = request or http_request
    server = FastMCP(
        "google-form-automation",
        instructions=(
            "Drive Google Form Automation Tool, a desktop app that fills Google Forms in bulk "
            "for testing. The app must be open. Only use it on forms the user owns or may test. "
            "Simulate before starting a run, and start a run only after the user agrees."
        ),
    )

    async def call(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            status, data = await anyio.to_thread.run_sync(call_backend, method, path, body)
        except BackendUnavailable as error:
            raise ToolError(str(error))
        if status >= 400:
            raise ToolError(data.get("error") or f"The app returned HTTP {status}.")
        return data

    def quoted(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    @server.tool()
    async def app_status() -> Dict[str, Any]:
        """Check that the app is running and whether Chrome and ChromeDriver are available. Call this first."""
        await call("GET", "/healthz")
        diagnostics = await call("GET", "/diagnostics/runtime")
        return {
            "running": True,
            "mode": diagnostics.get("mode"),
            "chrome_found": bool(diagnostics.get("chrome_path")),
            "chromedriver_found": bool(diagnostics.get("chromedriver_path")),
            "version": diagnostics.get("version"),
        }

    @server.tool()
    async def list_forms() -> Dict[str, Any]:
        """List forms already saved in the app (id, title, URL, question count)."""
        data = await call("GET", "/forms")
        forms = data.get("forms") or []
        return {"forms": forms[:MAX_LIST_ITEMS], "total": len(forms)}

    @server.tool()
    async def extract_form(
        form_url: str = Field(description="Public Google Form URL, https://docs.google.com/forms/d/..."),
    ) -> Dict[str, Any]:
        """Read a Google Form's questions and options into the app. Returns the form with its id."""
        data = await call("POST", "/form_filling/extract", {"form_url": form_url})
        form = await call("GET", f"/forms/{quoted(data['form_id'])}")
        return _compact_form(form["form"])

    @server.tool()
    async def get_form(form_id: str = Field(min_length=1, description="Form id from list_forms or extract_form")) -> Dict[str, Any]:
        """Show a saved form's questions, options and current answer settings."""
        data = await call("GET", f"/forms/{quoted(form_id)}")
        return _compact_form(data["form"])

    @server.tool()
    async def set_answer_config(
        form_id: str = Field(min_length=1),
        edits: Dict[str, Dict[str, Any]] = Field(
            description=(
                "Per question_id: optional fill_percentage (0-100), answers (list of text answers), "
                "options (list of {text, percentage, next_page_id}; next_page_id '__submit__' ends the "
                "form after that option). Option percentages of a single-choice question total 100; "
                "checkbox percentages are independent chances per option."
            ),
        ),
    ) -> Dict[str, Any]:
        """Change how answers are chosen for some questions of a saved form."""
        await call("POST", "/save_edit", {"form_id": form_id, "edits": edits})
        data = await call("GET", f"/forms/{quoted(form_id)}")
        return _compact_form(data["form"])

    @server.tool()
    async def simulate(
        form_id: str = Field(min_length=1),
        num_submissions: int = Field(ge=1, le=500),
        submission_mode: SubmissionMode = "prefill_link",
        seed: Optional[int] = Field(default=None, ge=0, description="Reuse a seed to get the same plan"),
    ) -> Dict[str, Any]:
        """Preview the answers a batch would send, per question against target. Sends nothing to Google."""
        body: Dict[str, Any] = {"form_id": form_id, "num_submissions": num_submissions,
                                "submission_mode": submission_mode}
        if seed is not None:
            body["seed"] = seed
        data = await call("POST", "/simulate", body)
        data.pop("success", None)
        data["sample_rows"] = (data.get("sample_rows") or [])[:MAX_SAMPLE_ROWS]
        return data

    @server.tool()
    async def start_run(
        form_id: str = Field(min_length=1),
        num_submissions: int = Field(ge=1, le=500),
        concurrent_threads: int = Field(default=1, ge=1, le=10),
        min_delay: float = Field(default=1, ge=0),
        max_delay: float = Field(default=5, ge=0),
        submission_mode: SubmissionMode = "prefill_link",
        seed: Optional[int] = Field(default=None, ge=0, description="Seed from simulate to send exactly that plan"),
    ) -> Dict[str, Any]:
        """Start submitting a batch to the real Google Form. Only call after the user has agreed."""
        body: Dict[str, Any] = {
            "form_id": form_id, "num_submissions": num_submissions,
            "concurrent_threads": concurrent_threads, "min_delay": min_delay, "max_delay": max_delay,
            "submission_mode": submission_mode,
        }
        if seed is not None:
            body["seed"] = seed
        data = await call("POST", "/start_submission", body)
        return {key: data.get(key) for key in ("run_id", "seed", "prepared_count", "submission_mode", "warnings", "message")}

    @server.tool()
    async def run_status(form_id: str = Field(min_length=1)) -> Dict[str, Any]:
        """Progress of the current or last run of a form."""
        return await call("GET", f"/submission_status?form_id={quoted(form_id)}")

    @server.tool()
    async def stop_run(form_id: str = Field(min_length=1, description="Form whose run should stop")) -> Dict[str, Any]:
        """Stop the running batch of one form."""
        return await call("POST", "/stop_submission", {"form_id": form_id})

    @server.tool()
    async def list_runs(form_id: str = Field(min_length=1)) -> Dict[str, Any]:
        """List the runs of a form, newest first."""
        data = await call("GET", f"/runs?form_id={quoted(form_id)}")
        runs = data.get("runs") or []
        return {"runs": runs[:MAX_LIST_ITEMS], "total": len(runs)}

    @server.tool()
    async def get_report(run_id: str = Field(min_length=1)) -> Dict[str, Any]:
        """Outcome of a run: counts, failure reasons, and actual against target per question."""
        data = await call("GET", f"/runs/{quoted(run_id)}")
        data.pop("success", None)
        return data

    @server.tool()
    async def retry_failed(
        run_id: str = Field(min_length=1),
        include_unknown: bool = Field(default=False, description="Also resend responses whose outcome is unknown; they may already have reached Google"),
    ) -> Dict[str, Any]:
        """Start a new run that resends the failed responses of a run with the same answers."""
        data = await call("POST", f"/runs/{quoted(run_id)}/retry", {"include_unknown": include_unknown})
        data.pop("success", None)
        return data

    @server.tool()
    async def apply_preset(
        form_id: str = Field(min_length=1),
        preset: Literal["uniform", "positive_skew", "negative_skew", "bell", "first_heavy"] = Field(
            description="uniform, first_heavy for any choice question; positive_skew, negative_skew and bell for scale questions",
        ),
        question_id: str = Field(default="all", min_length=1, description="One question_id, or 'all' for every question the preset fits"),
    ) -> Dict[str, Any]:
        """Set option percentages of choice questions to a ready-made distribution."""
        form = (await call("GET", f"/forms/{quoted(form_id)}"))["form"]
        edits: Dict[str, Any] = {}
        skipped = []
        for question in _compact_form(form)["questions"]:
            if question_id != "all" and question["question_id"] != question_id:
                continue
            options = question.get("options") or []
            if not options or preset not in presets_for(question["type"]):
                skipped.append(question["question_id"])
                continue
            values = apply_distribution_preset(len(options), preset, question["type"] in ORDERED_TYPES)
            edits[question["question_id"]] = {
                "options": [{"text": option["text"], "percentage": value} for option, value in zip(options, values)],
            }
        if not edits:
            raise ToolError(f"Preset '{preset}' fits none of the selected questions.")
        await call("POST", "/save_edit", {"form_id": form_id, "edits": edits})
        return {"applied_to": list(edits), "skipped": skipped if question_id == "all" else []}

    @server.tool()
    async def export_config(form_id: str = Field(min_length=1)) -> Dict[str, Any]:
        """Export a form's answer configuration as a template object that import_config accepts."""
        return await call("GET", f"/forms/{quoted(form_id)}/config/export")

    @server.tool()
    async def import_config(
        form_id: str = Field(min_length=1),
        template: Optional[Dict[str, Any]] = Field(default=None, description="Template object from export_config"),
        template_id: Optional[str] = Field(default=None, description="Id of a saved template from list_templates"),
        apply: bool = Field(default=False, description="False only previews which questions match; True applies them"),
    ) -> Dict[str, Any]:
        """Apply a configuration template to a form. Preview first (apply false), then apply."""
        if (template is None) == (template_id is None):
            raise ToolError("Give either template or template_id.")
        body: Dict[str, Any] = {"apply": apply}
        if template is not None:
            body["template"] = template
        else:
            body["template_id"] = template_id
        data = await call("POST", f"/forms/{quoted(form_id)}/config/import", body)
        data.pop("success", None)
        return data

    @server.tool()
    async def get_personas(form_id: str = Field(min_length=1)) -> Dict[str, Any]:
        """Show a form's personas: weighted groups of respondents with their own answer settings."""
        data = await call("GET", f"/forms/{quoted(form_id)}/personas")
        return {"personas": data.get("personas") or []}

    @server.tool()
    async def set_personas(
        form_id: str = Field(min_length=1),
        personas: List[Dict[str, Any]] = Field(
            max_length=8,
            description=(
                "The full list, replacing any existing one; [] removes personas. Each item: name, weight "
                "(all weights total 100), optional description, and overrides: question_id -> "
                "{fill_percentage, answers, options: [{text, percentage}]} for questions that differ "
                "from the form's shared settings. Option texts must exist on the question."
            ),
        ),
    ) -> Dict[str, Any]:
        """Replace the personas of a form. Simulate afterwards to check the split."""
        data = await call("POST", f"/forms/{quoted(form_id)}/personas", {"personas": personas})
        return {"personas": data.get("personas") or []}

    @server.tool()
    async def list_templates() -> Dict[str, Any]:
        """List answer configuration templates saved in the app."""
        data = await call("GET", "/templates")
        templates = data.get("templates") or []
        return {"templates": templates[:MAX_LIST_ITEMS], "total": len(templates)}

    return server


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    create_server().run("stdio")


if __name__ == "__main__":
    main()

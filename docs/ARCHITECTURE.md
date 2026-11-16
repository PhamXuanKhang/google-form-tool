# Architecture

This project is a local desktop app for extracting, configuring, and submitting Google Forms in bulk. The packaged product runs an Electron shell and a local Flask backend; source development can run the Flask backend directly.

## Runtime Entry Points

- `wsgi.py` starts the Flask backend with Waitress outside debug mode.
- `app/__init__.py` creates the Flask app, registers routes, and initializes logging.
- `electron/main.js` owns the desktop window lifecycle.
- `electron/backendProcess.js` starts and stops the packaged backend sidecar.
- `app/mcp_server.py` (`python -m app.mcp_server`, packaged as `GoogleFormToolMcp.exe` via `mcp_server_entry.py`) is a stdio MCP server for agents. It proxies the running backend over HTTP on `127.0.0.1`, found through `runtime.json`; see `docs/decisions/0005-mcp-proxy.md`.
- `app/factory.py` holds the Flask application factory; `import app` stays light and loads it on first use.

## Main Flows

- Extract: `app/routes/forms.py` receives a Google Form URL and delegates browser extraction to `app/adapters/browser/form_extractor.py`.
- Configure: templates and JS under `app/templates/` and `app/static/js/form_filling/` render question configs and validate client-side input.
- Submit: `app/routes/submissions.py` validates requests, builds a seeded plan with `app/domain/response_plan.py` (the exact answer rows to send), records it as a run, and starts `app/services/submission_manager.py`. The manager tracks active submitters and runs `app/adapters/browser/form_submitter.py` workers, which take plan rows for direct or prefilled URL submission and report each row's result.
- Prefill: `app/domain/prefill_link_generator.py` builds Google Forms prefill URLs from configured answers.
- Storage: `app/services/storage_service.py` persists forms and submission history in TinyDB (`db.json`). `app/services/run_store.py` keeps one header per run in the `runs` table and every row in an append-only `<APP_DATA>/runs/<run_id>.jsonl`, so row updates never rewrite `db.json`. See `docs/decisions/0004-run-store.md`.
- Scheduled runs: `app/services/drip_runner.py` runs one background thread per scheduled run, sending responses at the times stored in the run log (`app/domain/drip_schedule.py`). There is no global scheduler. Electron stops the backend with a hard kill, so on startup `create_app` marks unfinished runs `interrupted` and in-flight responses `unknown`; nothing is sent until the user resumes.
- Runtime: on startup the backend writes `<APP_DATA>/runtime.json` (port, pid) for local clients (`app/services/runtime_info.py`).
- Diagnostics: the `/healthz` and diagnostics routes expose runtime health for desktop support.
- Landing: `landing/` is a separate static site deployed on its own (for example to Vercel). It is not part of the packaged app; its release link points to GitHub Releases latest.

## Boundaries

- UI code should call Flask routes, not storage or Selenium directly.
- The MCP server calls Flask routes only. It must not import storage, Flask or Selenium, and must not write anything but the MCP protocol to stdout.
- Route handlers live in `app/routes/` (one shared `main` blueprint), validate input, and delegate business logic to `app/domain/`, `app/adapters/`, or `app/services/`. See `docs/decisions/0002-route-split.md`.
- `app/domain/` holds form processing, prefill link generation, and form copy planning, and does not import Selenium or adapters. Browser automation lives in `app/adapters/browser/` and the Gemini client in `app/adapters/ai/`. Runtime configuration is `app/config.py`.
- Selenium lifecycle belongs in extractor/submitter/copy modules; each path must clean up drivers.
- Generated artifacts, local reports, and AI planning scratch files should stay ignored and out of the repo.

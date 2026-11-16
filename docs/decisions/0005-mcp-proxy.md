# 0005 MCP server as a proxy to the running app

Date: 2026-11-17

## Status

Accepted

## Context

Release 2.0 lets an agent (Claude or another MCP client) extract, configure, simulate, run,
stop and review form batches. MCP clients start servers as separate stdio processes. The app's
data and live state belong to the backend process:

- TinyDB rewrites `db.json` and locks only inside one process (`app/services/storage_service.py`).
- Running submissions are tracked in memory (`app/services/submission_manager.py`).
- The packaged backend exe is built without a console and prints to stdout (`wsgi.py`), while
  MCP stdio needs a console process whose stdout carries only the protocol.

## Decision

1. `app/mcp_server.py` is a stdio MCP server built with the official Python SDK (`mcp==1.30.0`,
   FastMCP). Every tool calls the running backend over HTTP on `127.0.0.1`. The server never
   opens storage, never imports Flask or Selenium, and never starts the backend.
2. It finds the backend through `<APP_DATA>/runtime.json` (port, pid), written at backend
   startup, and confirms it with `GET /healthz` before each call. With no file or no answer,
   every tool returns "Google Form Automation Tool is not running. Open the app, then try again."
3. Tools go through the same routes as the UI, so validation, the 500-response and 10-thread
   limits, and the one-run-per-form conflict (409) apply unchanged. Backend errors become tool
   errors carrying the backend's message. No tool takes an AI key, and `stop_run` needs a form
   id (no stop-all).
4. The package ships a second exe, `GoogleFormToolMcp.exe`, with its console always on, in the
   same folder as the backend exe and sharing its libraries. From source it runs as
   `python -m app.mcp_server`. Settings shows the configuration to paste into Claude Desktop or
   Claude Code, and the Claude skill `skills/google-form-automation/SKILL.md`.
5. `import app` became light: the Flask factory moved to `app.factory`, and `create_app` and
   the models load on first use, so the MCP process imports only what it needs.

## Alternatives Considered

1. MCP server opening `db.json` directly. Rejected: two processes writing TinyDB lose updates,
   and it could not see or stop runs held in the backend's memory.
2. A `--mcp` flag on the backend exe. Rejected: the exe's console mode is fixed at build time,
   and the backend writes to stdout.
3. Starting the backend from the MCP server when it is closed. Rejected by the release contract;
   the user keeps control of when the app runs.

## Consequences

Positive:

- One source of truth and one set of checks for UI and agent.
- The MCP server stays small and has no access to storage.

Tradeoffs:

- The app must be open for any tool to work.
- `mcp` 1.30.0 needs pydantic 2.12 or newer on Python 3.14, so pydantic moved from 2.11.5 to
  2.12.5. `mcp` 2.x is not used yet: it needs a newer pydantic and renames the server API.
- A hard-killed backend leaves `runtime.json` behind. The health check covers it, but another
  program answering `/healthz` on the same port would be trusted.

## Follow-Up

- Presets, personas and scheduled runs add their own tools in later phases.

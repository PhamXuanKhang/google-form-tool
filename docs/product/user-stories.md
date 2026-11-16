# User Stories

Behavior described here is what the code does today. Status values:
`keep` (stays as is), `change` (behavior will change), `retire` (removed).

## US-001 Extract a public Google Form

As a form tester, I want to paste a Google Form URL and see its questions, so that I can
configure how it will be filled.

Status: keep

Acceptance criteria:

1. A missing or non-Google-Forms URL is rejected with HTTP 400 and an error message.
2. A valid URL returns the form title, pages, and questions with supported options; the form is stored locally.
3. If Chrome or ChromeDriver cannot start, or the form cannot be loaded, the user gets an error (HTTP 500) with runtime diagnostics instead of a crash.
4. `GET /form_filling/preview` returns the stored form for the current session, or 400/404 when none exists.

Routes: `/form_filling` (GET, POST), `/form_filling/extract`, `/form_filling/preview`
Modules: `app/adapters/browser/form_extractor.py`, `app/adapters/browser/driver_manager.py`
Tests: `tests/test_form_extractor.py`, `tests/test_extract_route.py`, `tests/test_driver_manager.py`

## US-002 Configure answers

As a form tester, I want to set answer probabilities, custom responses, or load answers from
a file, so that submissions follow the distribution I need.

Status: keep

Acceptance criteria:

1. Invalid answer configuration (bad probabilities, missing form id, empty edits) is rejected with HTTP 400; an unknown form returns 404.
2. A valid edit is applied to the stored form and persisted.
3. Uploading a CSV, JSON, or XLSX file returns one parsed response row per submission; other formats, a missing file, or an oversized file are rejected (400/413).
4. The browser-side validator rejects invalid probability input before it is sent.

Routes: `/save_edit`, `/load_data`
Modules: `app/domain/form_processor.py`, `app/static/js/form_filling/`
Tests: `tests/test_form_processor.py`, `tests/test_save_edit_route.py`, `tests/test_js_prefill_validator.py`, `tests/test_question_entry_id.py`

## US-003 Submit configured responses

As a form tester, I want to run a controlled batch of submissions, either by filling the form
directly or through generated prefilled links, so that I get the responses I configured.

Status: keep

Acceptance criteria:

1. A request needs a form id; an unknown `submission_mode` is rejected with HTTP 400. Prefill is the default mode.
2. Submission count (1-500), concurrent threads (1-10, not above the count), and min/max delay are validated; invalid values return 400.
3. Responses come from the configured distribution, an uploaded data file (`upload_id`), or AI text answers.
4. Status can be polled per form or for all active submissions; a finished submission's final status is kept for 60 seconds.
5. A running submission can be stopped by form id, or all at once when no id is given.
6. Each submission result is saved to the form's history.
7. Every batch is planned before it starts and saved as a run: the response includes `run_id` and `seed`, sending the same `seed` again plans the same answers, and each response's answers and outcome are recorded. Direct mode draws each response independently; prefill mode keeps exact per-question quotas.

Routes: `/start_submission`, `/stop_submission`, `/submission_status`
Modules: `app/adapters/browser/form_submitter.py`, `app/domain/prefill_link_generator.py`, `app/domain/form_processor.py`, `app/domain/response_plan.py`, `app/services/run_store.py`
Tests: `tests/test_form_submitter.py`, `tests/test_submission_status_retention.py`, `tests/test_prefill_link_generator.py`, `tests/test_prefill_submission.py`, `tests/test_submission_persistence.py`, `tests/test_response_plan.py`, `tests/test_run_store.py`, `tests/test_planned_submission.py`

## US-004 Generate AI text answers

As a form tester, I want to generate varied text answers for a text question with my Gemini
API key, so that I do not have to write them by hand.

Status: keep

Acceptance criteria:

1. `/validate_api_key` reports whether a key is usable; a missing key returns 400, and a missing AI dependency or unavailable model returns a coded error.
2. `/generate_ai_text_answers` requires form id, question id, and API key, and a count between 1 and 500.
3. Only text and textarea questions are accepted; other question types return 400.
4. The API key is never written to logs or echoed in responses.
5. Timeouts return 504 and other provider failures return 500 with a generic message.

Routes: `/validate_api_key`, `/generate_ai_text_answers`
Modules: `app/adapters/ai/ai_responder.py`
Tests: `tests/test_ai_text_route.py`, `tests/test_ai_model_resolution.py`, `tests/test_ai_generator_gating.py`, `tests/test_validate_api_key_route.py`

## US-005 Review forms, history, and exports

As a form tester, I want to see my recent forms and past submissions and export them, so that
I can review what was sent.

Status: keep

Acceptance criteria:

1. The home page lists stored forms and filters them by a search term on title or description.
2. A form can be deleted by URL; an empty URL returns 400 and an unknown form 404.
3. Submission history for a form is returned as JSON.
4. History exports as CSV (default) or JSON as a file download; an unknown form returns 404.
5. Forms, submissions, and history persist locally between app restarts.

Routes: `/`, `/forms/delete`, `/submission_history/<form_id>`, `/export_history/<form_id>`
Modules: `app/services/storage_service.py`
Tests: `tests/test_storage_service.py`, `tests/test_delete_form_route.py`, `tests/test_submission_history_route.py`, `tests/test_submission_persistence.py`

## US-006 Check app health and runtime

As a user or maintainer, I want to see whether the app and its Chrome driver are working, so
that I can fix setup problems.

Status: keep. The submission-time resource panel (CPU/memory chart, `/system_status`,
`/monitoring_history`) is retired.

Acceptance criteria:

1. `/healthz` returns HTTP 200 with `{"status": "ok"}`.
2. `/diagnostics/runtime` returns data, DB, and log paths, Chrome and ChromeDriver paths, and runtime mode (dev, frozen, electron).
3. The diagnostics settings page renders the same information.
4. The about page renders.

Routes: `/healthz`, `/diagnostics/runtime`, `/settings/diagnostics`, `/about`
Modules: `app/config.py`, `app/adapters/browser/driver_manager.py`
Tests: `tests/test_healthz.py`, `tests/test_runtime_diagnostics_route.py`, `tests/test_runtime_config.py`, `tests/test_i18n_render.py`

## US-007 Copy a form (best effort)

As a form owner, I want to preview and apply a copy of a source form onto a form I own, so
that I can reuse its structure. An exact clone is not claimed.

Status: keep

Acceptance criteria:

1. Extracting the source requires a Google Forms URL; invalid or empty URLs return 400.
2. The preview plan lists supported and unsupported features for the stored form; an unknown form returns 404.
3. Applying needs a valid Google Forms edit URL and an explicit ownership confirmation; otherwise it returns 400.
4. The result status is `success` or `partial` (HTTP 200); any other result returns 500.

Routes: `/form_copy`, `/form_copy/extract_source`, `/form_copy/preview_plan`, `/form_copy/apply_to_target`
Modules: `app/domain/form_copy_planner.py`, `app/adapters/browser/form_copier.py`
Tests: `tests/test_form_copier.py`, `tests/test_form_copy_planner.py`, `tests/test_form_copy_routes.py`, `tests/test_form_copy_ui.py`

## US-008 Distribute the Windows app

As a maintainer, I want to build the Windows installer and publish a landing page, so that
users can download the latest release.

Status: keep. `landing/` is a separate deployable; its placeholder URL is replaced at deploy time.

Acceptance criteria:

1. `scripts/package-windows.ps1` builds the backend sidecar and the Electron installer.
2. The packaged backend starts and answers `/healthz` with 200.
3. The landing page builds as a static site and its call to action links to the latest GitHub release.

Routes: none (packaging and static site)
Modules: `scripts/package-windows.ps1`, `google_form_tool.spec`, `electron-builder.yml`, `landing/`
Tests: manual packaging smoke; `landing/package.json` build

## US-009 Use the app offline with a consistent interface

As a user, I want every screen to load without internet, follow my light or dark preference,
and share one navigation, so that the desktop app works anywhere and feels like one tool.

Status: keep

Acceptance criteria:

1. The five pages load scripts, stylesheets, fonts, icons and images only from the app;
   third-party libraries live in `app/static/vendor/` with their licenses.
2. The theme follows the OS preference until the user picks one in the sidebar; the choice
   persists and is applied before first paint. Reduced-motion preferences turn off
   non-essential animation.
3. A left sidebar links Home, Form Filling, Copy Form, Settings and About, marks the current
   page, holds the language picker, theme toggle, bug report link and version, and collapses
   to icons in narrow windows.
4. Form Filling shows a horizontal stepper; loading, empty and error states each have their
   own design, and notifications use one shared toast.

Routes: none new (restyles `/`, `/form_filling`, `/form_copy`, `/settings/diagnostics`, `/about`)
Modules: `app/templates/base.html`, `app/static/css/tokens.css`, `app/static/css/styles.css`, `app/static/js/scripts.js`, `app/static/vendor/`
Tests: `tests/test_offline_assets.py`, `tests/test_i18n_render.py`, `tests/test_form_copy_ui.py`; visual check by eye in both themes

## US-010 Preview a batch before sending

As a form tester, I want to see the answers a batch will send before anything reaches Google,
so that I can fix the configuration first.

Status: keep

Acceptance criteria:

1. `POST /simulate` plans the batch with the same seeded planner a run uses and returns, per
   question, counts and rates per option next to the configured target (text questions: distinct
   values and samples), blank rates, skipped-answer warnings and up to 20 sample rows.
2. Simulation never starts a browser and never records a run; more than 500 responses returns 400.
3. Starting a run with the simulated `seed` sends exactly the simulated rows, in both submission modes.
4. Form Filling step 4 shows the preview with charts and samples, can generate a new plan, and can run exactly the previewed one.

Routes: `/simulate`
Modules: `app/domain/run_report.py`, `app/domain/response_plan.py`, `app/routes/runs.py`, `app/static/js/form_filling/simulation.js`
Tests: `tests/test_simulation_and_reports.py`, `tests/test_run_report.py`

## US-011 Review a run and resend failures

As a form tester, I want a report of each run and a way to resend the responses that failed,
so that I know what reached the form and can complete the batch.

Status: keep

Acceptance criteria:

1. `GET /runs?form_id=` lists a form's runs, newest first; `GET /runs/<run_id>` returns the header and a summary: success, failed, unknown and pending counts, duration, failure reasons, and actual against target per question counting only successful responses.
2. `GET /runs/<run_id>/rows` pages responses (limit up to 100) and filters by status; `GET /runs/<run_id>/export?format=csv|json` downloads them, and CSV cells that a spreadsheet would run as a formula are neutralized.
3. `POST /runs/<run_id>/retry` starts a new run with the original answers of failed responses. Responses with an unknown outcome are included only with `include_unknown: true`. A retry always refers to the first run, and a response any retry already sent successfully is never sent again; when nothing is left, it returns 400. A running submission on the form returns 409, an unknown run 404.
4. Run ids outside the expected format return 400 before any file is read. Responses still marked in flight on a run that is no longer running read as unknown.
5. The monitor shows live counts, rate per minute, time left and the latest responses, and links to the report page `/runs/<run_id>/view`. The Home form popup lists the form's runs.

Routes: `/runs`, `/runs/<run_id>`, `/runs/<run_id>/rows`, `/runs/<run_id>/export`, `/runs/<run_id>/retry`, `/runs/<run_id>/view`
Modules: `app/routes/runs.py`, `app/domain/run_report.py`, `app/services/run_store.py`, `app/services/history_export.py`, `app/templates/run_report.html`, `app/static/js/run_report.js`
Tests: `tests/test_simulation_and_reports.py`, `tests/test_run_report.py`, `tests/test_planned_submission.py`

## US-012 Drive the app from an agent

As a Claude (or other MCP client) user, I want an agent to extract, configure, preview, run and
review form batches through the app, so that I can hand off a test with one request.

Status: keep

Acceptance criteria:

1. The MCP server (`GoogleFormToolMcp.exe`, or `python -m app.mcp_server` from source) offers
   `app_status`, `list_forms`, `extract_form`, `get_form`, `set_answer_config`, `simulate`,
   `start_run`, `run_status`, `stop_run`, `list_runs`, `get_report` and `retry_failed`.
2. Every tool goes through the running app over `127.0.0.1`; when the app is closed, tools say
   to open it. The server never opens the database or starts the app.
3. The app's limits and checks apply unchanged (500 responses, 10 threads, one run per form);
   errors from the app come back as tool errors. `stop_run` requires a form id.
4. Only JSON-RPC is written to the server's stdout.
5. Settings shows the configuration for Claude Desktop and Claude Code, and the Claude skill,
   which tells the agent to simulate first and to send only after the user agrees.
6. `GET /forms` and `GET /forms/<form_id>` return saved forms as JSON; `/form_filling/extract`
   also returns the `form_id`.

Routes: `/forms`, `/forms/<form_id>` (plus the routes the tools call)
Modules: `app/mcp_server.py`, `mcp_server_entry.py`, `app/runtime_info.py`, `app/routes/forms.py`, `app/routes/pages.py`, `skills/google-form-automation/SKILL.md`
Tests: `tests/test_mcp_server.py`, `tests/test_route_snapshot.py`; `scripts/smoke-mcp.py` (packaged or `--from-source`)

## US-013 Reuse answer setups with presets and templates

As a form tester, I want ready-made distributions and reusable answer setups, so that I can
configure long or repeated forms quickly.

Status: keep

Acceptance criteria:

1. Choice questions offer presets: even and first-heavy for any choice question; lean high, lean
   low and bell for scale questions. Percentages total exactly 100 with two decimals and stay
   editable; a preset can be applied to every question of the same type.
2. A template holds a form's answer settings apart from the form (schema version, name,
   structure fingerprint, per-question settings) and never an API key or a file path.
3. `GET /forms/<form_id>/config/export` downloads a template; `POST /forms/<form_id>/config/import`
   takes a file, a template object or a saved `template_id` and returns a preview of matched,
   unmatched and missing questions. It changes the form only with `apply: true`, and only for
   matched questions; a question whose options differ is not applied.
4. Exporting and importing into the same form restores its configuration exactly.
5. Invalid templates, unknown schema versions, unknown fields and non-JSON files return 400;
   files over the upload limit return 413; the form is unchanged in every case.
6. Named templates can be saved, listed and deleted (`/templates`).
7. The MCP server offers `apply_preset`, `export_config`, `import_config` (preview by default)
   and `list_templates`.

Routes: `/presets`, `/forms/<form_id>/config/export`, `/forms/<form_id>/config/import`, `/templates`, `/templates/<template_id>/delete`
Modules: `app/domain/distribution_presets.py`, `app/domain/config_template.py`, `app/services/template_store.py`, `app/routes/templates.py`, `app/static/js/form_filling/config_tools.js`
Tests: `tests/test_presets_and_templates.py`, `tests/test_mcp_server.py`

## US-014 Model respondent groups and let AI propose a setup

As a form tester, I want responses to come from distinct groups whose answers hang together, and
I want an AI to propose a configuration from a plain description, so that test data looks like
real respondents with little manual work.

Status: keep

Acceptance criteria:

1. A form can have up to 8 personas with weights totalling 100; each persona overrides the
   shared settings only for the questions where it differs. Branching stays shared.
2. A plan splits responses across personas with exact quotas, builds each persona's rows from
   its own settings, tags them with the persona, and shuffles them with the seed. Every answer in
   a response comes from the same persona. Without personas, plans are unchanged.
3. `GET`/`POST /forms/<form_id>/personas` read and replace the list; weights not totalling 100,
   more than 8 personas, unknown questions or options, and invalid percentages return 400 and
   save nothing. Forms saved before personas still load.
4. Simulation and run reports break results down per persona against each persona's own
   targets; overall targets blend the personas by weight. Templates carry personas.
5. `POST /ai/propose_config` (form, Gemini key, audience description, optional personas) returns
   a checked proposal with current and proposed settings and warnings, and saves nothing. Invalid
   or malformed answers return a coded 422; unknown questions and options are dropped with a
   warning; a timeout returns 504. The key is never logged, stored or returned.
6. The UI applies only the questions and personas the user selects. MCP offers `get_personas` and
   `set_personas`, and no AI tool, since MCP never takes an API key.
7. `/save_edit` rejects invalid settings (percentages outside 0-100, missing option percentages,
   non-text answers) with 400 instead of saving a form that can no longer load.

Routes: `/forms/<form_id>/personas`, `/ai/propose_config`
Modules: `app/domain/personas.py`, `app/domain/response_plan.py`, `app/domain/autopilot_proposal.py`, `app/domain/edit_validation.py`, `app/adapters/ai/ai_responder.py`, `app/routes/personas.py`, `app/routes/ai.py`, `app/static/js/form_filling/personas_autopilot.js`
Tests: `tests/test_personas.py`, `tests/test_ai_autopilot.py`, `tests/test_edit_validation.py`, `tests/test_mcp_server.py`

## US-015 Spread a run over time

As a form tester, I want a batch sent gradually over a time window that I can pause and resume,
also after closing the app, so that long runs do not arrive all at once.

Status: keep

Acceptance criteria:

1. `/start_submission` accepts `schedule: {window_minutes}` from 1 minute to 7 days; other values
   return 400. Without it, runs behave as before.
2. Every response gets its own send time inside the window, spread evenly with jitter. Only due
   responses are sent, at most one per thread per tick; a backlog (for example after the computer
   slept) is spread again, never sent in a burst.
3. `POST /runs/<run_id>/pause` stops taking new responses; `POST /runs/<run_id>/resume` continues a
   paused or interrupted scheduled run over what is left of the window, keeping at least the
   minimum delay between sends when the window has passed. A running submission on the form
   returns 409.
4. When the app starts, unfinished runs become `interrupted` and responses that were being sent
   become `unknown`. Nothing is sent until the user resumes, no response is sent twice, and
   `unknown` responses are never resent automatically.
5. Stopping a scheduled run leaves waiting responses unsent and marks the run `stopped`.
6. The UI previews the pace, shows the next send time with pause and resume, offers resume on the
   report, shows a Home banner for interrupted runs, and states that runs only send while the
   app is open. The desktop app asks before closing while a run is in progress.
7. MCP `start_run` accepts `window_minutes`; `pause_run` and `resume_run` are available.

Routes: `/runs/<run_id>/pause`, `/runs/<run_id>/resume` (plus `schedule` on `/start_submission`, `status` on `/runs`)
Modules: `app/domain/drip_schedule.py`, `app/services/drip_runner.py`, `app/services/run_store.py`, `app/routes/runs.py`, `app/factory.py`, `electron/main.js`
Tests: `tests/test_drip.py`, `tests/test_mcp_server.py`

## Route to story map

| Route | Story |
| --- | --- |
| `/healthz`, `/diagnostics/runtime`, `/settings/diagnostics`, `/about` | US-006 |
| `/`, `/forms/delete`, `/submission_history/<form_id>`, `/export_history/<form_id>` | US-005 |
| `/form_filling`, `/form_filling/extract`, `/form_filling/preview` | US-001 |
| `/load_data`, `/save_edit` | US-002 |
| `/start_submission`, `/stop_submission`, `/submission_status` | US-003 |
| `/validate_api_key`, `/generate_ai_text_answers` | US-004 |
| `/form_copy`, `/form_copy/extract_source`, `/form_copy/preview_plan`, `/form_copy/apply_to_target` | US-007 |
| `/simulate` | US-010 |
| `/forms`, `/forms/<form_id>` | US-012 |
| `/presets`, `/forms/<form_id>/config/export`, `/forms/<form_id>/config/import`, `/templates`, `/templates/<template_id>/delete` | US-013 |
| `/forms/<form_id>/personas`, `/ai/propose_config` | US-014 |
| `/runs/<run_id>/pause`, `/runs/<run_id>/resume` | US-015 |
| `/runs`, `/runs/<run_id>`, `/runs/<run_id>/rows`, `/runs/<run_id>/export`, `/runs/<run_id>/retry`, `/runs/<run_id>/view` | US-011 |

Retired routes (no story): `/generate_response`, `/ai_status`, `/monitoring_history`, `/system_status`.

## Backlog

Candidate work that is not yet a story.

| Epic | Description | Status |
| --- | --- | --- |
| E01 form-filling reliability | Improve unsupported question handling, required-field diagnostics, and browser cleanup when specific failures recur | candidate |
| E02 desktop packaging | Keep Windows packaging, install smoke, and runtime diagnostics aligned with releases | candidate |
| E03 harness maturity | Add story packets and decisions only when repeated friction proves they are useful | dropped; the harness was collapsed into `docs/WORKFLOW.md` |

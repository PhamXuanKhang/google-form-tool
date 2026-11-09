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

Routes: `/start_submission`, `/stop_submission`, `/submission_status`
Modules: `app/adapters/browser/form_submitter.py`, `app/domain/prefill_link_generator.py`, `app/domain/form_processor.py`
Tests: `tests/test_form_submitter.py`, `tests/test_submission_status_retention.py`, `tests/test_prefill_link_generator.py`, `tests/test_prefill_submission.py`, `tests/test_submission_persistence.py`

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

Retired routes (no story): `/generate_response`, `/ai_status`, `/monitoring_history`, `/system_status`.

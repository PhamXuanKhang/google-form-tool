# Detailed Test Plan

Date: 2026-06-14
Branch: `goal-project-refactor-audit`
Scope: Google Form Automation Tool desktop/local app, backend, Electron shell, landing page, and Windows packaging.

## 1. Purpose

This plan defines how to start detailed verification for each existing feature, with clear coverage across unit, integration, E2E, platform, and release smoke checks.

Goals:

- Verify that existing implemented features still satisfy the product contract in `docs/TEST_MATRIX.md`.
- Expand manual E2E coverage where automated tests cannot prove real browser, desktop, provider, or installer behavior.
- Keep every PASS tied to direct evidence: command, environment, result, and artifact.
- Keep unverified items PENDING until a safe test target, runtime, credential, or environment is available.
- Avoid scope creep: do not add new abstractions, dependencies, or runtime changes during test planning.

## 2. Test Principles

- No evidence, no PASS.
- Prefer automated tests when they already exist.
- Use manual verification only for UI, Google Forms DOM behavior, Electron runtime, installer, or external provider flows.
- Use tiny safe datasets for live submission tests.
- Do not run bulk submissions against production or third-party forms without explicit permission.
- Do not commit generated artifacts such as `dist/`, `release/`, `landing/dist/`, logs, screenshots, or local reports unless explicitly requested.
- If runtime code changes are needed later, run GitNexus impact analysis on the exact function/class/method/route before editing.
- Run `mcp__gitnexus.detect_changes(scope="all")` before committing any changes.

## 3. Required Environments

| Environment | Purpose | Required tools/data | PASS evidence |
| --- | --- | --- | --- |
| Local Python backend | Unit and backend integration tests | Python 3.12 venv, project deps | Pytest command output |
| Local Node/Electron | Electron static and desktop checks | Node.js, npm deps, Electron | `node --check`, module smoke, manual UI notes |
| Browser/Selenium | Extract, direct submit, prefill, copy flows | Chrome/Chromium, ChromeDriver or auto-resolved driver | Safe form URL, screenshots/notes, status/history evidence |
| External Google Form test target | Live extract/submit/pre-fill checks | Disposable form controlled by tester | Form response count, app status/history |
| AI provider test account | Live AI provider smoke | Non-production API key, bounded prompt | Request/response notes with secrets redacted |
| Windows packaging environment | Installer generation | Python venv, npm deps, PyInstaller/Electron Builder caches | Generated artifact list and checksum output |
| Clean Windows profile or VM | Install/uninstall smoke | Built NSIS/MSI installer | Install, launch, health check, uninstall notes |
| GitNexus CLI/MCP | Code intelligence health | `npx gitnexus`, MCP tools | CLI status; MCP query result if FTS works |

## 4. Baseline Commands

Run these before feature-specific testing.

| Check | Command | Expected result | Notes |
| --- | --- | --- | --- |
| Branch guard | `git status --short --branch` | On `goal-project-refactor-audit`; no unrelated changes | Stop if on `master`/`main`. |
| Harness matrix | `scripts\bin\harness-cli.exe query matrix` | 10 implemented stories | Confirms durable feature inventory. |
| Full pytest | `.\.venv\Scripts\python.exe -m pytest -q` | `215 passed, 1 deselected` or updated expected count | Record exact duration/result. |
| GitNexus CLI status | `npx gitnexus status` | Indexed/current commit match | Run `npx gitnexus analyze` if stale. |
| npm audit | `npm audit --audit-level=high` | `found 0 vulnerabilities` | Run after npm deps are installed. |
| Electron syntax | `node --check electron\main.js`; `node --check electron\backendProcess.js`; `node --check electron\preload.js` | All parse successfully | Static proof only, not UI proof. |
| Landing build | `cd landing; npm run build` | `landing/dist` contains copied static assets | Remove generated `landing/dist` after verification unless needed locally. |

## 5. Test Data Strategy

### 5.1 Disposable Google Forms

Create or identify controlled forms for manual/live verification:

| Form | Required question types | Purpose | Safety rule |
| --- | --- | --- | --- |
| `GF-SMOKE-01-basic` | Short answer, paragraph, multiple choice, checkbox | Extract/configure/direct submit smoke | Max 1-2 submissions per run. |
| `GF-SMOKE-02-prefill` | Text, radio, checkbox, date/time if supported | Prefill URL generation and prefill submission | Verify generated URL before submit. |
| `GF-SMOKE-03-required` | Required fields and validation edge cases | Required-field diagnostics | Stop after validation/status proof. |
| `GF-SMOKE-04-pages` | Multi-page form with sections | Page extraction and navigation | Use only controlled test form. |
| `GF-SMOKE-05-copy-source` | Mixed supported/unsupported fields | Form copy preview/apply | Do not claim exact clone. |

### 5.2 AI Provider Test Data

- Use a non-production API key only.
- Use a bounded prompt such as: `Generate a concise survey answer under 20 words.`
- Redact API keys from logs, screenshots, commits, and notes.
- Record provider/model, request route, HTTP status, and response shape.

### 5.3 Local Persistence Data

- Use a temporary form name prefix: `E2E_TEST_<date>_<case>`.
- Before testing, note existing history count if visible.
- After testing, verify new history/status entries and export behavior.
- Do not delete user data unless the test explicitly requires cleanup and the tester approves.

## 6. Feature-by-Feature Test Plan

### 6.1 Extract Form

| Field | Plan |
| --- | --- |
| Objective | Verify that a Google Form respondent URL is parsed into local title, description, pages, questions, options, and entry IDs. |
| Use case | User pastes a public Google Form URL and previews the structure before configuring answers. |
| Expected behavior | App returns supported fields, warns or marks unsupported fields, and does not leak browser drivers after extraction. |
| Unit tests | `tests/test_form_extractor.py`, `tests/test_question_entry_id.py`, `tests/test_driver_manager.py` |
| Integration tests | `tests/test_extract_route.py` |
| E2E/manual | Start app, extract `GF-SMOKE-01-basic`, verify title/questions/options in UI. Repeat with `GF-SMOKE-04-pages` for sections/pages. |
| Acceptance criteria | Extract route returns success for safe form; UI preview matches source form; unsupported fields are visible as warnings, not silent failures. |
| Test criteria | Record command/session, form URL owner, question count, page count, and app status. |
| Risks | Google Forms DOM changes; Chrome/driver mismatch; private form permissions; unsupported question types. |
| Current status | Automated PASS; live browser extraction PENDING until safe target is available. |

### 6.2 Configure Answers

| Field | Plan |
| --- | --- |
| Objective | Verify answer probability/custom response validation in backend and UI. |
| Use case | User adjusts probabilities and custom text before submitting responses. |
| Expected behavior | Invalid probabilities/configs are rejected; valid configs are accepted and preserved for submission. |
| Unit tests | `tests/test_form_processor.py`, `tests/test_js_prefill_validator.py`, `tests/js/test_prefill_validator.mjs` |
| Integration tests | Route coverage through save/edit and prefill validation tests. |
| E2E/manual | Extract `GF-SMOKE-01-basic`, configure valid and invalid values, verify inline/UI validation and backend rejection. |
| Acceptance criteria | Invalid sum/empty required configs cannot proceed; valid config can be saved and used. |
| Test criteria | Capture invalid case, valid case, and resulting UI/backend status. |
| Risks | JS validation diverges from backend validation; unsupported question type config appears editable. |
| Current status | Automated PASS; rendered browser validation PENDING. |

### 6.3 Bulk Direct Submit

| Field | Plan |
| --- | --- |
| Objective | Verify controlled bulk direct submission with worker status tracking and safe delay/thread settings. |
| Use case | User submits a small number of configured responses to a controlled form. |
| Expected behavior | App starts workers, respects thread/delay settings, reports success/failure counts, and retains recent status. |
| Unit tests | `tests/test_form_submitter.py`, `tests/test_submission_status_retention.py` |
| Integration tests | Submission route/status tests through existing pytest suite. |
| E2E/manual | Use `GF-SMOKE-01-basic`, 1 thread, 1-2 total submissions, conservative delay. Verify Google Form response count and app history/status. |
| Acceptance criteria | Safe test form receives expected response count; app reports terminal status; no orphan browser processes. |
| Test criteria | Record form ownership, response count before/after, app status, and cleanup. |
| Risks | Accidental spam, Google anti-abuse throttling, DOM changes, driver cleanup failure. |
| Current status | Automated PASS; live direct submit PENDING until safe target is available. |

### 6.4 Prefill Submit

| Field | Plan |
| --- | --- |
| Objective | Verify prefilled URL generation and optional submission flow. |
| Use case | User chooses prefill flow instead of direct browser filling. |
| Expected behavior | App builds valid Google Forms prefill URLs and can submit a tiny safe response when requested. |
| Unit tests | `tests/test_prefill_link_generator.py`, `tests/test_prefill_submission.py`, `tests/test_js_prefill_validator.py` |
| Integration tests | Prefill submission route tests in pytest suite. |
| E2E/manual | Use `GF-SMOKE-02-prefill`, generate URL, open it manually, verify fields are populated, submit 0-1 response if approved. |
| Acceptance criteria | URL contains expected entry parameters; form displays prefilled answers; status/history update if submitted. |
| Test criteria | Record generated URL shape with sensitive values redacted if needed, and before/after response count. |
| Risks | Google entry ID mismatch; URL encoding issues; unsupported fields. |
| Current status | Automated PASS; live prefill check PENDING. |

### 6.5 AI Answer Generation

| Field | Plan |
| --- | --- |
| Objective | Verify local validation and live provider behavior for bounded AI-generated text answers. |
| Use case | User requests generated text for open-ended survey answers. |
| Expected behavior | Missing/invalid API key is rejected; valid provider/model returns bounded text without exposing secrets. |
| Unit tests | `tests/test_ai_model_resolution.py`, `tests/test_ai_generator_gating.py` |
| Integration tests | `tests/test_ai_text_route.py`, `tests/test_validate_api_key_route.py` |
| E2E/manual | Configure non-production API key, call AI generation from UI/backend with bounded prompt, verify response shape and UI handling. |
| Acceptance criteria | Bad key path fails safely; good key path returns usable answer; secrets are not logged or committed. |
| Test criteria | Record provider, model, route/UI path, HTTP status, and redacted response sample. |
| Risks | Provider outage, quota/cost, key leakage, model response drift. |
| Current status | Automated local logic PASS; live provider PENDING until credentials are available. |

### 6.6 Persistence, History, and Export

| Field | Plan |
| --- | --- |
| Objective | Verify local storage of forms, submission history, status retention, and export behavior. |
| Use case | User reviews previous forms/submissions and exports CSV/history data. |
| Expected behavior | Data persists between app restarts and export includes expected fields. |
| Unit tests | `tests/test_storage_service.py`, `tests/test_submission_persistence.py`, `tests/test_submission_status_retention.py` |
| Integration tests | `tests/test_submission_history_route.py`, `tests/test_delete_form_route.py`, `tests/test_save_edit_route.py` |
| E2E/manual | Save a test form/config, restart app, verify it remains; run tiny submission/prefill and export history if UI supports it. |
| Acceptance criteria | Saved data survives restart; delete/edit routes work; export contains expected rows. |
| Test criteria | Record storage path from diagnostics, before/after item counts, and export filename if generated. |
| Risks | User data pollution, platform path differences, stale records from earlier tests. |
| Current status | Automated PASS; full desktop restart/export smoke PENDING. |

### 6.7 Runtime Diagnostics and Monitoring

| Field | Plan |
| --- | --- |
| Objective | Verify health, diagnostics, driver paths, monitoring metrics, and support visibility. |
| Use case | User/support opens diagnostics to troubleshoot local runtime. |
| Expected behavior | `/healthz` returns ok; diagnostics expose actionable mode/path/driver information; monitoring routes return safe JSON. |
| Unit tests | `tests/test_healthz.py`, `tests/test_runtime_config.py`, `tests/test_logging_and_warnings.py` |
| Integration tests | `tests/test_runtime_diagnostics_route.py`, `tests/test_monitoring_routes.py` |
| E2E/manual | Start source backend and Electron/packaged backend; open diagnostics page; verify Chrome/ChromeDriver/log paths. |
| Acceptance criteria | Health ok in source and packaged modes; diagnostics do not expose secrets; paths are actionable. |
| Test criteria | Record port, mode (`dev`/`frozen`), health response, and diagnostics fields checked. |
| Risks | Path differences across Windows profiles; packaged resource path drift. |
| Current status | Automated/backend smoke PASS; rendered diagnostics UI PENDING. |

### 6.8 Form Copy MVP

| Field | Plan |
| --- | --- |
| Objective | Verify best-effort copy preview/apply behavior for supported fields and warnings for unsupported fields. |
| Use case | User previews copying a source form into an editable target form. |
| Expected behavior | Preview identifies supported/unsupported operations; apply performs supported copy without claiming exact clone. |
| Unit tests | `tests/test_form_copier.py`, `tests/test_form_copy_planner.py` |
| Integration tests | `tests/test_form_copy_routes.py`, `tests/test_form_copy_ui.py` |
| E2E/manual | Use controlled source/target forms, preview copy, verify warnings, apply only with tester-owned target. |
| Acceptance criteria | Unsupported features are warned; supported operations succeed or fail with clear error; target form remains recoverable. |
| Test criteria | Record source/target ownership, operation summary, warnings, and target verification. |
| Risks | Google Forms editor DOM changes, destructive edits to target form, unsupported feature ambiguity. |
| Current status | Automated PASS; live browser/editor copy PENDING. |

### 6.9 Electron Desktop Shell

| Field | Plan |
| --- | --- |
| Objective | Verify Electron starts/stops backend correctly and renders the app workflow. |
| Use case | User launches desktop app from source or installed shortcut. |
| Expected behavior | Electron window opens, backend starts on expected port, app loads local UI, backend stops cleanly when app exits. |
| Unit/static tests | `node --check electron\main.js`, `node --check electron\backendProcess.js`, `node --check electron\preload.js` |
| Integration tests | Node require smoke for `electron/backendProcess` exports. |
| E2E/manual | Run `npm run electron:dev`, verify UI loads, open diagnostics, close app, verify no orphan backend process. |
| Acceptance criteria | Window renders; backend health ok; no orphan processes after exit. |
| Test criteria | Record launch command, port, health response, screenshots/notes, and process cleanup. |
| Risks | Electron version differences, Windows permissions, port collision. |
| Current status | Static smoke PASS; interactive desktop smoke PENDING. |

### 6.10 Windows Packaging and Installer

| Field | Plan |
| --- | --- |
| Objective | Verify reproducible package build and install/uninstall behavior. |
| Use case | Maintainer creates release installers and user installs app on Windows. |
| Expected behavior | Backend sidecar and NSIS/MSI installers are generated; installed app launches and uninstalls cleanly. |
| Automated/smoke | `.\scripts\package-windows.ps1` |
| Config checks | Electron builder config smoke for `extraResources`, backend source, backend target, NSIS, MSI. |
| E2E/manual | Install generated `.exe` or `.msi` in clean Windows profile/VM, launch from shortcut, verify health/diagnostics, uninstall. |
| Acceptance criteria | Artifacts exist; checksums include artifacts; installed app launches; uninstall removes binaries while preserving user data as intended. |
| Test criteria | Record artifact names, SHA256 file, install path, launch result, health response, uninstall result. |
| Risks | SmartScreen/AV warnings, cache-dependent build, clean-profile differences, code-signing absence. |
| Current status | Packaging smoke PASS; clean install/uninstall PENDING. |

### 6.11 Landing Page

| Field | Plan |
| --- | --- |
| Objective | Verify static landing page build and release CTA behavior. |
| Use case | Visitor opens landing page and downloads latest Windows release. |
| Expected behavior | Landing page builds static assets, links to GitHub Releases latest, and uses safe external link attributes. |
| Automated/static | `cd landing; npm run build`; PowerShell assertions against `landing/index.html` and `landing/package.json` |
| Integration | Verify deploy output contains `index.html`, `styles.css`, `script.js`, `banner.png`. |
| E2E/manual | Open built/deployed page in browser, click CTA, verify GitHub Releases latest opens. |
| Acceptance criteria | Static build has all expected assets; CTA link is correct; sections render correctly. |
| Test criteria | Record build command, generated files, URL checked, and browser result. |
| Risks | Placeholder Vercel URL remains in README, release link changes, missing asset after deploy. |
| Current status | Static build PASS; deployed browser check PENDING until deploy URL exists. |

### 6.12 Security and Same-Origin Guard

| Field | Plan |
| --- | --- |
| Objective | Verify baseline local-app security guardrails. |
| Use case | App rejects unsafe cross-origin or invalid route usage. |
| Expected behavior | Same-origin guard and static security checks continue to pass. |
| Automated tests | `tests/test_p1_security_static.py`, `tests/test_same_origin_guard.py`, `tests/test_frontend_popup_global.py` |
| Integration/E2E | Attempt invalid origin request in local dev session if needed. |
| Acceptance criteria | Existing guard tests pass; no unsafe external navigation introduced. |
| Test criteria | Record pytest output and any manual invalid-origin result. |
| Risks | Desktop/local assumptions may hide browser-origin regressions. |
| Current status | Automated PASS through full suite. |

### 6.13 Internationalization and Rendering

| Field | Plan |
| --- | --- |
| Objective | Verify EN/VI rendering paths and user-facing copy remain usable. |
| Use case | User switches or receives localized UI strings. |
| Expected behavior | Templates render without missing critical text and do not break layout. |
| Automated tests | `tests/test_i18n_render.py` |
| E2E/manual | Open key pages in Electron/browser and inspect visible EN/VI strings where supported. |
| Acceptance criteria | Key routes render; no obvious untranslated critical controls in target language. |
| Test criteria | Record pages checked and language state. |
| Risks | Compiled translation artifacts may be generated locally; do not commit generated `.mo` unless explicitly intended. |
| Current status | Automated PASS; visual language smoke PENDING. |

## 7. Integration Test Plan by Boundary

| Boundary | Coverage target | Existing proof | Next integration expansion |
| --- | --- | --- | --- |
| Flask routes -> core services | Extract, save/edit, history, AI, copy, diagnostics | Existing pytest route tests | Add route-level regression only when a bug is found. |
| Core -> Selenium/browser | Extract, submit, copy | Unit/mocked tests plus prior backend smoke | Live controlled forms for DOM behavior. |
| UI -> Flask routes | Configure, submit, diagnostics, copy UI | UI route/static tests | Browser/Electron E2E smoke. |
| Electron -> backend sidecar | Backend lifecycle and port | Static/module smoke | Interactive launch/close process cleanup. |
| Packaging -> Electron/backend resources | Sidecar inclusion and installer generation | Packaging smoke | Clean profile install/uninstall. |
| Landing -> releases | Static assets and CTA | Static build/assertions | Deployed browser CTA check. |
| Harness/GitNexus -> repo state | Matrix and index health | Harness query, CLI status | Resolve MCP FTS warning outside current session. |

## 8. E2E Scenario Matrix

| ID | Scenario | Preconditions | Steps | Expected evidence | Status |
| --- | --- | --- | --- | --- | --- |
| E2E-001 | Source backend health and diagnostics | Python venv ready | Start `wsgi.py` with `GOOGLE_FORM_TOOL_NO_BROWSER=1`; call `/healthz`; call `/diagnostics/runtime` | Health JSON and diagnostics mode/path fields | Ready; previously PASS |
| E2E-002 | Electron source launch | Node deps installed | Run `npm run electron:dev`; verify app window; open diagnostics; close app | Screenshot/notes, health response, no orphan process | PENDING |
| E2E-003 | Extract controlled form | Safe public test form | Paste `GF-SMOKE-01-basic`; extract; compare preview to source | Title/question/page counts | PENDING |
| E2E-004 | Configure valid/invalid answers | Extracted form | Try invalid probabilities; then valid config | Rejection message and successful save/proceed | PENDING |
| E2E-005 | Tiny direct submit | Controlled form and explicit approval | Submit 1 response with 1 thread and safe delay | App status/history and response count before/after | PENDING |
| E2E-006 | Prefill URL flow | Controlled prefill form | Generate URL; open; verify fields; optionally submit once | URL shape and populated fields | PENDING |
| E2E-007 | History persistence | Saved test form | Restart app; verify saved form/history remains | Before/after visible counts | PENDING |
| E2E-008 | Form copy preview/apply | Controlled source and target edit form | Preview copy; apply supported operations only | Warning list and target verification | PENDING |
| E2E-009 | Packaged backend health | Packaging artifacts exist | Start `dist\GoogleFormTool\GoogleFormTool.exe`; call health/diagnostics | `mode: frozen`, health ok | Ready; previously PASS |
| E2E-010 | Clean installer smoke | Clean Windows profile/VM | Install; launch; check health; uninstall | Install/launch/uninstall notes | PENDING |
| E2E-011 | AI provider live smoke | Non-production API key | Configure key; request bounded answer | Redacted provider/model/status/result | PENDING |
| E2E-012 | Landing deployed page | Deploy URL available | Open URL; click CTA; verify sections/assets | Browser notes and target URL | PENDING |

## 9. Execution Order

### Phase 0: Baseline Guard

1. Confirm branch: `git status --short --branch`.
2. Confirm no unrelated local changes.
3. Run Harness matrix query.
4. Run full pytest.
5. Run GitNexus CLI status and analyze if stale.

Exit criteria: all local baseline checks pass or any failure is recorded with root cause and status.

### Phase 1: Existing Automated Coverage

1. Run full pytest once.
2. If failing, isolate with targeted test file.
3. Do not fix unrelated failures unless they block the selected test objective.
4. Record exact command, environment, and result.

Exit criteria: current automated status is known and recorded.

### Phase 2: Static and Integration Smoke

1. Run Electron syntax checks.
2. Run Node backend module smoke.
3. Run Electron builder config smoke.
4. Run landing build/static assertions.
5. Run source backend health smoke.
6. Run packaged backend health smoke only if packaging artifacts exist or packaging smoke is being run.

Exit criteria: static/platform integration status is known.

### Phase 3: Controlled Browser/Desktop E2E

1. Prepare disposable Google Forms.
2. Start source backend or Electron dev.
3. Run extract -> configure -> submit/pre-fill flows with tiny safe settings.
4. Verify history/status/diagnostics after each run.
5. Clean up only test-owned data.

Exit criteria: each E2E scenario has PASS/PENDING/FAIL with evidence.

### Phase 4: Packaging and Installer

1. Run `.\scripts\package-windows.ps1`.
2. Verify generated artifacts and checksums.
3. Move to clean Windows profile/VM.
4. Install, launch, check diagnostics, uninstall.

Exit criteria: package generation and clean install behavior are separately recorded.

### Phase 5: External Provider and Release Surface

1. Configure non-production AI key.
2. Run bounded AI provider smoke.
3. Verify landing deploy URL once available.
4. Verify GitHub Releases latest CTA and downloadable installer availability.

Exit criteria: provider/deploy behavior is verified or remains PENDING with reason.

## 10. Evidence Template

Use this format for every manual or semi-manual test entry.

```md
### Test Evidence: <ID> <Name>

- Date/time:
- Branch/commit:
- Environment:
- Preconditions:
- Command(s):
- Test data:
- Steps performed:
- Expected result:
- Actual result:
- Result: PASS | FAIL | PENDING
- Artifacts/notes:
- Cleanup performed:
- Follow-up:
```

## 11. Failure Triage Rules

| Failure type | Immediate action | Follow-up |
| --- | --- | --- |
| Automated test regression | Re-run targeted test; inspect diff and recent changes | Fix only if related to selected scope. |
| Google Forms DOM failure | Confirm with controlled form and browser version | Create reliability story before runtime fix. |
| Driver/browser lifecycle leak | Capture process list before/after | Run GitNexus impact before editing Selenium lifecycle code. |
| AI provider failure | Check key, quota, provider status, request shape | Do not commit secrets; record redacted evidence. |
| Installer failure | Capture installer log/error and clean profile state | Separate packaging build issue from install/runtime issue. |
| MCP/GitNexus warning | Verify CLI status and run analyze/force analyze | Treat MCP FTS as PENDING until fresh session or index inspection proves resolution. |

## 12. Definition of Done for Test Campaign

The detailed test campaign can be considered complete only when:

- Every row in `docs/TEST_MATRIX.md` has current unit/integration evidence recorded.
- Every E2E/manual column is either PASS with direct evidence or PENDING with a concrete blocker and next step.
- Live submission tests use only controlled forms and tiny safe counts.
- AI provider checks use non-production credentials and redacted evidence.
- Clean installer smoke is run on a clean Windows profile/VM.
- Generated artifacts are removed or left untracked intentionally.
- `mcp__gitnexus.detect_changes(scope="all")` confirms expected scope before any commit.
- Final report links to commands, environment, results, pending items, and risks.

## 13. Immediate Next Steps

1. Create or provide disposable Google Form URLs for `GF-SMOKE-01` through `GF-SMOKE-05`.
2. Run `git status --short --branch` and `.\.venv\Scripts\python.exe -m pytest -q` before manual E2E.
3. Run `npm run electron:dev` and execute E2E-002 through E2E-007 with tiny safe data.
4. Run `.\scripts\package-windows.ps1`, then perform clean profile/VM installer smoke.
5. Provide a non-production AI key for E2E-011.
6. Re-check GitNexus MCP FTS in a repaired or fresh MCP environment.
7. Update `docs/PROJECT_REFACTOR_AUDIT.md` only when new evidence is collected.

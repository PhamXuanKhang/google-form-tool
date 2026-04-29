# Beta Task Instruction Packs - Google Form Automation Tool

Generated: 2026-04-29
Role: Chu thau / Contractor
Target: Ship internal beta with prefill-link submission as the preferred mode.

## Project Context

Working directory:

```text
D:\02_projects\tools\google_form_automation_tool
```

Current stack:

- Flask 3.1, Selenium 4.32, TinyDB, Pydantic 2.11, vanilla JS/Jinja2, pytest.
- Current flow: extract Google Form DOM -> configure answers -> submit by DOM filling -> monitor status/history.
- Beta decision: prioritize prefill-link submission, but do not require normal users to manually paste a prefill link.
- Fallback decision: only ask user for prefill link if extractor cannot derive `entry.<id>` metadata from Google Forms DOM.

Current relevant files:

- `app/models.py`
- `app/main_routes.py`
- `app/core/form_extractor.py`
- `app/core/form_processor.py`
- `app/core/form_submitter.py`
- `app/static/js/form_filling/*.js`
- `app/templates/form_filling.html`
- `tests/`
- `.env.example`
- `config.py`
- `docs/beta-test-runbook.md`

Reference implementation idea from old project:

- `D:\02_projects\tools\google-form-tool\manage_data.py`: generates Google Forms prefill URLs from `entry.<id>` params.
- `D:\02_projects\tools\google-form-tool\fill_by_prefill_link.py`: opens generated URLs and clicks Next/Submit.

## Task Graph

```text
TIP-001 Beta Test Config
  -> TIP-002 Entry Metadata Extraction
      -> TIP-003 Prefill Link Generator
          -> TIP-004 Prefill Submission Backend
              -> TIP-005 Frontend Mode + Unsupported Popup
                  -> TIP-006 Inline AI Text Generation
                      -> TIP-007 Verification + Beta Docs
```

Do not run later TIPs before their dependencies are DONE unless Chu thau explicitly approves.

## Global Builder Rules

1. Implement exactly the assigned TIP.
2. Keep changes surgical.
3. Do not remove existing DOM-fill submission; prefill-link mode should coexist until verified.
4. Do not introduce a new frontend framework.
5. Do not commit `.env`, runtime `db.json`, logs, or real API keys.
6. Run the specified tests and report exact command output summary.
7. If the real Google Form test URL is missing, mark real integration checks as `UNTESTED - missing TEST_GOOGLE_FORM_URL`, not DONE.

## Completion Report Format

After each TIP, report:

```markdown
## COMPLETION REPORT - TIP-XXX

**STATUS:** DONE / PARTIAL / BLOCKED

**FILES CHANGED:**
- Created:
- Modified:

**TEST RESULTS:**
- Commands run:
- Acceptance criteria:

**ISSUES DISCOVERED:**
- Severity - description - suggestion

**DEVIATIONS FROM SPEC:**
- What - why - impact

**SUGGESTIONS FOR CHU THAU:**
- Observation - recommendation
```

---

# TIP-001: Beta Test Config And Real Form Fixture

## HEADER

- TIP-ID: TIP-001
- Project: Google Form Automation Tool
- Module: Config / Tests / Docs
- Depends on: None
- Priority: P0
- Estimated effort: 30-45 minutes

## CONTEXT

- Working directory: `D:\02_projects\tools\google_form_automation_tool`
- Key files:
  - `.env.example`
  - `config.py`
  - `tests/conftest.py`
  - `README.md`
  - `docs/beta-test-runbook.md`
- Current issue:
  - Real integration test has a hardcoded sample form URL in `tests/conftest.py`.
  - Homeowner wants a configurable test form link.

## TASK

Add a configurable test form URL for beta/integration testing.

## SPECIFICATIONS

1. Add `TEST_GOOGLE_FORM_URL` to `.env.example`.
2. Add `TEST_GOOGLE_FORM_URL` to `Config` in `config.py`.
3. Update the `sample_form_url` fixture in `tests/conftest.py`:
   - Prefer `Config.TEST_GOOGLE_FORM_URL` when set.
   - Keep the current hardcoded sample URL as fallback.
4. Update docs:
   - README test section should mention setting `TEST_GOOGLE_FORM_URL` for the homeowner's real test form.
   - `docs/beta-test-runbook.md` should mention where to put the test URL.
5. Do not print or expose `SECRET_KEY` or Gemini API keys.

## ACCEPTANCE CRITERIA

Given: `.env` contains `TEST_GOOGLE_FORM_URL=https://docs.google.com/forms/...`
When: the builder runs `.\venv\Scripts\python.exe -m pytest -m integration -q`
Then: the integration fixture uses that URL.

Given: `.env` does not contain `TEST_GOOGLE_FORM_URL`
When: the builder runs `.\venv\Scripts\python.exe -m pytest -m integration -q`
Then: the existing fallback sample URL is used.

Given: normal unit tests are run
When: the builder runs `.\venv\Scripts\python.exe -m pytest`
Then: unit tests still pass.

## CONSTRAINTS

- Do not modify `.env`.
- Do not require the test URL for unit tests.
- Do not add new dependencies.

## REPORT FORMAT

Use the Completion Report format above.

---

# TIP-002: Explicit Entry Metadata Extraction

## HEADER

- TIP-ID: TIP-002
- Project: Google Form Automation Tool
- Module: Models / Extractor / Tests
- Depends on: TIP-001
- Priority: P0
- Estimated effort: 60-90 minutes

## CONTEXT

- Key files:
  - `app/models.py`
  - `app/core/form_extractor.py`
  - `app/core/form_processor.py`
  - `tests/test_form_extractor.py`
  - `tests/test_form_processor.py`
- Current behavior:
  - `Question.question_id` currently stores the raw Google Forms entry number as a string.
  - Prefill URLs need full params like `entry.123456=value`.
- Desired behavior:
  - Store explicit prefill metadata while preserving backwards compatibility.

## TASK

Add explicit `entry_id` metadata to extracted questions.

## SPECIFICATIONS

1. Add an optional field to `Question`:

```python
entry_id: Optional[str] = None
```

2. In `FormExtractor._extract_data_from_params()`:
   - Keep `question_id` as the current raw ID string, because existing DOM selectors/tests may rely on it.
   - Set `entry_id` to `entry.<raw_id>` for every extracted question that has an entry ID.
   - For grid questions, set each row's `entry_id` to `entry.<row_entry_id>`.
   - For the default email pseudo-question `q_email`, set `entry_id=None` unless Google provides a real entry ID.
3. Ensure old stored forms without `entry_id` still load from TinyDB.
4. Add helper behavior where needed:
   - Code that needs prefill params should prefer `question.entry_id`.
   - If `question.entry_id` is missing and `question.question_id` is numeric, derive `entry.<question.question_id>` as fallback.
5. Update tests:
   - Unit test model load with missing `entry_id`.
   - Extractor test asserts real extracted questions include `entry_id` starting with `entry.` when applicable.

## ACCEPTANCE CRITERIA

Given: a newly extracted normal question
When: the form is serialized to JSON
Then: the question includes `entry_id: "entry.<number>"`.

Given: an old stored form without `entry_id`
When: `StorageService._load_form()` loads it
Then: validation does not fail.

Given: a grid question with multiple row entries
When: extraction completes
Then: each generated row question has its own `entry_id`.

Given: tests are run
When: `.\venv\Scripts\python.exe -m pytest`
Then: all unit tests pass.

## CONSTRAINTS

- Do not rename `question_id`.
- Do not break DOM-fill mode.
- Do not migrate TinyDB manually unless required by tests.

## REPORT FORMAT

Use the Completion Report format above.

---

# TIP-003: Prefill Link Generator Service

## HEADER

- TIP-ID: TIP-003
- Project: Google Form Automation Tool
- Module: Core / Tests
- Depends on: TIP-002
- Priority: P0
- Estimated effort: 90-120 minutes

## CONTEXT

- Key files:
  - `app/core/form_processor.py`
  - `app/models.py`
  - New file allowed: `app/core/prefill_link_generator.py`
  - `tests/`
- Reference:
  - `D:\02_projects\tools\google-form-tool\manage_data.py`
- Current gap:
  - App can generate response dictionaries, but cannot convert them into Google Forms prefill URLs.

## TASK

Create a reusable service that converts a `Form` and response dictionaries into Google Forms prefill URLs.

## SPECIFICATIONS

1. Create `app/core/prefill_link_generator.py`.
2. Implement a small class or functions. Suggested API:

```python
class PrefillLinkGenerator:
    def __init__(self, form: Form):
        ...

    def build_prefill_url(self, responses: Dict[str, Any]) -> str:
        ...

    def build_prefill_urls(self, responses_list: List[Dict[str, Any]]) -> List[str]:
        ...
```

3. Base URL rules:
   - Accept stored form URL from `form.url`.
   - Normalize to a Google Forms `/viewform` URL.
   - Preserve form ID path.
   - Add `usp=pp_url`.
   - If query params already exist, replace only generated answer params and avoid duplicated answer params.
4. Entry mapping rules:
   - Response keys may be either:
     - raw `question_id`, e.g. `"123456789"`
     - full `entry_id`, e.g. `"entry.123456789"`
   - Generator should map both to the right `entry.<id>`.
   - Prefer `Question.entry_id` from the extracted form.
5. Value encoding rules:
   - Text/date/time/email values become one query param.
   - Multiple choice/dropdown/linear scale become one query param.
   - Checkbox values may produce repeated query params with the same `entry.<id>`.
   - Empty string, `None`, and empty list are skipped.
6. Unsupported values:
   - Nested objects should raise a clear `ValueError`.
   - Missing entry metadata should raise a clear `ValueError` naming the question.
7. Add focused unit tests:
   - single text field
   - multiple choice
   - checkbox repeated params
   - response keyed by raw question ID
   - response keyed by full entry ID
   - skip empty values
   - clear error when no entry mapping exists

## ACCEPTANCE CRITERIA

Given: a form with `entry_id="entry.111"` and response `{"111": "Alice"}`
When: `build_prefill_url()` runs
Then: the URL contains `entry.111=Alice` encoded correctly.

Given: a checkbox response `{"111": ["A", "B"]}`
When: `build_prefill_url()` runs
Then: the URL contains two `entry.111=` params.

Given: response has `None` or `""`
When: `build_prefill_url()` runs
Then: that answer is omitted from the URL.

Given: unit tests are run
When: `.\venv\Scripts\python.exe -m pytest`
Then: all tests pass.

## CONSTRAINTS

- Do not use ad hoc string concatenation for query encoding when `urllib.parse` can do it safely.
- Do not remove old DOM-fill code.
- Do not add external dependencies.

## REPORT FORMAT

Use the Completion Report format above.

---

# TIP-004: Prefill Submission Backend

## HEADER

- TIP-ID: TIP-004
- Project: Google Form Automation Tool
- Module: FormSubmitter / Routes / Tests
- Depends on: TIP-003
- Priority: P0
- Estimated effort: 120-180 minutes

## CONTEXT

- Key files:
  - `app/core/form_submitter.py`
  - `app/main_routes.py`
  - `app/core/prefill_link_generator.py`
  - `tests/test_form_submitter.py`
  - `tests/test_submission_persistence.py`
- Current behavior:
  - `/start_submission` always uses DOM-fill mode.
  - `FormSubmitter._submit_single_form()` fills fields directly.
- Desired beta behavior:
  - Prefer prefill-link mode.
  - Keep DOM-fill as fallback/debug mode.

## TASK

Add backend support for `submission_mode="prefill_link"` and make it the default mode for beta.

## SPECIFICATIONS

1. Route request:
   - `/start_submission` accepts optional `submission_mode`.
   - Valid values: `prefill_link`, `dom_fill`.
   - Default: `prefill_link`.
   - Reject unknown values with HTTP 400 and clear error.
2. Response preparation:
   - Data-driven mode: use `responses_list` directly.
   - AI/single response mode: use provided `responses`.
   - Manual/random mode: generate enough responses using `FormProcessor.generate_random_responses()` for `num_submissions`.
3. Prefill URL generation:
   - Use `PrefillLinkGenerator` from TIP-003.
   - Generate one URL per submission.
4. Submitter behavior:
   - Add a method for opening a prefilled URL and clicking through Google Form pages until Submit.
   - Suggested method names:

```python
submit_prefilled_urls(...)
_submit_prefilled_url(driver, url)
```

5. Success detection:
   - Treat submission as success if confirmation text appears OR URL changes to a submitted/response state.
   - Keep existing text matching for English/Vietnamese.
   - Add a timeout and clear logs for failures.
6. Stop behavior:
   - Respect existing `stop_flag`.
   - Do not start extra submissions after stop.
7. Status/history:
   - `Submission` history should work exactly like current mode.
   - Status endpoint shape should remain unchanged.
8. Tests:
   - Mock generator and driver for route tests.
   - Test default mode is `prefill_link`.
   - Test explicit `dom_fill` still calls old path.
   - Test invalid mode returns 400.
   - Test prefill mode records submission history.

## ACCEPTANCE CRITERIA

Given: `/start_submission` is called without `submission_mode`
When: request is valid
Then: backend uses prefill-link mode.

Given: `/start_submission` is called with `submission_mode="dom_fill"`
When: request is valid
Then: backend uses current DOM-fill behavior.

Given: `submission_mode="unknown"`
When: `/start_submission` is called
Then: route returns 400 with a clear error.

Given: prefill mode finishes
When: `/submission_history/<form_id>` is called
Then: the new batch appears in history.

Given: tests are run
When: `.\venv\Scripts\python.exe -m pytest`
Then: all unit tests pass.

## CONSTRAINTS

- Do not remove current DOM-fill implementation.
- Do not change `Submission` model unless absolutely necessary.
- Do not spawn one Chrome process per URL if an existing thread can reuse a driver.
- Keep batch limits: max 500 submissions and max 10 threads.

## REPORT FORMAT

Use the Completion Report format above.

---

# TIP-005: Frontend Submission Mode And Unsupported Feature Popup

## HEADER

- TIP-ID: TIP-005
- Project: Google Form Automation Tool
- Module: Frontend / Routes
- Depends on: TIP-004
- Priority: P1
- Estimated effort: 90-120 minutes

## CONTEXT

- Key files:
  - `app/templates/form_filling.html`
  - `app/static/js/form_filling/main.js`
  - `app/static/js/form_filling/navigation.js`
  - `app/static/js/form_filling/question_config.js`
  - `app/static/js/form_filling/submission.js`
  - `app/translations/*/LC_MESSAGES/messages.po`
- Product decision:
  - Prefill-link mode should be the normal beta path.
  - Unsupported features should not silently fail.

## TASK

Wire the frontend to submit using prefill-link mode by default and show "developing soon" popup for unsupported features.

## SPECIFICATIONS

1. Submission settings:
   - `getFormSettings()` should include `submission_mode: "prefill_link"` by default.
   - If a small debug selector is added, default must still be `prefill_link`.
2. Unsupported feature detection:
   - Detect extracted questions with unsupported beta types:
     - `rank`
     - `file_upload`
     - `rating` if no stable submit support exists
     - missing `entry_id` when prefill mode is selected
   - Show popup:

```text
Tinh nang nay dang duoc phat trien va se co trong ban cap nhat tiep theo.
```

3. Behavior:
   - If unsupported question blocks prefill mode, prevent starting submission and show a clear popup naming the issue.
   - Do not block extract/preview.
   - DOM-fill debug mode may still be available for developer testing if already supported.
4. Fallback guidance:
   - If missing entry metadata, show a clear message that a future fallback may ask for a prefill link.
   - Do not add a separate prefill-link config panel unless TIP-004 cannot work without it.
5. i18n:
   - Add user-facing strings to translation files if the surrounding file already uses i18n.

## ACCEPTANCE CRITERIA

Given: extracted form contains only supported question types and entry IDs
When: user starts automation
Then: request body includes `submission_mode: "prefill_link"`.

Given: extracted form contains `rank`
When: user tries to start automation
Then: submission is blocked with the developing-soon popup.

Given: a question is missing entry metadata
When: user tries prefill mode
Then: submission is blocked with a clear popup.

Given: unit tests are run
When: `.\venv\Scripts\python.exe -m pytest`
Then: existing backend tests still pass.

## CONSTRAINTS

- Do not create a new full configuration screen for prefill links.
- Do not remove file upload answer data mode.
- Keep existing 4-step UX.

## REPORT FORMAT

Use the Completion Report format above.

---

# TIP-006: Inline AI Text Generation In Main Configuration

## HEADER

- TIP-ID: TIP-006
- Project: Google Form Automation Tool
- Module: AI / Frontend / Routes
- Depends on: TIP-005
- Priority: P2
- Estimated effort: 120-180 minutes

## CONTEXT

- Key files:
  - `app/core/ai_responder.py`
  - `app/main_routes.py`
  - `app/static/js/form_filling/question_config.js`
  - `app/static/js/form_filling/main.js`
  - `app/templates/form_filling.html`
- Current behavior:
  - AI Generate is a separate answer method section.
- Desired behavior:
  - AI should be integrated into each text question's normal config.

## TASK

Move AI generation into the main question configuration flow for text-like questions.

## SPECIFICATIONS

1. Text-like questions:
   - Apply inline AI generation to:
     - `input_text`
     - `textarea`
   - Optional if simple and safe:
     - `input_email` can keep deterministic email generator; do not force AI for email.
2. UI:
   - In each text-like question card, keep the existing answer generator dropdown.
   - Add/keep `AI Generate` as an option in that dropdown.
   - When selected and user clicks Generate:
     - If API key is available, call backend and fill the textarea.
     - If API key is missing, show popup/modal asking user to enter API key.
3. API key handling:
   - Store user-provided key in localStorage as current code does.
   - Do not store API key in backend DB.
   - Do not require separate AI answer method tab.
4. Backend:
   - Reuse existing `/generate_response` or add a narrow endpoint for one question if cleaner.
   - Do not generate AI answers for non-text option questions in this TIP.
5. Existing AI section:
   - Either remove/hide the separate AI answer method from beta UI, or leave it only if it does not confuse the main flow.
   - Preferred: integrate into main flow and avoid requiring a separate tab/mode.
6. Error handling:
   - Invalid key: clear popup.
   - Generation failure: clear popup and keep existing manual answers unchanged.

## ACCEPTANCE CRITERIA

Given: a text question card and no API key
When: user selects `AI Generate` and clicks Generate
Then: app prompts for API key without leaving Step 2.

Given: a valid API key
When: user generates text for one question
Then: generated answers appear in that question's textarea.

Given: a multiple choice question
When: Step 2 renders
Then: AI Generate is not offered for that option question in this TIP.

Given: user saves manual configuration
When: `/save_edit` receives edits
Then: AI-generated text is saved the same way as manually typed text.

Given: tests are run
When: `.\venv\Scripts\python.exe -m pytest`
Then: all unit tests pass.

## CONSTRAINTS

- Do not send API key to logs.
- Do not store API key in TinyDB.
- Do not require a new dependency.
- Do not redesign the whole Step 2 UI.

## REPORT FORMAT

Use the Completion Report format above.

---

# TIP-007: Verification, Real Form Smoke Test, And Beta Docs

## HEADER

- TIP-ID: TIP-007
- Project: Google Form Automation Tool
- Module: QA / Docs / Test Runbook
- Depends on: TIP-006
- Priority: P0 for verification, P2 for doc polish
- Estimated effort: 90-150 minutes

## CONTEXT

- Key files:
  - `docs/beta-test-runbook.md`
  - `README.md`
  - tests added by earlier TIPs
- Goal:
  - Verify the whole beta flow against the homeowner's test form.

## TASK

Run full beta verification and update docs with exact pass/fail instructions.

## SPECIFICATIONS

1. Automated tests:
   - Run unit tests:

```powershell
.\venv\Scripts\python.exe -m pytest
```

   - Run integration extract:

```powershell
.\venv\Scripts\python.exe -m pytest -m integration -q
```

2. Manual smoke tests using `TEST_GOOGLE_FORM_URL`:
   - Extract test form.
   - Manual config text and option questions.
   - Submit 2-3 responses with `submission_mode=prefill_link`, 1 thread.
   - Verify Google Form actual response count increases.
   - Verify app submission history stores the batch.
3. Detailed cases:
   - Text input
   - Paragraph
   - Email
   - Multiple choice
   - Checkbox
   - Dropdown
   - Linear scale
   - Date
   - Time
   - Unsupported type popup
4. Update `docs/beta-test-runbook.md`:
   - Add final exact steps for prefill-link mode after implementation.
   - Add expected request payload shape if useful.
   - Add a "paste result here" block for every manual test.
5. If a case cannot be tested:
   - Mark it clearly as `UNTESTED`.
   - Explain why.

## ACCEPTANCE CRITERIA

Given: unit tests are run
When: command finishes
Then: all selected unit tests pass.

Given: integration extract is run outside sandbox with valid Chrome paths
When: command finishes
Then: integration extract passes.

Given: prefill-link smoke submission with 2-3 rows
When: automation finishes
Then: Google Form response count increases by the expected number.

Given: unsupported question type is present
When: user tries to submit
Then: app shows the developing-soon popup and does not silently fail.

Given: docs are opened
When: homeowner follows the beta runbook
Then: each test has clear input, expected output, and a place to paste actual output.

## CONSTRAINTS

- Do not fabricate manual test results.
- Do not mark real form submission PASS without checking Google Form response count.
- Do not commit `.env`.

## REPORT FORMAT

Use the Completion Report format above.


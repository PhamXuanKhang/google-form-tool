# Beta Debug Phase - Before Next Beta Test

Generated: 2026-04-29
Role: Chu thau / Contractor
Purpose: fix all issues reported during beta-test-runbook manual testing before the next beta attempt.

## Current Status

Automated baseline before this debug phase:

```text
pytest -q                    -> 122 passed, 1 deselected
pytest -m integration -q     -> 1 passed against TEST_GOOGLE_FORM_URL
```

Manual beta is NOT ready yet.

Reasons:

1. Inline AI key validation fails with Gemini model error.
2. Start Automation is blocked by `rank` even though the user expects the rest of the form to submit.
3. Some frontend blocking/warning paths were previously silent because popup wiring was incomplete.
4. Manual config UX still has confusing/incorrect behavior for email/date/time generators.
5. The real prefill submit smoke test has not been completed with Google Form response count verification.

## Evidence From Manual Beta Report

### E-001 - Manual config unclear / validation uncertain

User feedback:

```text
hầu hết đều ok, nhưng không biết validation có chạy không
cho 1 số câu hỏi mà user cho nhiều câu hơn...
```

Interpretation:

- Step 2 does not clearly explain whether multiline text answers are an answer pool or one answer per submission.
- There is no visible validation summary before Step 3.
- Current helper text for email says "Should match form count", which conflicts with how text answer pools currently work.

### E-002 - Email auto generator not usable

User feedback:

```text
Question có emails không dùng được auto generate email.
```

Potential causes:

- `input_email` cards use a separate email-generator UI path, unlike text cards.
- The generated emails may be blocked later by prefill compatibility if the question is the `q_email` pseudo-question.
- Actual extracted `input_email` questions with real `entry_id` should be supported, but the UI must make that clear.

### E-003 - Inline AI popup appears, but validation/generation fails

User feedback:

```text
popup yêu cầu nhập api key nhưng thực ra cũng không hoạt động
POST /validate_api_key HTTP/1.1 400
```

New concrete error:

```text
API key validation failed: 404 models/gemini-1.5-flash is not found for API version v1beta,
or is not supported for generateContent. Call ListModels to see the list of available models
and their supported methods.
```

Root cause hypothesis:

- `AIResponder` hardcodes `gemini-1.5-flash`.
- The installed Google Generative AI SDK/API version no longer exposes that model name for `generateContent`.
- Validation should not depend on one hardcoded stale model.

### E-004 - Date/time generation is confusing or wrong

User feedback:

```text
Giờ và ngày đang bị tách rời khi bị auto gen,
trong khi hiện tại đang có gen giờ riêng và ngày riêng.
```

Observed code behavior:

- `input_text`, `textarea`, `date`, and `time` share the same generator dropdown.
- Date/time cards currently expose generic options: Name, Phone, Date, Hour, Minute.
- For a Google Forms `time` field, generated value should be `HH:MM`, not just hour or minute.
- For a `date` field, generated value should be `YYYY-MM-DD`.

### E-005 - Start Automation appears to do nothing

User feedback:

```text
ấn vào start submission còn không có tương tác gì với server
```

Confirmed root cause already fixed in current workspace:

- `startFormSubmission()` can be blocked by frontend validator before calling `/start_submission`.
- The validator used `window.showPopup?.(...)`, but `showPopup` was not exposed globally.
- This made frontend blocking appear as "nothing happened".

Current fix already applied:

- `form_extract.js` exposes `window.showPopup = showPopup`.
- `tests/test_frontend_popup_global.py` guards this.

### E-006 - Start is blocked by rank

New user feedback:

```text
Tính năng đáng lẽ ra phải bấm nút được là start thì lại bị hiện thông báo liên quan đến rank:
Tính năng này đang được phát triển và sẽ có trong bản cập nhật tiếp theo. (rank)
và không sử dụng được.
```

Root cause:

- TIP-005 intentionally blocked prefill submit if any unsupported beta type exists.
- The real test form includes a `rank` question.
- Product expectation has changed: unsupported questions should not block the whole form by default.

New desired behavior:

- Start should still work for the supported questions.
- Unsupported questions like `rank` should be skipped or warned, not block the entire batch.
- If a required unsupported question makes Google reject submission, the submitter should report failure through the normal success/fail path, not block before trying.

## Debug Phase Decision

For beta, prefer "submit what is supported, warn about skipped unsupported fields" over "block entire form because one unsupported type exists".

Blocking should be reserved for cases that are guaranteed to create a broken request:

- missing `form_id`
- invalid settings
- no extracted form
- no entry metadata for a question that the backend is about to include
- `q_email` pseudo-question with configured values and no real entry mapping

Unsupported-but-skippable types:

- `rank`
- `file_upload`
- `rating`
- unknown types

These should be skipped in prefill mode unless explicitly implemented.

## Task Graph

```text
DBG-001 Popup + Start Gate Regression Check
  -> DBG-002 Gemini Model Resolution + AI Availability
      -> DBG-003 Inline AI UX/Error Messages
          -> DBG-004 Unsupported Question Skip Strategy
              -> DBG-005 Manual Config UX For Email/Date/Time
                  -> DBG-006 Prefill Submission Observability
                      -> DBG-007 Full Regression + Runbook Update
```

Run in order. Do not start the next beta test until all P0 debug tasks are DONE.

## Global Builder Rules

1. Keep changes surgical.
2. Preserve prefill-link mode as the default.
3. Do not log API keys or full sensitive payloads.
4. Do not remove DOM-fill mode.
5. Do not change the tech stack or add major frontend dependencies.
6. Run `.\venv\Scripts\python.exe -m pytest -q` after each task.
7. If a task needs real Gemini or real Google Form response count, mark that part as MANUAL/UNTESTED unless actually verified.

---

# DBG-001: Popup + Start Gate Regression Check

## HEADER

- ID: DBG-001
- Priority: P0
- Depends on: None
- Files likely involved:
  - `app/static/js/form_filling/form_extract.js`
  - `app/static/js/form_filling/main.js`
  - `tests/test_frontend_popup_global.py`
  - `docs/beta-test-runbook.md`

## TASK

Verify and harden the frontend feedback path so any client-side block before `/start_submission` is visible to the user.

## SPECIFICATIONS

1. Ensure `showPopup` is available as `window.showPopup`.
2. Ensure `showPopup(message, type)` supports at least:
   - `info`
   - `success`
   - `warning`
   - `error`
3. Wrap `window.startFormSubmission` with a defensive `try/catch`:
   - If validator or settings collection throws, show an error popup.
   - Log the error to console for debugging.
   - Do not silently return.
4. Add/keep a regression test proving `window.showPopup = showPopup` exists.
5. Update runbook: when Start does not hit server, check for frontend popup and browser console first.

## ACCEPTANCE CRITERIA

Given: validator blocks submission
When: user clicks `Start Automation`
Then: a visible popup explains the reason.

Given: validator throws unexpectedly
When: user clicks `Start Automation`
Then: a visible error popup appears and no silent failure occurs.

Given: tests are run
When: `pytest -q`
Then: all tests pass.

## REPORT REQUIRED

Completion report must include:

- Whether `window.showPopup` is globally available.
- Whether Start preflight exceptions are visible.
- Test command output.

---

# DBG-002: Gemini Model Resolution + AI Availability

## HEADER

- ID: DBG-002
- Priority: P0
- Depends on: DBG-001
- Files likely involved:
  - `app/core/ai_responder.py`
  - `app/main_routes.py`
  - `config.py`
  - `.env.example`
  - `requirements.txt`
  - `tests/test_ai_text_route.py`

## TASK

Fix Gemini validation/generation so it does not depend on a stale hardcoded model name.

## SPECIFICATIONS

1. Add configurable model support:
   - Add `GEMINI_MODEL` to `.env.example`.
   - Add `Config.GEMINI_MODEL`.
   - `AIResponder` should use `GEMINI_MODEL` if set.
2. Add model fallback resolution:
   - If configured/default model is unavailable, try to select a model that supports `generateContent`.
   - Use `genai.list_models()` when available.
   - Prefer fast text models, but do not hardcode only one stale model.
   - Do not require browsing current Google docs; runtime model listing is the source of truth.
3. Improve errors:
   - `/validate_api_key` should return a user-actionable error if no compatible model is available.
   - Do not echo API key.
   - Log model names/errors without secret values.
4. Preserve tests with mocked AI responder.
5. Add tests for:
   - configured model used when available
   - stale model triggers fallback
   - no model supporting `generateContent` returns clean validation failure
   - error response/log does not include API key

## ACCEPTANCE CRITERIA

Given: API returns `404 model not found` for the configured model
When: validation runs
Then: AIResponder tries an available fallback model supporting `generateContent`.

Given: no compatible model exists
When: `/validate_api_key` is called
Then: route returns 400 with a clear non-secret message.

Given: a valid API key and available model
When: inline AI Generate runs
Then: text answers are generated.

Given: tests are run
When: `pytest -q`
Then: all tests pass.

## MANUAL VERIFICATION

After implementation:

1. Install deps from `requirements.txt`.
2. Start app.
3. Clear browser `localStorage.gemini_api_key`.
4. Click AI Generate on an `input_text` question.
5. Enter valid Gemini key.
6. Expected:
   - key validates
   - answers populate textarea
   - no `gemini-1.5-flash not found` error

## REPORT REQUIRED

Completion report must include:

- Model resolution behavior.
- Whether `GEMINI_MODEL` was added.
- Test output.
- Manual verification status if a real key was available.

---

# DBG-003: Inline AI UX/Error Messages

## HEADER

- ID: DBG-003
- Priority: P1
- Depends on: DBG-002
- Files likely involved:
  - `app/static/js/form_filling/main.js`
  - `app/static/js/form_filling/question_config.js`
  - `app/templates/form_filling.html`
  - translations
  - docs

## TASK

Make inline AI failures understandable during beta.

## SPECIFICATIONS

1. If AI package is missing:
   - Show popup: AI dependency is not installed; run pip install -r requirements.txt.
2. If model is unavailable:
   - Show popup: selected Gemini model is unavailable; check GEMINI_MODEL or API access.
3. If key is invalid:
   - Show popup: API key validation failed.
4. If user cancels key prompt:
   - Show popup: API key required.
5. Do not clear existing textarea contents on any failure.
6. If generation succeeds:
   - Fill exactly `count` lines.
   - Show success toast.
7. Keep key only in localStorage.

## ACCEPTANCE CRITERIA

Given: invalid key
When: user attempts AI Generate
Then: popup explains validation failed and textarea remains unchanged.

Given: valid key
When: user attempts AI Generate
Then: textarea receives generated lines.

Given: page reloads after saved key
When: user clicks Generate again
Then: no prompt appears and saved key is reused.

## REPORT REQUIRED

Completion report must include:

- Manual no-key/invalid-key/valid-key behavior.
- Screenshots or exact popup text if manually tested.
- Test output.

---

# DBG-004: Unsupported Question Skip Strategy

## HEADER

- ID: DBG-004
- Priority: P0
- Depends on: DBG-001
- Files likely involved:
  - `app/static/js/form_filling/prefill_validator.js`
  - `app/static/js/form_filling/main.js`
  - `app/core/form_submitter.py`
  - `app/core/prefill_link_generator.py`
  - `app/core/form_processor.py`
  - `tests/js/test_prefill_validator.mjs`
  - backend tests for prefill submission

## TASK

Change unsupported question handling from "block entire submit" to "warn and skip unsupported fields" for beta.

## SPECIFICATIONS

1. Define unsupported/skippable types in one shared concept:
   - `rank`
   - `file_upload`
   - `rating`
   - `unknown`
2. Frontend behavior:
   - If form contains skippable unsupported types, do NOT block Start.
   - Show a warning popup/toast listing skipped types/questions.
   - Continue to call `/start_submission`.
3. Backend behavior:
   - In prefill mode, filter generated/submitted response dictionaries before building prefill URLs.
   - Remove answers for unsupported/skippable question types.
   - Log a warning summary without sensitive answer values.
4. Keep hard blocks for:
   - `q_email` pseudo-question with submitted values and no real entry mapping
   - truly missing entry metadata for supported question types
5. Return or expose warnings:
   - `/start_submission` response should include warnings if practical.
   - UI should show warnings before or after start.
6. If unsupported required questions cause Google submission failure:
   - Submitter should record failure through normal success/fail counts.
   - Do not pre-block unless required-status is reliably extracted and known.

## ACCEPTANCE CRITERIA

Given: form contains `rank`
When: user clicks Start
Then: frontend shows warning and still sends `/start_submission`.

Given: prefill mode receives responses with `rank`
When: building URLs
Then: `rank` answer is omitted from prefill params.

Given: form contains supported fields plus `rank`
When: submit runs
Then: supported fields are attempted.

Given: q_email has configured values but no entry mapping
When: user clicks Start
Then: frontend still blocks with q_email-specific message.

Given: tests are run
When: `pytest -q`
Then: all tests pass.

## MANUAL VERIFICATION

Use the current real test form with `Test rank`.

Expected after this task:

```text
Click Start Automation:
- warning mentions rank will be skipped
- Network tab shows POST /start_submission
- server logs show submission started
```

Google response count may still fail if Google requires rank; if so, report as submitter/form-required issue, not frontend gate issue.

## REPORT REQUIRED

Completion report must include:

- Which unsupported types are skipped.
- Whether current real test form reaches `/start_submission`.
- Test output.

---

# DBG-005: Manual Config UX For Email, Date, And Time

## HEADER

- ID: DBG-005
- Priority: P1
- Depends on: DBG-004
- Files likely involved:
  - `app/static/js/form_filling/question_config.js`
  - `app/core/form_processor.py`
  - tests for processor/frontend static checks
  - docs

## TASK

Fix confusing manual answer generation for email/date/time.

## SPECIFICATIONS

1. Specialize generator dropdowns by question type:
   - `input_text`: Name, Phone, Generic Text, AI Generate
   - `textarea`: Generic Text, AI Generate
   - `input_email`: Email generator only
   - `date`: Date only
   - `time`: Time only
2. Time generator:
   - Generate `HH:MM`, not separate hour/minute values.
3. Date generator:
   - Generate `YYYY-MM-DD`.
4. Email generator:
   - For real `input_email` questions with numeric/entry metadata, generated emails should be included in prefill mode.
   - For `q_email` pseudo-question without entry, show q_email block only if user tries to submit it.
5. Clarify multiline semantics:
   - Decide and document one behavior:
     - Option A: lines are an answer pool; each submission randomly chooses one.
     - Option B: line N maps to submission N.
   - Current backend behaves like Option A. For this debug phase, keep Option A unless explicitly changing backend.
   - Update helper text so user does not think line count must match submission count except where actually required.
6. Add validation summary before Step 3:
   - Percent fields are 0-100.
   - Multiple-choice/dropdown totals should equal 100.
   - Text/date/time/email line lists may be empty only if fill percentage is 0.

## ACCEPTANCE CRITERIA

Given: a date question
When: user opens generator dropdown
Then: only date-appropriate generator options are shown.

Given: a time question
When: user generates values
Then: generated lines are `HH:MM`.

Given: a real input_email question
When: user clicks email generate
Then: textarea receives valid email lines and prefill mode can include them.

Given: user enters invalid percentages
When: moving to Step 3
Then: visible validation explains what to fix.

Given: tests are run
When: `pytest -q`
Then: all tests pass.

## REPORT REQUIRED

Completion report must include:

- Final semantics for multiline answers.
- Manual verification for email/date/time.
- Test output.

---

# DBG-006: Prefill Submission Observability

## HEADER

- ID: DBG-006
- Priority: P1
- Depends on: DBG-004
- Files likely involved:
  - `app/core/form_submitter.py`
  - `app/main_routes.py`
  - `app/static/js/form_filling/submission.js`
  - logs/tests

## TASK

Make prefill submission debug-visible without exposing sensitive answer data.

## SPECIFICATIONS

1. `/start_submission` response should include:
   - submission mode
   - number of URLs/responses prepared
   - warnings from skipped unsupported fields if available
2. Client should display start response warnings.
3. Server logs should include:
   - form id
   - submission mode
   - total submissions
   - skipped field count/type summary
   - no full prefill URLs by default, because URLs contain answers
4. Optional debug-only behavior:
   - Add a dev-only setting or endpoint to preview first prefill URL redacted.
   - Do not expose full URLs unless explicitly in local debug mode.
5. Success detection:
   - Keep current confirmation text OR URL-change heuristic.
   - Add diagnostic logs when a URL is submitted but success condition fails.

## ACCEPTANCE CRITERIA

Given: user clicks Start
When: route accepts request
Then: UI shows "Started..." plus any warnings.

Given: backend skips rank
When: route starts
Then: response/log mentions skipped rank count but not answer values.

Given: submitter fails to detect success
When: submission ends
Then: logs include enough non-secret context to debug the failure.

## REPORT REQUIRED

Completion report must include:

- Example `/start_submission` response shape.
- Example log lines with secrets omitted.
- Test output.

---

# DBG-007: Full Regression + Runbook Update

## HEADER

- ID: DBG-007
- Priority: P0
- Depends on: DBG-002, DBG-003, DBG-004, DBG-005, DBG-006
- Files likely involved:
  - `docs/beta-test-runbook.md`
  - all tests

## TASK

Run and document the full pre-beta verification after debug fixes.

## REQUIRED AUTOMATED TESTS

```powershell
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe -m pytest -m integration -q
```

## REQUIRED MANUAL TESTS

1. Extract real test form.
2. Manual config:
   - input_text
   - textarea
   - input_email with real entry
   - multiple_choice
   - checkbox
   - dropdown
   - linear_scale
   - date
   - time
   - rank present but skipped warning
3. Start prefill submit:
   - `num_submissions=2`
   - `concurrent_threads=1`
   - response count BEFORE/AFTER checked in Google Form
4. Inline AI:
   - no key
   - invalid/stale model
   - valid key if available
5. q_email gate:
   - no configured q_email: no block
   - configured q_email: block

## ACCEPTANCE CRITERIA

Beta can proceed only when:

- Unit tests pass.
- Integration extract passes.
- Start button reaches server with current real form containing rank.
- Unsupported rank is skipped/warned, not pre-blocking whole submit.
- Google Form response count delta equals app-reported success count for a 2-submission smoke.
- AI key validation no longer fails due stale hardcoded model.
- Date/time/email generators produce valid values.
- Runbook final decision is filled with PASS/FIX/DEFER.

## REPORT REQUIRED

Completion report must include:

```text
Unit tests:
Integration extract:
Start request reached server with rank form: YES/NO
Response count BEFORE:
Response count AFTER:
Delta:
App success/total:
AI validation with real key: PASS/FAIL/UNTESTED
Date/time/email generator: PASS/FAIL
Final recommendation: SHIP INTERNAL BETA / FIX BEFORE BETA / DEFER
```

## Current Contractor Recommendation

Do not run another full beta smoke until DBG-002 and DBG-004 are complete.

Rationale:

- DBG-002 fixes the known Gemini model blocker.
- DBG-004 fixes the current Start Automation blocker on the real test form.


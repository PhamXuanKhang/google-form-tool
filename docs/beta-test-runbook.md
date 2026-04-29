# Beta Test Runbook - Google Form Automation Tool

Muc tieu: giup test nhanh cac luong beta, ghi lai input/output thuc te, va paste ket qua cho Chu thau phan tich tiep.

Ngay test: 
Nguoi test: 
May/OS: 
Chrome path dang dung: 
ChromeDriver path dang dung: 
Google Form test URL: (dat trong `.env` bang bien `TEST_GOOGLE_FORM_URL=https://docs.google.com/forms/d/e/<id>/viewform`; neu de trong, integration test fallback ve sample URL co san trong `tests/conftest.py`)

## 0. Setup Check

Lenh chay:

```powershell
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe -m pytest -m integration -q
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

Dat khi:

- Unit test pass: `76 passed, 1 deselected` hoac khong co test fail moi.
- Integration extract pass: `1 passed, 76 deselected`.
- App mo duoc tai `http://localhost:5000`.
- Neu integration fail vi Chrome crash trong sandbox, chay lai ngoai sandbox/terminal thuong.

Ket qua thuc te (TIP-007 verification):

```text
pytest -q                    -> 121 passed, 1 deselected in 2.77s
pytest -m integration -q     -> 1 passed, 121 deselected in 32.39s
                                (test_extract_form_data_structure against TEST_GOOGLE_FORM_URL real)
run_local.ps1                -> UNTESTED automatically; chay tay tren may homeowner.
```

Danh gia: PASS (automated) / NEEDS REVIEW (run_local manual)

## 1. Extract Form

Input:

- Form URL: link Google Form test co hau het dang cau hoi.

Cach test:

1. Mo `http://localhost:5000/form_filling`.
2. Paste Form URL.
3. Bam `Extract`.
4. Doi preview hien title, description, pages, questions.

Dat khi:

- Preview hien dung title/description.
- Cac cau hoi duoc chia page dung.
- Moi cau hoi hien type hop ly: `input_text`, `textarea`, `multiple_choice`, `checkbox`, `dropdown`, `linear_scale`, `date`, `time`, `input_email`.
- Khong co popup loi Chrome/ChromeDriver.

Can ghi lai:

```text
Form title:
So page:
So cau hoi:
Type nao sai/khong extract duoc:
Screenshot/loi neu co:
```

Danh gia: PASS / FAIL / NEEDS REVIEW

## 2. Manual Configure Answers

Input goi y:

- Text/name: tao 3-5 dong mau.
- Email: tao 3-5 email mau.
- Multiple choice/dropdown: set phan bo tong 100%.
- Checkbox: set tung option 0-100% doc lap.
- Date: dung `YYYY-MM-DD`.
- Time: dung `HH:MM`.

Cach test:

1. Sau khi extract, bam `Next Step`.
2. Chon `Manual Input`.
3. Dien/generate cau tra loi cho cac cau text/email.
4. Set phan tram cho options.
5. Bam `Next Step` de app goi `/save_edit`.

Dat khi:

- Khong co popup `Failed to save manual configuration`.
- Step 3 hien settings.
- Neu quay lai Step 2, UI van co cau hoi va config co the sua tiep.

Can ghi lai:

```text
Question IDs/type nao config OK:
Question IDs/type nao config loi:
Popup/message neu co:
```

Danh gia: PASS / FAIL / NEEDS REVIEW

## 3. File Upload Data-Driven Submission

Input CSV mau:

```csv
entry_or_question_id_1,entry_or_question_id_2
Nguyen Van A,a@example.com
Tran Thi B,b@example.com
```

Luu y: cot CSV hien tai nen dung `question_id` sau khi extract. Neu khong chac `question_id`, lay tu preview JSON/devtools hoac cho Chu thau tao tool export mapping.

Cach test:

1. Chon `File Upload`.
2. Upload file CSV/JSON/XLSX.
3. Doi message `Loaded X response sets`.
4. Sang Step 3, so submissions tu dong bang so row.

Dat khi:

- Upload thanh cong va preview 3 row dau.
- So submissions bang so response rows.
- Backend khong bao unsupported format.

Can ghi lai:

```text
File type:
Rows loaded:
Mapping/cot da dung:
Row nao bi sai/khong load:
```

Danh gia: PASS / FAIL / NEEDS REVIEW

## 4. AI Text Generation Dropdown Gating (TIP-006.1)

Sau khi extract form co du 4 loai cau hoi text-like, kiem tra dropdown
"Answer Type" trong tung card cau hoi tai Step 2:

```text
Cau hoi input_text  -> dropdown CO option "AI Generate"
Cau hoi textarea    -> dropdown CO option "AI Generate"
Cau hoi date        -> dropdown KHONG co option "AI Generate"
Cau hoi time        -> dropdown KHONG co option "AI Generate"
```

Danh gia: PASS / FAIL / NEEDS REVIEW

## 4.1. AI Text Generation

Trang thai mong muon cho beta sap toi:

- AI chi ap dung cho cau text-like: `input_text`, `textarea`, co the them `input_email` neu can.
- Dropdown trong tung cau text co option `AI Generate`.
- Neu user chua nhap API key, hien popup/modal yeu cau nhap API key.
- Sau khi co key, generate va dien cau tra loi vao textarea cua cau do.
- Khong bat user chuyen sang tab/mode rieng.

Test sau khi da implement:

```text
Question text:
API key popup co hien khong:
Output AI co dien vao dung textarea khong:
Output co phu hop cau hoi khong:
```

Danh gia: PASS / FAIL / NEEDS REVIEW / NOT IMPLEMENTED

## 5. Current DOM Fill Submission

Input an toan:

- `Number of submissions`: 2-3
- `Concurrent threads`: 1
- `Minimum delay`: 1
- `Maximum delay`: 2

Cach test:

1. Vao Step 3, dien settings nho.
2. Sang Step 4.
3. Bam `Start Automation`.
4. Theo doi progress, success/fail, elapsed time.
5. Mo Google Form responses de doi chieu so response that.

Dat khi:

- Progress chay tu 0 den 100%.
- Completed = Total.
- Success rate >= 80% voi form don gian.
- Google Form nhan dung so response.
- Submission history co them record.

Can ghi lai:

```text
Settings:
Completed/Total:
Success/Failed:
Success rate:
Google Form actual response count before:
Google Form actual response count after:
Loai cau hoi nao gay fail:
Log/error neu co:
```

Danh gia: PASS / FAIL / NEEDS REVIEW

## 6. Prefill-Link Mode - Real Form Smoke Test

**MUST start with `num_submissions=2-3`, `concurrent_threads=1`.** Increase only after a clean run. Verification requires checking Google Form actual response count, NOT just app status.

### 6.0 Pre-conditions

- `.env` has `TEST_GOOGLE_FORM_URL=<owned-test-form-viewform-url>`.
- Test form is owned by you so you can read response count.
- Chrome/ChromeDriver paths set in `.env`.
- App running at `http://localhost:5000`.

### 6.1 Steps

1. Open `http://localhost:5000/form_filling`.
2. Paste the test form URL → click `Extract`. Confirm Step 1 preview shows title/pages/questions.
3. Open Google Form responses page in another tab. Note **response count BEFORE**.
4. Click `Next Step` → choose `Manual Input` → fill at least one text answer + one option distribution → click `Next Step` → Step 3.
5. Step 3: set `Number of submissions = 2`, `Concurrent threads = 1`, `Minimum delay = 1`, `Maximum delay = 2`. Click `Review and Start`.
6. Step 4: click `Start Automation`. Watch progress to 100%, success/fail, elapsed.
7. Refresh Google Form responses page. Note **response count AFTER**.
8. Open `/submission_history?form_id=<id>` (or app history UI) — confirm a new batch row exists.

### 6.2 Expected request payload (devtools Network -> /start_submission)

```json
{
  "form_id": "f_<deterministic-id>",
  "form_url": "https://docs.google.com/forms/d/e/.../viewform",
  "num_submissions": 2,
  "concurrent_threads": 1,
  "min_delay": 1,
  "max_delay": 2,
  "submission_mode": "prefill_link"
}
```

`submission_mode` MUST be present and equal to `"prefill_link"` — sent explicitly by `getFormSettings()` even though the backend defaults to it (TIP-005).

### 6.3 Acceptance

- App reports `Completed = Total`, success rate >= 80%.
- **Google Form response count increased by exactly the success count** (not by Total - the failed ones must NOT have created responses).
- `/submission_history` lists the new batch with matching `success_rate` and `time_used`.
- Browser visit to one of the prefill URLs (paste manually if you grabbed it from logs) shows fields pre-filled.

### 6.4 Paste result here

```text
Form URL used:
Response count BEFORE:
Response count AFTER:
Delta (AFTER - BEFORE):
App-reported success/total:
App-reported success_rate:
Submission history row appeared: YES/NO
Any error in app log:
```

Danh gia: PASS / FAIL / NEEDS REVIEW / UNTESTED

## 6.1.b Per-question-type matrix

For each type below, configure 1 question of that type (Manual mode), submit 2-3 responses with prefill mode, and check the Google Form response page.

```text
Type             | Configured value(s)         | Response shows correctly? (Y/N)
---------------- | --------------------------- | -------------------------------
input_text       |                             |
textarea         |                             |
input_email      |                             |
multiple_choice  |                             |
checkbox         |                             |
dropdown         |                             |
linear_scale     |                             |
date             | YYYY-MM-DD                  |
time             | HH:MM                       |
unsupported popup (rank present): triggered? Y/N
q_email gate (manual answer typed for default email): popup shown? Y/N
```

Danh gia: PASS / FAIL / NEEDS REVIEW / UNTESTED

## 6.5 Inline AI flow (TIP-006) — only if Gemini API key available

1. Step 2, on a text/textarea card, change `Answer Type` to `AI Generate`.
2. Click `Generate`. With no key in localStorage, expect a popup asking for the key.
3. Cancel once → expect "API key required" popup, no answers generated.
4. Click again → enter a valid key → expect "API key saved" toast → textarea fills with N answers.
5. Reload the page → click Generate again → expect NO popup (key reused from localStorage).

Paste result here:

```text
Popup appeared with no key: Y/N
Cancel produced "API key required": Y/N
Valid key saved + answers populated: Y/N
Reload reused key (no popup): Y/N
Notes/error if any:
```

Danh gia: PASS / FAIL / NEEDS REVIEW / UNTESTED (no API key)

## 6.1. Prefill Compatibility Gate (Frontend)

Su dung sau khi TIP-005 / TIP-005.1 da apply. Co Node.js: bo qua, da co unit test
chay tu dong qua pytest (`tests/test_js_prefill_validator.py`).

Khong co Node tren may homeowner: kiem tra tay nhung case sau truoc khi submit.

```text
Case A - Form binh thuong, du entry: Start Automation -> chay binh thuong.
Case B - Form co cau hoi `rank`:      Start -> popup "developing soon (rank)", khong call backend.
Case C - Cau hoi thieu entry_id:      Start -> popup "missing entry metadata", khong call backend.
Case D - q_email khong cau hinh:      Start -> chay binh thuong, email bi bo qua.
Case E - q_email + manual answers:    Start -> popup "default email field is not supported in prefill-link mode yet".
Case F - q_email + CSV co cot q_email: Start -> popup giong Case E.
Case G - q_email + AI/single response: Start -> popup giong Case E.
```

Danh gia: PASS / FAIL / NEEDS REVIEW

## 7. Unsupported / Later Features

Trong beta, neu gap type/tinh nang chua ho tro, UI nen hien popup:

```text
Tinh nang nay dang duoc phat trien va se co trong ban cap nhat tiep theo.
```

Ap dung truoc cho:

- `rank`
- branching phuc tap chua enumerate duoc het nhanh
- file upload question
- rating neu chua co handler submit on dinh
- other option neu prefill-link mode chua support

Test:

```text
Tinh nang/type:
Popup co hien khong:
User co bi chan submit toan bo form khong:
```

Danh gia: PASS / FAIL / NEEDS REVIEW

## 8. Final Beta Decision

Tong hop:

```text
Setup check:                  PASS (automated unit + integration extract)
Extract:                      PASS (integration extract against TEST_GOOGLE_FORM_URL)
Manual config:                UNTESTED (manual run required)
File upload:                  UNTESTED (manual run required)
AI dropdown gating:           PASS (test_ai_generator_gating, source-level)
Inline AI text generation:    UNTESTED (requires Gemini key)
DOM fill submit:              UNTESTED (legacy path, manual run required)
Prefill-link mode (real form): UNTESTED (requires response-count check by homeowner)
Per-question-type matrix:     UNTESTED (manual run required)
Prefill compatibility gate:   PASS (Node JS suite via pytest, 20 assertions)
Unsupported feature popup:    PASS (covered by gate suite)
q_email gate:                 PASS (covered by gate suite)
History/export:               PASS (test_submission_persistence covers history; UI verify pending)
```

Quyet dinh:

- SHIP INTERNAL BETA
- FIX BEFORE BETA
- DEFER FEATURE

Ghi chu them:

```text
Paste nhan xet, log, screenshot link, form URL test, hoac hanh vi bat thuong o day.
```

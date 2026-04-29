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

Ket qua thuc te:

```text
Paste output o day.
```

Danh gia: PASS / FAIL / NEEDS REVIEW

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

## 4. AI Text Generation

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

## 6. Prefill-Link Mode - Target Beta Flow

Quyet dinh san pham: uu tien prefill-link mode nhung khong bat user tu nhap prefill link neu co the lay entry tu extract.

Target UX:

1. User paste Google Form URL va bam `Extract`.
2. Backend extract luon `entry.<id>` tu Google Forms DOM/data-params.
3. Step 2 dung config hien co: answers, option percentages, file data, AI text.
4. Backend sinh prefill URLs noi bo.
5. Submitter mo tung prefill URL, click Next/Submit, va verify success.

Fallback neu khong lay duoc entry tu DOM:

- Hien popup huong dan user lay prefill link tu Google Form:
  - Mo form owner UI.
  - Bam menu ba cham.
  - Chon `Get pre-filled link`.
  - Dien moi cau hoi mot gia tri mau.
  - Bam `Get link`.
  - Paste link vao app.
- App parse `entry.<id>` tu link va map lai voi cau hoi da extract.

Dat khi:

- User binh thuong khong can nhap prefill link.
- Chi form nao extract entry that bai moi can fallback.
- Distribution tu Step 2 sinh ra dung so link va dung ty le.
- Checkbox co the sinh nhieu value tren cung mot `entry`.
- Other option duoc danh dau la tinh nang sau neu chua implement.

Can ghi lai sau khi implement:

```text
Lay entry tu extract: YES/NO
Neu NO, fallback prefill link co parse duoc khong:
So prefill URLs sinh ra:
Submit thanh cong:
Sai mapping cau hoi nao:
```

Danh gia: PASS / FAIL / NEEDS REVIEW / NOT IMPLEMENTED

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
Setup check:
Extract:
Manual config:
File upload:
AI text generation:
DOM fill submit:
Prefill-link mode:
Unsupported feature popup:
History/export:
```

Quyet dinh:

- SHIP INTERNAL BETA
- FIX BEFORE BETA
- DEFER FEATURE

Ghi chu them:

```text
Paste nhan xet, log, screenshot link, form URL test, hoac hanh vi bat thuong o day.
```

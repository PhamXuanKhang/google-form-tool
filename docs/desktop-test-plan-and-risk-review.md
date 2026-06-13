# Desktop Test Plan and Risk Review

Updated: 2026-06-08

## 1. Context and product direction

Định hướng hiện tại là **desktop/Electron app**, không phải public web app chạy qua localhost cho nhiều user bên ngoài. Vì vậy mức ưu tiên thay đổi:

- **Tạm giảm ưu tiên:** CSRF, login/authentication, hardening web public, rate limit kiểu web server.
- **Tăng ưu tiên:** dọn tiến trình nền, dọn Chrome/ChromeDriver, giới hạn số luồng theo tài nguyên máy, cleanup dữ liệu `%APPDATA%`, random hóa thứ tự điền form để tránh cảm giác lặp.
- **Tình trạng hiện tại:** Core MVP đã test integration với form thật. Form đơn luồng, một đường đi, không rẽ nhánh hiện chạy ổn. Các phần cần test kỹ tiếp là branching, prefill edge cases, parallel execution, cleanup tài nguyên.

Ước lượng theo hướng desktop app: **75-80% cho local desktop MVP**, với điều kiện phải xử lý/verify kỹ issue chạy ngầm và cleanup tài nguyên.

---

## 2. Current priority assessment

| Area | Current assessment | Priority | Notes |
|---|---:|---|---|
| Core extract → configure → submit | Tốt với form đơn giản, single-path | High | Cần test thêm branching/grid/rank/random order. |
| DOM fill business logic | Chạy được basic case, còn edge-case gaps | High | `_fill_question()` cần cải thiện hoặc cảnh báo rõ unsupported. |
| Prefill mode | Có vẻ chạy ổn nhưng chưa test sâu | Medium | Cần test required/branching/special types. |
| Background processes/resource cleanup | Chưa đủ chắc | Critical | Có issue remote báo chạy ngầm/ngốn tài nguyên/dữ liệu rác. |
| Storage | Tạm ổn cho desktop app hiện tại | Low/Medium | Có thể cleanup model sau. |
| Frontend localhost UI | Tạm ổn | Low | Sau chuyển Electron JS có thể làm lại. |
| Security web hardening | Tạm defer | Low | Không phải public web server. |
| Desktop packaging readiness | Cần tập trung | High | Cần test uninstall/data/process cleanup. |

---

## 3. Review `_fill_question()` business logic

Target: `app/core/form_submitter.py`, method `FormSubmitter._fill_question()`.

### 3.1 Current flow

1. `/start_submission` tạo background thread `submission_task`.
2. `FormSubmitter.submit_form()` tạo nhiều worker threads theo `concurrent_threads`.
3. Mỗi worker tạo một Chrome WebDriver.
4. `_submit_single_form()` mở form URL.
5. `_fill_page()` duyệt từng question theo thứ tự trong config.
6. `_fill_question()` điền từng câu theo `question.type`.
7. Click Next hoặc Submit.

### 3.2 Issues found

#### Issue A — Fill order đang cố định, không random

Hiện `_fill_page()` điền theo thứ tự câu hỏi trong form:

```python
for question in page.questions:
    self._fill_question(driver, question)
```

Impact:

- Mỗi lần submit nhìn giống nhau.
- Tạo cảm giác robot/lặp lại.
- User đã quan sát thấy vấn đề này với form thật.

Recommended fix:

- Randomize thứ tự câu hỏi trong từng page.
- Không random thứ tự page.
- Với uploaded data mode, vẫn có thể random thứ tự fill field, nhưng không shuffle thứ tự rows nếu user kỳ vọng row order.

Test:

- Run 10 submissions cùng một form.
- Capture thứ tự gọi `_fill_question()`.
- Expect có ít nhất 2 order khác nhau.

Priority: **High**.

---

#### Issue B — `rank` được generate nhưng DOM fill không làm gì

Trong `FormProcessor` có:

```python
elif q_type == "rank":
    return self._generate_rank_response(question)
```

Nhưng trong `_fill_question()`:

```python
elif question.type == "rank":
    pass
```

Impact:

- Rank bị skip âm thầm.
- Nếu required thì submit fail.
- Nếu optional thì app có thể báo success dù không điền.

Recommended fix:

- Nếu chưa implement drag/drop ranking, phải cảnh báo rõ là unsupported.
- Không nên silent `pass`.

Test:

- Required rank form → fail/warning rõ.
- Optional rank form → warning skipped type.

Priority: **High nếu dùng rank**, Medium nếu chưa support rank.

---

#### Issue C — Multiple choice/checkbox match exact text, dropdown match normalized

Dropdown đã normalize text:

```python
target = self._normalize_button_text(str(response))
matched = [o for o in options if self._normalize_button_text(o.text) == target]
```

Nhưng multiple choice/checkbox dùng exact match:

```python
if option_text == response:
```

và:

```python
if option_text in response:
```

Impact:

- Dễ fail với whitespace, line break, Unicode, tiếng Việt có dấu, option có mô tả.

Recommended fix:

- Dùng `_normalize_button_text()` đồng bộ cho multiple choice và checkbox.

Test:

- Option tiếng Việt.
- Option có extra whitespace.
- Option có line break/description.

Priority: **Medium/High**.

---

#### Issue D — Fallback chọn option đầu tiên đang silent

Multiple choice nếu không match thì chọn option đầu:

```python
first_radio = question_container.find_element(By.XPATH, ".//div[@role='radio']")
driver.execute_script("arguments[0].click();", first_radio)
```

Dropdown nếu không match thì chọn option đầu trong list.

Impact:

- Có thể submit sai answer mà user không biết.
- Khó debug extractor/config mismatch.

Recommended fix:

- Ít nhất log warning gồm `question_id`, expected response, selected fallback.
- Tốt hơn: có mode fail-fast sau này.

Priority: **Medium**.

---

#### Issue E — Linear scale dễ lỗi nếu response là string

Hiện code giả định response là số:

```python
if 0 <= response - 1 < len(scale_options):
```

Impact:

- Nếu response từ CSV/JSON là `"3"`, có thể TypeError.
- `_fill_page()` catch exception và tiếp tục, làm required scale bị bỏ trống.

Recommended fix:

- Convert `int(response)` trước khi dùng.
- Nếu invalid thì warning/fallback/fail rõ.

Test:

- `response=3`.
- `response="3"`.
- `response="bad"`.
- Out-of-range.

Priority: **Medium**.

---

#### Issue F — Time handling có thể sai với nhiều input

Hiện `time` được xử lý như text:

```python
elif question.type in ["input_text", "time"]:
    text_fields = question_container.find_elements(By.XPATH, ".//input[@type='text']")
    for field in text_fields:
        field.clear()
        field.send_keys(str(response))
```

Impact:

- Google Forms time có thể có 2 field giờ/phút.
- Gửi `"12:30"` vào cả 2 field có thể sai.

Recommended test:

- Test form thật có time question ở Chrome headless.
- Nếu fail, split `HH:MM` thành hour/minute.

Priority: **Medium**.

---

#### Issue G — Date selector phụ thuộc DOM

Hiện tìm:

```python
input[@type='date']
```

Impact:

- Nếu Google Forms render date khác theo locale/browser, DOM fill fail.

Test:

- Test form thật với date question.
- Test môi trường tiếng Việt nếu có.

Priority: **Medium**.

---

#### Issue H — Unsupported types chưa explicit

`file_upload`, `rating`, `unknown`, `rank` không có xử lý DOM rõ ràng.

Impact:

- Required unsupported question có thể fail ở bước submit nhưng root cause không rõ.

Recommended fix:

- Add explicit unsupported branch.
- Surface warning/log/UI status.

Priority: **Medium**.

---

## 4. Giải thích cơ chế chạy song song

Có 2 tầng chạy nền/chạy song song.

### 4.1 Background thread ở route `/start_submission`

Khi user start submission, route tạo một thread nền:

```python
thread = threading.Thread(target=submission_task)
thread.start()
```

Ý nghĩa:

- Request trả về ngay.
- Submission vẫn chạy kể cả frontend không poll nữa.
- Nếu app/backend chưa tắt, thread này vẫn tiếp tục.

### 4.2 Worker threads trong `FormSubmitter`

`FormSubmitter.submit_form()` tạo số worker theo `concurrent_threads`.

Mỗi worker tạo **một Chrome WebDriver**:

```text
concurrent_threads = 1  => 1 Chrome instance
concurrent_threads = 5  => 5 Chrome instances
concurrent_threads = 10 => 10 Chrome instances
```

Đây là điểm ngốn RAM/CPU chính.

### 4.3 Cleanup Chrome hiện tại

Worker DOM và prefill đều có:

```python
finally:
    self._increment_status("current_threads", -1)
    if driver:
        driver.quit()
```

Điều này tốt cho normal flow. Nhưng vẫn có rủi ro nếu:

- process bị kill đột ngột;
- Electron đóng window nhưng không kill backend;
- `driver.quit()` không dọn hết child process;
- submission vẫn chạy khi user tưởng đã đóng/xóa app.

### 4.4 `active_submitters`

`active_submitters` giữ submitter đang chạy hoặc mới chạy xong trong TTL 300s để frontend đọc status.

Đây không phải Chrome leak nếu `driver.quit()` thành công, nhưng vẫn giữ object trong memory tạm thời.

---

## 5. Phân tích issue remote “chạy ngầm / dữ liệu rác / nghi virus”

Issue:

> chạy app rồi xoá app đi mà dữ liệu rác còn nguyên, còn chạy ngầm liên tục, bị nhận xét như virus.

Khả năng cao do các nguyên nhân sau:

1. **App data nằm ngoài thư mục app**
   - Config đang dùng `%APPDATA%\GoogleFormTool`.
   - Có thể có:
     - `db.json`;
     - `secret_key`;
     - `logs`;
     - `drivers`.
   - Xóa file app không xóa `%APPDATA%`.

2. **Electron backend process chưa bị kill khi đóng app**
   - Nếu Electron spawn Python/Flask child process mà không kill process tree, backend có thể chạy tiếp.

3. **Submission đang chạy vẫn tiếp tục**
   - Nếu user đóng UI nhưng backend còn sống, Selenium threads vẫn chạy.

4. **Chrome/ChromeDriver orphan process**
   - Khi app bị kill mạnh, child process có thể sót.

5. **Monitoring daemon threads**
   - CPU/network/thread monitors không giữ process sống một mình, nhưng nếu backend còn sống thì chúng vẫn chạy.

Critical requirement cho desktop:

> Electron phải quản lý vòng đời backend: khi app đóng phải stop submission, quit Chrome, kill backend child process tree.

---

## 6. Resource-based concurrency limit

Thay vì web rate limit, desktop app nên giới hạn số Chrome chạy song song theo máy user.

Đề xuất ban đầu:

```text
effective_threads = min(
    user_requested_threads,
    limit_by_available_ram,
    limit_by_cpu_cores,
    hard_cap
)
```

Heuristic:

- Reserve RAM cho OS/app: **1.5-2 GB**.
- Ước lượng mỗi headless Chrome: **400-700 MB**.
- CPU cap: `max(1, cpu_cores - 2)`.
- MVP hard cap: **3 hoặc 4 Chrome instances**.

Ví dụ:

```text
Available RAM: 8 GB
Reserve: 2 GB
Per Chrome: 600 MB
RAM limit: 10
CPU limit: 4
Hard cap: 4
=> effective_threads = 4
```

Nếu user nhập 20 threads trên máy yếu, app nên clamp và báo:

```text
Reduced concurrent threads from 20 to 2 based on available system resources.
```

---

## 7. Randomness strategy

Current issue: thứ tự điền từng form đang tuần tự.

Recommended MVP:

1. Randomize thứ tự câu hỏi trong từng page.
2. Không random thứ tự page.
3. Không shuffle uploaded rows mặc định.
4. Với generated/random mode, có thể randomize row order/prefill URL order để tránh pattern quá rõ.

Test:

- Chạy cùng form 10 submissions.
- Log/capture thứ tự điền.
- Expect có nhiều hơn 1 thứ tự.

---

## 8. Revised test plan

### Level 1 — Fast unit tests

Run:

```bash
pytest tests/test_form_processor.py -v
pytest tests/test_prefill_link_generator.py -v
pytest tests/test_form_submitter.py -v
pytest tests/test_submission_status_retention.py -v
pytest tests/test_submission_persistence.py -v
pytest tests/test_storage_service.py -v
```

Mục tiêu:

- Response generation.
- Prefill URL generation.
- Worker distribution.
- Stop/status retention.
- TinyDB write behavior.

---

### Level 2 — Full automated test suite

Run:

```bash
pytest tests/ -v
```

Pass condition:

- All tests pass.
- Test nào skip vì Chrome/network thì ghi rõ lý do.

---

### Level 3 — Real Google Form DOM-fill matrix

#### 3.1 Simple single-page form

Question types:

- Short answer.
- Paragraph.
- Email.
- Multiple choice.
- Checkbox.
- Dropdown.
- Linear scale.
- Date.
- Time.

Run matrix:

| Case | Threads | Submissions | Expected |
|---|---:|---:|---|
| Basic smoke | 1 | 1 | Success, response sheet có 1 row đúng. |
| Repeat simple | 1 | 5 | Success, values có variation. |
| Parallel small | 2 | 6 | Success, không leak Chrome. |
| Delay random | 1 | 5 | Delay nằm trong range. |
| Stop mid-run | 2 | 20 | Stop được, Chrome đóng. |

---

#### 3.2 Multi-page no-branch form

| Case | Threads | Submissions | Expected |
|---|---:|---:|---|
| Multi-page smoke | 1 | 1 | Next/Submit works. |
| Multi-page repeat | 1 | 5 | Tất cả page được fill. |
| Multi-page parallel | 2 | 6 | Không mismatch page. |

---

#### 3.3 Branching form

Cases:

| Case | Expected |
|---|---|
| Option A → Page 2 | Chỉ Page 2 được answer. |
| Option B → Page 3 | Chỉ Page 3 được answer. |
| Option C → Submit | Later pages bị skip/remove. |

Branching cần test kỹ vì hiện user chủ yếu test form không rẽ nhánh.

---

#### 3.4 Hard question types

| Type | Expected current decision |
|---|---|
| Multiple choice grid | Verify thật. Nếu unsupported thì warning rõ. |
| Checkbox grid | Verify thật. Nếu unsupported thì warning rõ. |
| Rating | Cần proof DOM support hoặc mark unsupported. |
| Rank | Hiện DOM chưa implemented, phải warning/skip rõ. |
| File upload | Mark unsupported trừ khi chủ động implement. |

Pass condition:

- Không silent success với required unsupported question.

---

### Level 4 — Prefill validation

Cases:

| Case | Expected |
|---|---|
| Text-only prefill | URL có đúng entry params, submit success. |
| Choice prefill | Choice match config. |
| Checkbox prefill | Multiple values encode đúng. |
| Date/time prefill | Google accept values. |
| Required unfilled choice | Fallback fill hoặc validation error rõ. |
| Branch submit sentinel | Later answers removed. |
| Unsupported prefill type | Skipped with warning. |

---

### Level 5 — Resource/background-process tests

#### 5.1 Normal completion cleanup

Steps:

1. Start app.
2. Start 5 submissions, 1 thread.
3. Wait complete.
4. Check Task Manager/Process Explorer.

Expected:

- Không còn Chrome/ChromeDriver dư sau completion.
- `current_threads = 0`.

#### 5.2 Stop cleanup

Steps:

1. Start 50 submissions, 2 threads, delay dài.
2. Click Stop.
3. Wait 10s.
4. Check processes.

Expected:

- Submission stopped.
- Chrome/ChromeDriver đóng.
- Không còn worker submit tiếp.

#### 5.3 Electron window close cleanup

Steps:

1. Start long submission.
2. Close Electron window.
3. Observe process tree.

Expected:

- App stop submission hoặc hỏi user.
- Backend process exit.
- Chrome children exit.

#### 5.4 Force quit cleanup

Steps:

1. Start long submission.
2. Kill Electron process.
3. Check orphan Python/Chrome/ChromeDriver.

Expected:

- Lý tưởng là không orphan.
- Nếu OS vẫn để sót, lần mở app sau cần detect/offer cleanup.

#### 5.5 App deletion/uninstall data cleanup

Data hiện ở `%APPDATA%\GoogleFormTool`.

Need product decision:

- Add “Clear local data” button.
- Hoặc add uninstall cleanup script.

Cần dọn:

- `%APPDATA%\GoogleFormTool\db.json`
- `%APPDATA%\GoogleFormTool\logs`
- `%APPDATA%\GoogleFormTool\drivers`
- `%APPDATA%\GoogleFormTool\secret_key`

---

### Level 6 — Resource-limit tests

| Machine condition | User requested | Expected |
|---|---:|---|
| Low RAM | 10 | Clamp xuống safe value. |
| Normal RAM/CPU | 10 | Clamp theo hard cap 3-4. |
| User requests 0 | 0 | Reject. |
| User requests negative | -1 | Reject. |
| User requests huge | 999 | Clamp/reject rõ ràng. |

Need display:

- available RAM;
- CPU core count;
- requested threads;
- effective threads;
- reason for clamp.

---

### Level 7 — Randomness/human-like behavior tests

| Case | Expected |
|---|---|
| Same form, 10 submissions | Question fill order varies. |
| Weighted choice config | Distribution respects weights. |
| Prefill generated rows | Không bị grouped quá máy móc nếu có thể. |
| Uploaded data mode | Preserve row order by default. |

---

## 9. Recommended backlog

### P0 — Must fix/verify for desktop beta

1. Verify/harden Chrome/ChromeDriver cleanup on finish, stop, app exit.
2. Electron lifecycle: kill backend child process tree on exit.
3. Add local data cleanup/uninstall support for `%APPDATA%\GoogleFormTool`.
4. Add machine-aware cap for `concurrent_threads`.
5. Randomize DOM fill order within each page.
6. Explicit warning for unsupported DOM types: `rank`, `rating`, `file_upload`, `unknown`.

### P1 — Important

1. Normalize matching for multiple choice/checkbox.
2. Convert linear scale response safely.
3. Test/fix date/time DOM fill.
4. Add warning for fallback choice selection.
5. Deep-test prefill branching/required questions.

### P2 — Later

1. `Submission.created_at` and stricter ID validation.
2. Pagination/storage optimization.
3. Frontend cleanup after Electron rewrite.
4. Web security hardening only if app becomes network-facing.

---

## 10. Acceptance criteria for next milestone

Milestone pass khi:

1. `pytest tests/ -v` pass.
2. Real simple Google Form DOM fill pass:
   - 1 thread / 1 submission;
   - 1 thread / 5 submissions;
   - 2 threads / 6 submissions.
3. Stop test pass, không leftover Chrome/ChromeDriver.
4. Electron close app stops backend and child processes.
5. Có documented/implemented cleanup path cho `%APPDATA%\GoogleFormTool`.
6. DOM fill order thay đổi qua repeated generated submissions.
7. Unsupported question types không silent.

---

## 11. Conclusion

Với hướng desktop/Electron, có thể defer security web. Rủi ro thực tế lớn nhất hiện tại là:

1. **Background process/resource cleanup** — critical do đã có user report.
2. **Selenium concurrency** — mỗi worker là một Chrome instance, phải cap theo tài nguyên máy.
3. **DOM fill edge cases** — simple forms ổn, nhưng rank/grid/date/time/branching cần test rõ.
4. **Deterministic fill order** — nên randomize trong từng page để giảm cảm giác lặp.

Sau khi hoàn thành P0, desktop beta có thể đạt khoảng **85% readiness**.

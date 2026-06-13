# Google Form Automation Tool — Hardening Task Breakdown

> Roadmap mới để nâng điểm Security, Reliability, Architecture và Performance lên khoảng 9/10 sau các review gần nhất. Scope tài liệu này thay thế roadmap phase cũ và chia việc thành 3 mảng A/B/C để triển khai tuần tự, có kiểm chứng rõ ràng.

---

## Mục tiêu chất lượng

| Mảng | Hiện tại ước lượng | Mục tiêu |
|------|-------------------|----------|
| Security | ~7/10 | 9/10 |
| Reliability | ~7/10 | 9/10 |
| Architecture | ~7/10 | 8.5–9/10 |
| Performance | ~7/10 | 8.5–9/10 sau A/B, 9/10 sau C |

## Quy ước

| Ký hiệu | Ý nghĩa |
|---------|--------|
| P0 | Bắt buộc, ưu tiên cao nhất |
| P1 | Nên làm để đạt mức hardening tốt |
| P2 | Tối ưu sau khi A/B ổn định |

## Verification chung

Sau mỗi task có sửa `app/core/`, `app/services/`, route xử lý submit/upload, hoặc security boundary, chạy tối thiểu:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

Nếu task chỉ sửa tài liệu thì không bắt buộc chạy test, nhưng phải đọc lại diff/nội dung để xác nhận đúng scope.

---

# Part A — Security/Reliability Quick Wins

Mục tiêu: vá các điểm rủi ro thực tế, ít refactor, giúp app local desktop an toàn hơn và giảm lỗi race/UX khi thao tác nhanh.

## Task A-1 — Same-origin guard cho mutating requests

**Priority:** P0  
**Mảng:** Security  
**Files dự kiến:** `app/main_routes.py`, `tests/test_extract_route.py` hoặc test route security mới.

### Scope
- Thêm guard dùng chung cho các route mutating như extract, load data, save edit, start/stop submission, copy form apply.
- Cho phép request không có `Origin`/`Referer` để không phá local clients hợp lệ.
- Nếu có `Origin` hoặc `Referer`, chỉ chấp nhận same host/localhost hiện tại.
- Trả `403` JSON rõ ràng khi bị chặn.

### Verify
- Test request same-origin pass.
- Test cross-origin `Origin: https://evil.example` bị `403`.
- Full regression pass.

## Task A-2 — Generic 500 responses, detailed server logs only

**Priority:** P0  
**Mảng:** Security/Reliability  
**Files dự kiến:** `app/main_routes.py`, route tests liên quan.

### Scope
- Chuẩn hóa các `except Exception` ở route boundary.
- Client nhận lỗi chung kiểu `Internal server error` cho lỗi ngoài dự kiến.
- Lỗi validation/user-action vẫn trả `400`/`409` với message actionable.
- Log server vẫn giữ exception detail bằng `logger.exception(...)`.

### Verify
- Test forced unexpected exception không leak traceback/class/path ra JSON response.
- Existing validation tests vẫn pass.
- Full regression pass.

## Task A-3 — Refuse duplicate submission start with 409 Conflict

**Priority:** P0  
**Mảng:** Reliability  
**Files dự kiến:** `app/main_routes.py`, `tests/test_prefill_submission.py` hoặc route submission test.

### Scope
- Khi `active_submitters[form_id]` đang chạy, `/start_submission` phải từ chối request mới bằng `409`.
- Không silently replace submitter đang chạy.
- Response JSON nói form này đang có submission chạy.

### Verify
- Test start lần 2 khi submitter running trả `409`.
- Test start sau khi finished/cleanup vẫn cho phép.
- Full regression pass.

## Task A-4 — Retain finished status for polling

**Priority:** P0  
**Mảng:** Reliability/UX  
**Files dự kiến:** `app/main_routes.py`, possibly `app/core/form_submitter.py`, tests submission status.

### Scope
- Sau khi submission kết thúc, giữ final status đủ lâu để frontend poll thấy kết quả cuối.
- Không cleanup submitter ngay lập tức trước khi UI đọc được final state.
- Có TTL nhỏ hoặc cache final status theo `form_id`.

### Verify
- Test `submission_status` sau khi submitter finished vẫn trả final success/failed/end_time.
- Test cleanup không giữ dữ liệu vô hạn.
- Full regression pass.

## Task A-5 — Selenium selector hardening for dropdown/options

**Priority:** P1  
**Mảng:** Reliability  
**Files dự kiến:** `app/core/form_submitter.py`, `tests/test_form_submitter.py`.

### Scope
- Làm selector cho dropdown/options bớt phụ thuộc text/class dễ vỡ.
- Ưu tiên `role`, `aria-*`, stable structural selectors khi phù hợp.
- Không rewrite toàn bộ Selenium flow; chỉ harden điểm dễ flake.

### Verify
- Existing form submitter tests pass.
- Add/adjust focused unit tests for selector decision helpers nếu có helper.
- Full regression pass.

## Task A-6 — XLSX column/cell caps

**Priority:** P1  
**Mảng:** Security/Performance  
**Files dự kiến:** `config.py`, `app/core/form_processor.py`, `tests/test_form_processor.py`.

### Scope
- Thêm giới hạn số cột và độ dài cell khi parse CSV/JSON/XLSX upload.
- Reuse style `MAX_UPLOAD_ROWS` hiện có.
- Trả `ValueError` controlled khi vượt giới hạn.

### Verify
- Test file quá nhiều cột bị reject.
- Test cell quá dài bị reject.
- Test file hợp lệ vẫn parse bình thường.
- Full regression pass.

---

# Part B — Reliability/Architecture Hardening

Mục tiêu: làm runtime ổn định hơn khi có lỗi worker, API nội bộ rõ hơn, route exception policy nhất quán hơn.

## Task B-1 — Worker accounting on thread-level failures

**Priority:** P0  
**Mảng:** Reliability  
**Files dự kiến:** `app/core/form_submitter.py`, `tests/test_form_submitter.py`.

### Scope
- Đảm bảo mọi worker thread giảm `current_threads` trong `finally` kể cả crash sớm.
- Đảm bảo batch không kẹt `running=True` khi worker lỗi ngoài dự kiến.
- Final status phải phản ánh success/failed/total nhất quán.

### Verify
- Test giả lập worker exception vẫn có `current_threads == 0` và `running == False` cuối batch.
- Full regression pass.

## Task B-2 — Correct worker distribution for direct class usage

**Priority:** P1  
**Mảng:** Reliability/Architecture  
**Files dự kiến:** `app/core/form_submitter.py`, `tests/test_form_submitter.py`.

### Scope
- Đảm bảo `FormSubmitter` phân phối số lượng submit đúng kể cả khi class được gọi trực tiếp, không chỉ qua route.
- Xử lý remainder rõ ràng khi `num_submission` không chia hết cho số thread.
- Không thay đổi public status response shape.

### Verify
- Test direct submitter call với `num_submission=5`, `threads=2` tạo tổng đúng 5 attempts.
- Full regression pass.

## Task B-3 — Public StorageService.get_form_by_id

**Priority:** P1  
**Mảng:** Architecture  
**Files dự kiến:** `app/services/storage_service.py`, routes/tests đang dùng `_load_form`.

### Scope
- Thêm method public `get_form_by_id(form_id)` thay cho việc route/test gọi private `_load_form` khi không cần private API.
- Giữ `_load_form` nếu nội bộ vẫn cần, nhưng route mới dùng public API.
- Không refactor rộng storage layer ngoài điểm này.

### Verify
- Test `get_form_by_id` trả form đúng và `None` khi không có.
- Existing storage tests pass.
- Full regression pass.

## Task B-4 — Gemini key persistence opt-in

**Priority:** P1  
**Mảng:** Security/UX  
**Files dự kiến:** template/JS liên quan Gemini settings, tests frontend static nếu có.

### Scope
- Không lưu Gemini API key vào `localStorage` mặc định.
- Thêm lựa chọn user rõ ràng nếu muốn remember locally.
- Nếu không opt-in, giữ key trong memory/session runtime của page.
- UI wording nói rõ key lưu local trên máy nếu bật remember.

### Verify
- Static/frontend test hoặc manual check xác nhận không gọi `localStorage.setItem` cho key nếu chưa opt-in.
- Existing frontend tests pass.
- Full regression pass nếu sửa backend/core; nếu chỉ JS có thể chạy targeted frontend tests.

## Task B-5 — Route exception policy cleanup

**Priority:** P1  
**Mảng:** Architecture/Reliability  
**Files dự kiến:** `app/main_routes.py`, route tests.

### Scope
- Sau A-2, gom pattern lỗi route thành helper nhỏ hoặc decorator nhẹ nếu thật sự giảm lặp.
- Phân biệt validation error, conflict, not found, unexpected error.
- Không đổi response contract của các route đang được frontend dùng trừ khi test update rõ ràng.

### Verify
- Route tests pass.
- Full regression pass.

---

# Part C — Performance/Scalability Upgrades

Mục tiêu: giảm session bloat, kiểm soát cost/latency AI, và làm app sẵn sàng hơn cho packaged/local production mode.

## Task C-1 — Server-side upload cache by upload_id

**Priority:** P1  
**Mảng:** Performance/Architecture  
**Files dự kiến:** `app/main_routes.py`, storage/cache module nếu cần, tests load/start submission.

### Scope
- `/load_data` không nhét toàn bộ uploaded responses vào Flask session.
- Lưu parsed responses server-side theo `upload_id` ngắn hạn.
- Session chỉ giữ `upload_id`/metadata nhỏ.
- `/start_submission` đọc responses từ cache theo `upload_id`.

### Verify
- Test load data trả/upload lưu `upload_id`.
- Test start submission dùng cached uploaded data.
- Test missing/expired upload cache trả lỗi controlled.
- Full regression pass.

## Task C-2 — AI endpoint timeout and cost guard

**Priority:** P1  
**Mảng:** Performance/Security  
**Files dự kiến:** `app/core/ai_responder.py`, route AI nếu có, tests AI responder/route.

### Scope
- Thêm timeout cho Gemini calls.
- Giới hạn prompt/input size và số request hợp lý cho local app.
- Trả lỗi controlled khi timeout hoặc vượt giới hạn.
- Không log API key hoặc prompt nhạy cảm quá chi tiết.

### Verify
- Test timeout/failure path không crash route.
- Test oversized prompt bị reject.
- Full regression pass.

## Task C-3 — Upload cache lifecycle and cleanup

**Priority:** P2  
**Mảng:** Performance/Reliability  
**Files dự kiến:** upload cache module/routes tests.

### Scope
- Thêm TTL cleanup cho upload cache sau khi submission xong hoặc sau thời gian ngắn.
- Không xóa cache đang được active submission dùng.
- Có giới hạn tổng số upload cache entries hoặc tổng bytes.

### Verify
- Test expired cache cleanup.
- Test active cache không bị xóa khi đang dùng.
- Full regression pass.

## Task C-4 — Production deployment guardrails

**Priority:** P2  
**Mảng:** Security/Operations  
**Files dự kiến:** `config.py`, app startup docs/tests nếu cần.

### Scope
- Nếu chạy như public web server, yêu cầu cấu hình rõ ràng thay vì mặc định desktop-local unsafe.
- Document local desktop assumptions và các biến môi trường cần bật khi expose network.
- Không tự ý thêm auth system trong task này; chỉ guardrails/warnings/config checks.

### Verify
- Config tests cho desktop default không bị phá.
- Test production/public mode thiếu cấu hình bắt buộc sẽ warning/fail controlled theo design.
- Full regression pass nếu sửa config/app init.

---

# Dependency map

```text
A-1 same-origin guard ───────────────► C-4 production guardrails
A-2 generic 500 responses ───────────► B-5 route exception policy cleanup
A-3 duplicate start 409 ─────────────► A-4 final status retention
A-4 final status retention ──────────► B-1 worker accounting
A-5 selector hardening ──────────────► B-1 worker accounting
A-6 XLSX caps ───────────────────────► C-1 server-side upload cache
B-2 worker distribution ─────────────► B-1 worker accounting
B-3 public storage API ──────────────► B-5 route exception policy cleanup
B-4 Gemini key opt-in ───────────────► C-2 AI cost guard
C-1 upload cache ────────────────────► C-3 cache lifecycle
```

# Recommended execution order

1. A-1 same-origin guard.
2. A-2 generic 500 responses.
3. A-3 duplicate submission 409.
4. A-4 final status retention.
5. A-5 Selenium selector hardening.
6. A-6 XLSX caps.
7. B-2 worker distribution.
8. B-1 worker crash accounting.
9. B-4 Gemini key opt-in.
10. B-3 public storage API.
11. B-5 route exception policy cleanup.
12. C-1 server-side upload cache.
13. C-3 upload cache lifecycle.
14. C-2 AI timeout and cost guard.
15. C-4 production deployment guardrails.

# Completion target

App được coi là đạt mục tiêu hardening khi:

- A-1 đến A-6 pass full regression.
- B-1 đến B-5 pass full regression và không đổi UI contract ngoài các lỗi đã test.
- C-1/C-2 pass nếu muốn đạt performance/security khoảng 9/10.
- C-3/C-4 hoàn tất trước release/public distribution rộng hơn.

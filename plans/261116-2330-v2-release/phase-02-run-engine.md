# Phase 2 — Run engine

Nhánh: `feat/v2-run-engine` (từ `feat/v2-ui-foundation`).

Mục tiêu: một bộ sinh kế hoạch trả lời duy nhất, có seed, và một nơi lưu bền cho từng lượt
gửi. Mô phỏng, báo cáo, MCP, persona và chạy rải đều dựng trên phase này. Chưa đổi UI.

## Hiện trạng

- Hai bộ sinh khác nhau: rút độc lập `generate_random_responses`
  (`app/domain/form_processor.py:236`) cho chế độ direct, và phân bổ quota
  `generate_prefill_responses` (`:267`, `_allocate_counts` `:424`) cho prefill. Cả hai dùng
  `random` toàn cục, không seed.
- Prefill lọc bớt câu trả lời sau khi sinh (`app/adapters/browser/form_submitter.py`
  `_filter_skippable_responses` `:516`, `apply_prefill_branch_stops` ở processor `:290`).
- Trạng thái đợt chạy chỉ trong bộ nhớ (`app/services/submission_manager.py:10`); lịch sử chỉ
  lưu `Submission` tổng hợp (`app/models.py:124`).
- TinyDB ghi lại cả file mỗi lần ghi, khoá chỉ trong tiến trình
  (`app/services/storage_service.py:12`).

## Thiết kế

- **Response plan** (domain thuần, file mới `app/domain/response_plan.py`): hàm
  `build_plan(form, count, seed, mode, responses_list=None) -> ResponsePlan`. Một `ResponsePlan`
  gồm `seed`, `mode`, và danh sách hàng; mỗi hàng có `index`, `answers` (đúng dữ liệu sẽ gửi
  sau mọi bước lọc), và `skipped` (câu bị bỏ cùng lý do). Dùng `random.Random(seed)` riêng,
  truyền vào `FormProcessor`; không đụng `random` toàn cục. Không seed → tự sinh seed và trả
  về để tái lập được.
- Giữ ngữ nghĩa hiện tại của từng chế độ (prefill dùng quota, direct dùng rút độc lập) để không
  đổi hành vi đã có test. Việc lọc và dừng nhánh chuyển vào bước lập kế hoạch để kế hoạch phản
  ánh đúng thứ được gửi. Nếu phần lọc đang phụ thuộc Selenium, tách phần quyết định (thuần)
  khỏi phần thao tác trình duyệt; phần quyết định sang domain.
- **Submitter tiêu thụ kế hoạch**: `FormSubmitter` nhận sẵn danh sách hàng và báo kết quả từng
  hàng qua callback `on_row_result(index, status, error, started_at, finished_at)`. Chữ ký
  công khai hiện có (`submit_form`, `prepare_prefill_queue`, `get_status`, `stop`) giữ nguyên
  để test cũ không đổi; đường mới thêm vào bên cạnh.
- **Run store** (file mới `app/services/run_store.py`):
  - Header đợt chạy trong bảng TinyDB mới `runs` (cùng `db.json`, bảng riêng, không đụng bảng
    form): `run_id`, `form_id`, `created_at`, `mode`, `seed`, `total`, `threads`, delay,
    `status` (`pending|running|paused|interrupted|completed|stopped`), `target_snapshot`
    (phân phối mục tiêu tại thời điểm tạo), `retry_of` (tuỳ chọn). Header chỉ được ghi khi tạo
    và khi đổi trạng thái.
  - Hàng từng lượt trong `<APP_DATA>/runs/<run_id>.jsonl`, chỉ ghi thêm: một dòng "plan" cho
    mỗi hàng khi tạo, rồi một dòng "result" cho mỗi lần đổi trạng thái hàng
    (`in_flight|success|failed|unknown`). Đọc bằng cách gộp theo `index`, dòng sau thắng. Dòng
    cuối hỏng (JSON cắt cụt) bị bỏ qua, không ném lỗi. Một khoá ghi cho mỗi file trong tiến
    trình.
  - Đường dẫn lấy từ `Config` (thêm `RUNS_DIR`, mặc định `<APP_DATA>/runs`, đổi được bằng env
    như `DB_PATH`). Test cô lập qua cùng cơ chế `tests/conftest.py` đang dùng cho `DB_PATH`.
  - Nhà cung cấp có thể thay trong test, theo mẫu `set_storage_provider`
    (`app/services/__init__.py`).
- **Tích hợp**: `/start_submission` tạo header + kế hoạch, chạy qua đường mới, và trả thêm
  `run_id` và `seed` trong response (chỉ thêm khoá). `Submission` tổng hợp vẫn được lưu như cũ
  (US-003 AC6, US-005).
- **File runtime**: khi backend khởi động, ghi `<APP_DATA>/runtime.json` gồm `port`, `pid`,
  `started_at` (ghi vào file tạm rồi rename). Phase 4 dùng file này.

## Commit gợi ý

1. `refactor(domain): build seeded response plans in one place`
2. `feat(storage): persist runs with an append-only row log`
3. `feat(submission): record per-response results for each run`
4. `feat(runtime): write backend runtime info for local clients`

## Test bắt buộc

- Cùng form, cùng seed, cùng chế độ → hai kế hoạch giống hệt; khác seed → khác.
- Prefill: tổng số lựa chọn mỗi câu khớp `_allocate_counts`; test cũ của
  `tests/test_form_processor.py`, `tests/test_prefill_submission.py`,
  `tests/test_form_submitter.py` không sửa.
- 500 hàng ghi từ 10 luồng: đọc lại đủ 500, không trùng, và nội dung `db.json` trước và sau
  khi ghi hàng giống nhau từng byte (chỉ header làm đổi `db.json`).
- File JSONL có dòng cuối cắt cụt vẫn nạp được các hàng trước đó.
- Chạy với driver giả ở cả hai chế độ: hàng được lưu trùng `answers` của kế hoạch; `run_id`
  có trong response.
- Form dạng 1.x (không có trường mới) vẫn nạp và chạy được.
- `tests/test_route_snapshot.py`: không có route mới ở phase này.
- Thêm test: mọi module `app.*` tồn tại trên đĩa đều có trong `hiddenimports` của
  `google_form_tool.spec` (đọc file `.spec` dạng text). Cập nhật `.spec` cho module mới.

## Cuối phase

- Gate + packaging smoke (`/healthz` 200).
- Decision record `docs/decisions/0004-run-store.md` từ `docs/templates/decision.md`: vì sao
  hàng nằm trong JSONL chứ không trong `db.json`, và vì sao kế hoạch được lập trước khi gửi.
- Cập nhật `docs/ARCHITECTURE.md` (Main Flows: Submit, Storage).
- Push; fast-forward `release/v2`; cập nhật bảng trạng thái PR.

## Rollback

`git revert`. Store mới là phụ thêm; xoá thư mục `runs/` không ảnh hưởng form đã lưu.

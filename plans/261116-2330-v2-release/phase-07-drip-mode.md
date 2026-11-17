# Phase 7 — Chạy rải theo thời gian

Nhánh: `feat/v2-drip-mode` (từ `feat/v2-personas-autopilot`; phase này phụ thuộc phase 6).

## Hiện trạng buộc thiết kế

Electron tắt backend bằng `taskkill /T /F` (`electron/backendProcess.js:91`), nên mỗi lần
thoát app là một lần tắt cứng. Khôi phục sau tắt cứng là đường bình thường, không phải ngoại lệ.

## Thiết kế

- **Lịch (domain thuần, `app/domain/drip_schedule.py`)**:
  - `build_schedule(count, start_utc, window_seconds, rng) -> list[datetime]`: chia khung giờ
    thành `count` khoảng và đặt mỗi lượt ở một điểm ngẫu nhiên trong khoảng của nó (rải đều
    có jitter, không dồn cụm). Khung giờ từ 1 phút tới 7 ngày.
  - `due_rows(rows, now, max_per_tick) -> list`: các hàng `pending` có `due_at <= now`, tối
    đa `max_per_tick`.
  - `respread(remaining_count, now, window_end, rng)`: xếp lại các hàng còn lại trên phần
    khung giờ còn lại; nếu khung giờ đã hết thì rải trên một khoảng tối thiểu
    (`remaining_count × min_delay` hiện có), không bao giờ gửi dồn một lúc.
- **Lưu**: khi tạo đợt rải, ghi toàn bộ kế hoạch vào run store (phase 2) với `due_at` (UTC,
  ISO 8601) cho mỗi hàng; header có `schedule: {window_seconds, window_end}` và trạng thái.
  Trước khi gửi một hàng, ghi `in_flight`; sau khi gửi, ghi `success` hoặc `failed`.
- **Bộ chạy (`app/services/drip_runner.py`)**: một luồng nền cho mỗi đợt, nhận đồng hồ
  (`now()`), hàm ngủ và submitter qua tham số để test thay được. Mỗi nhịp: lấy `due_rows`, gửi
  qua đường submitter của phase 2 (tôn trọng số luồng đã cấu hình), ghi kết quả. Đăng ký vào
  `active_submitters` để `/submission_status`, 409 khi trùng form và `/stop_submission` hoạt
  động như đợt thường.
- **Tạm dừng / tiếp tục**: `paused` dừng lấy hàng mới, hàng đang gửi chạy nốt. Tiếp tục gọi
  `respread` cho các hàng `pending`.
- **Khôi phục khi khởi động** (gọi một lần trong `create_app`, sau khi storage sẵn sàng): mọi
  header `running` hoặc `paused` thành `interrupted`; hàng `in_flight` thành `unknown`. Không
  tự gửi gì. UI và MCP hiện đợt bị gián đoạn kèm nút "Tiếp tục"; khi người dùng tiếp tục thì
  `respread` các hàng `pending`. Bước khôi phục đi qua provider của run store để bộ test
  (vốn gọi `create_app` nhiều lần) không chạm dữ liệu thật và không chậm đi. Hàng `unknown` không bao giờ được tự gửi lại (có thể đã tới
  Google); người dùng xử lý qua retry có `include_unknown` của phase 3.
- Áp dụng cho đợt thường luôn: đợt thường bị tắt cứng cũng thành `interrupted` với hàng
  `in_flight` thành `unknown`, để báo cáo không nói sai.
- **Route** (chỉ thêm): `/start_submission` nhận `schedule: {window_minutes}` tuỳ chọn;
  `POST /runs/<run_id>/pause`, `POST /runs/<run_id>/resume`. Resume trả 409 nếu form đang có
  đợt khác chạy.
- **UI**: ở bước Settings, công tắc "Rải theo thời gian" với ô khung giờ và dòng xem trước
  ("khoảng 1 lượt mỗi 1,8 phút, xong lúc 14:30"). Ở Monitor: lượt kế tiếp lúc nào, nút tạm
  dừng/tiếp tục. Trang Home hiện biểu ngữ khi có đợt `interrupted`. Ghi rõ trong UI: đợt chỉ
  chạy khi app đang mở.
- Electron: khi đóng cửa sổ mà có đợt đang chạy, hỏi xác nhận (hộp thoại trong
  `electron/main.js`, đọc `/submission_status`). Không đổi cách tắt backend.

## MCP

`start_run` nhận `window_minutes`; thêm `pause_run`, `resume_run`. `run_status` trả thêm lượt
kế tiếp và trạng thái `interrupted`.

## Test bắt buộc (đồng hồ giả, submitter giả, không ngủ thật)

- 200 lượt trong 6 giờ: mọi `due_at` nằm trong khung; không khoảng 10 phút nào chứa quá số
  lượt cho phép theo `max_per_tick`; đẩy đồng hồ hết khung thì cả 200 được gửi đúng một lần.
- Pause giữa chừng: không hàng mới được gửi khi đồng hồ tiến; resume gửi nốt, tổng đúng 200.
- Tắt cứng mô phỏng: chạy tới giữa, bỏ engine, dựng engine thứ hai trên cùng store và gọi
  khôi phục → header `interrupted`, hàng `in_flight` thành `unknown`, không lần gửi nào xảy ra
  cho tới khi resume; sau resume, không `index` nào được gửi hai lần và các hàng còn lại được
  rải lại (không cùng một `due_at`).
- Resume khi khung giờ đã hết: các hàng còn lại vẫn cách nhau ít nhất `min_delay`.
- Stop một đợt rải: trạng thái `stopped`, hàng `pending` giữ nguyên, không gửi thêm.
- Khung giờ ngoài giới hạn hoặc không phải số → 400. Đợt thường (không `schedule`) hành xử
  như trước.
- Route snapshot: chỉ thêm.

## Cuối phase

Gate; US-015; bảng route; `docs/TEST_MATRIX.md`; `docs/ARCHITECTURE.md` (khôi phục khi khởi
động); push; fast-forward `release/v2`; cập nhật PR.

## Rollback

`git revert`. Đợt rải dở dang ở lại run store dưới dạng `interrupted`, vô hại.

# Phase 3 — Mô phỏng trước khi gửi và báo cáo sau khi gửi

Nhánh: `feat/v2-simulation-report` (từ `feat/v2-run-engine`).

## Mô phỏng (US-010)

- Domain `app/domain/run_report.py`: `summarize_plan(form, plan)` trả cho mỗi câu hỏi: số
  lượt và tỉ lệ mỗi lựa chọn, tỉ lệ bỏ trống, so với tỉ lệ cấu hình; với câu văn bản trả số
  giá trị khác nhau và vài mẫu.
- Route mới `POST /simulate`: body `form_id`, `num_submissions`, `submission_mode`, `seed`
  (tuỳ chọn), `upload_id` (tuỳ chọn). Validate bằng `validate_submission_request` (giới hạn
  500). Trả `seed`, tóm tắt từng câu, cảnh báo câu bị bỏ, và tối đa 20 hàng mẫu. Không tạo
  driver, không ghi run store.
- Chạy thật với cùng seed phải cho đúng kế hoạch đó: `/start_submission` nhận `seed` tuỳ chọn.
- UI ở bước "Review and Start": nút "Mô phỏng", biểu đồ cột mục tiêu so với mô phỏng cho từng
  câu lựa chọn (thư viện biểu đồ đã giữ ở phase 1), bảng mẫu cuộn được, nút "Sinh lại" (seed
  mới) và "Chạy đúng bản này" (giữ seed). Có trạng thái rỗng và lỗi.

## Báo cáo (US-011)

- Domain: `summarize_run(form, header, rows)` trả tổng quan (thành công, lỗi, không rõ, thời
  lượng), thực tế so với mục tiêu từng câu (chỉ tính hàng `success`), và nhóm lý do lỗi.
- Route mới:
  - `GET /runs?form_id=` — danh sách header của một form, mới nhất trước.
  - `GET /runs/<run_id>` — header + tóm tắt.
  - `GET /runs/<run_id>/rows?status=&offset=&limit=` — hàng có phân trang (limit tối đa 100).
  - `GET /runs/<run_id>/export?format=csv|json` — tải về; dùng lại cách dựng response trong
    `app/services/history_export.py`. Ô CSV bắt đầu bằng `=`, `+`, `-`, `@` phải được vô hiệu
    hoá (chống CSV injection); kiểm xem export hiện có đã làm chưa và dùng chung một hàm.
  - `POST /runs/<run_id>/retry` — tạo đợt mới chỉ gồm các hàng `failed` của đợt gốc, giữ
    nguyên `answers`, ghi `retry_of`. Hàng `unknown` không được gửi lại tự động; chỉ gửi khi
    body có `include_unknown: true`. Trả 409 nếu form đang có đợt chạy, 404 nếu không có đợt,
    400 nếu không có hàng nào để gửi lại.
- `run_id` không hợp lệ (ký tự ngoài `[a-z0-9_]`) trả 400 trước khi chạm hệ thống file.
- UI: trang lịch sử của form liệt kê các đợt; trang chi tiết đợt có thẻ số liệu, biểu đồ thực
  tế so với mục tiêu, bảng hàng lọc theo trạng thái, nút export và "Gửi lại lượt lỗi". Trang
  mới là route trang `GET /runs/<run_id>/view` (hoặc panel trong trang hiện có, chọn cách ít
  đụng template nhất) và đi theo mẫu `app/routes/pages.py`.
- Dữ liệu form bên ngoài hiển thị trong bảng phải được escape (đặt bằng `textContent`, không
  `innerHTML`); `tests/test_p1_security_static.py` phải xanh.

## Dashboard realtime

- Bước Monitor: thẻ số liệu (xong, thành công, lỗi, tốc độ, thời gian còn lại ước tính), thanh
  tiến độ, vòng tròn thành công/lỗi/chờ, và dòng sự kiện gần nhất (đọc từ
  `/runs/<run_id>/rows` hoặc trường thêm trong `/submission_status`).
- Giữ polling `/submission_status` (hợp đồng hiện có, chỉ thêm khoá `run_id`). Không thêm SSE:
  Waitress giữ một luồng cho mỗi kết nối mở và polling 1 giây là đủ cho 10 luồng gửi.
- Khi đợt xong: hiện nút "Xem báo cáo" dẫn tới trang chi tiết.

## Test bắt buộc

- `/simulate` không khởi tạo driver (monkeypatch `FormSubmitter`/`webdriver` để ném lỗi nếu
  được gọi) và không tạo file trong `RUNS_DIR`.
- Seed cố định: `answers` từ `/simulate` trùng với hàng được lưu sau `/start_submission` cùng
  seed với driver giả, ở cả `prefill` và `direct`.
- `/simulate` với 501 lượt trả 400.
- Báo cáo: đợt giả có 7 thành công, 3 lỗi → số liệu và phân phối thực tế đúng; retry tạo đợt
  3 hàng với `answers` giống hệt; retry lần hai trên đợt gốc không gửi trùng hàng đã thành
  công ở đợt retry (hoặc trả 400, chọn một và ghi vào user story).
- Export CSV và JSON; ô nguy hiểm được vô hiệu hoá.
- Route snapshot cập nhật: chỉ thêm các route trên.

## Cuối phase

- Gate. Tự kiểm bằng mắt các màn hình mới như phase 1.
- User stories US-010, US-011; bảng route; `docs/TEST_MATRIX.md`.
- Push; fast-forward `release/v2`; cập nhật PR.

## Rollback

`git revert`. Route mới chỉ đọc, trừ `retry`.

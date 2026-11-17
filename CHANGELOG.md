# Changelog

Tất cả thay đổi đáng chú ý của Google Form Automation Tool. Định dạng theo
[Keep a Changelog](https://keepachangelog.com/vi/1.1.0/), version theo
[Semantic Versioning](https://semver.org/lang/vi/).

## [2.0.0] - 2026-11-17

Biết trước kết quả trước khi gửi, đối chiếu sau khi gửi, câu trả lời theo persona, chạy
rải theo thời gian và điều khiển bằng agent qua MCP, trên một giao diện mới chạy offline.

### Added

- **Giao diện mới.** Design system riêng, app shell có sidebar, dark mode (theo hệ điều
  hành cho tới khi người dùng chọn), stepper ở trang Form Filling, skeleton và trạng thái
  lỗi khi xem trước. Bootstrap, Font Awesome, driver.js và Chart.js đóng gói sẵn trong
  `app/static/vendor/` kèm license; app không còn tải asset từ CDN.
- **Mô phỏng trước khi gửi** (`POST /simulate`). Xem phân phối từng câu so với mục tiêu và
  bảng mẫu, không mở Chrome và không gọi Google. Cùng seed cho đúng các lượt sẽ gửi;
  nút "Run exactly this" gửi đúng kế hoạch đó.
- **Báo cáo sau khi gửi.** Mỗi đợt lưu từng lượt; trang báo cáo `/runs/<id>/view` so thực
  tế với mục tiêu, lọc và phân trang lượt, export CSV/JSON, gửi lại lượt lỗi (lượt chưa rõ
  kết quả chỉ gửi lại khi người dùng chọn, lượt đã gửi lại không gửi lần nữa). Dashboard
  tiến độ realtime hiện tốc độ, thời gian còn lại và các lượt mới nhất.
- **Preset và template.** Preset một chạm cho câu chọn và thang điểm (đều, nghiêng đầu,
  nghiêng cao/thấp, hình chuông); lưu, nhân bản, xuất và nhập cấu hình dạng JSON, xem
  trước trước khi áp dụng.
- **Persona.** Tối đa 8 nhóm người trả lời có trọng số (tổng 100), mỗi nhóm ghi đè cấu hình
  cho các câu đã chọn. Mỗi lượt lấy mọi đáp án từ một persona; mô phỏng và báo cáo chia
  kết quả theo persona.
- **AI Autopilot** (`POST /ai/propose_config`). Gemini đề xuất cấu hình cả form, có thể kèm
  persona, từ mô tả bằng lời. Đề xuất sai schema bị từ chối; người dùng xem trước/sau từng
  câu rồi mới áp dụng. API key không được ghi log, lưu hay trả về.
- **Chạy rải theo thời gian.** Rải lượt gửi trong một khung từ 1 phút tới 7 ngày, tạm
  dừng/tiếp tục (`/runs/<id>/pause`, `/runs/<id>/resume`). Khi mở lại app, đợt đang dở
  được đánh dấu `interrupted` và chờ người dùng tiếp tục; lượt chưa rõ kết quả không tự gửi
  lại. App hỏi lại trước khi đóng khi còn đợt đang chạy.
- **MCP server và Claude skill.** `GoogleFormToolMcp.exe` (hoặc `python -m app.mcp_server`)
  cho agent 20 tool: extract, cấu hình, preset, template, persona, mô phỏng, chạy, tạm
  dừng, tiếp tục, dừng, báo cáo, gửi lại. Server chỉ gọi tới app đang mở. Settings hiện cấu
  hình sẵn để dán vào Claude Desktop và Claude Code; skill ở
  `skills/google-form-automation/SKILL.md`.
- Route JSON `GET /forms`, `GET /forms/<form_id>` và `GET /runs`; backend ghi
  `runtime.json` (port, pid) khi khởi động; biến môi trường tuỳ chọn `RUNS_DIR`.

### Changed

- Chế độ gửi trực tiếp rút câu trả lời riêng cho từng lượt thay vì một bộ cho cả đợt. Chế độ
  prefill giữ đúng quota từng câu, xáo theo seed.
- `/start_submission` trả thêm `run_id`, `seed` và nhận `seed`, `schedule` tuỳ chọn;
  `/submission_status` trả thêm `run_id`, `scheduled`, `paused`, `next_due_at`. Các khoá cũ
  giữ nguyên.
- Nâng `pydantic` 2.11.5 lên 2.12.5 (cần cho `mcp` 1.30.0).

### Fixed

- Các luồng gửi trực tiếp chạy song song không còn gửi nhầm câu trả lời của lượt khác.
- `/save_edit` từ chối tỉ lệ ngoài 0–100 hoặc thiếu, thay vì lưu và làm form không mở được.
- Ghi đè của persona chỉ thay các trường nó đặt.
- Đợt chạy rải dừng ở trạng thái `interrupted` khi trình duyệt không khởi động được, thay vì
  thử lại liên tục.
- Timeout của Gemini trả về ngay khi hết hạn.

### Security

- Export lịch sử và báo cáo vô hiệu hoá ô bắt đầu bằng công thức (CSV injection).
- Mô tả form và mô tả người dùng gửi cho Gemini dưới dạng khối dữ liệu, không phải chỉ dẫn;
  đề xuất trả về được kiểm như dữ liệu không tin cậy.

### Internal

- Kế hoạch gửi có seed nằm trong `app/domain/response_plan.py`; bản ghi từng lượt lưu ở
  `<APP_DATA>/runs/<run_id>.jsonl`, không ghi vào `db.json` (decision 0004).
- MCP là proxy HTTP tới app đang chạy (decision 0005). `import app` nhẹ hơn nhờ factory
  tách riêng.
- Test tăng từ 272 lên 529.

## [1.2.0] - 2026-11-10

Bản phát hành lớn đầu tiên sau v1.1.0: chuyển sang bộ cài desktop, thêm tính năng
copy form, siết bảo mật và độ ổn định, đồng thời dọn lại toàn bộ cấu trúc code.

### Added

- **Bộ cài Windows (Electron).** App giờ là ứng dụng desktop, phát hành dạng bộ cài
  NSIS `.exe` và `.msi` kèm `SHA256SUMS.txt` để kiểm tra toàn vẹn. Thay cho file
  `.zip` giải nén của các bản trước.
- **Copy form (best effort).** Trang `Form copy` trích xuất form nguồn, xem trước kế
  hoạch copy và áp lên form đích. Kết quả `success` hoặc `partial` kèm danh sách câu
  hỏi không copy được.
- **Trang Diagnostics** (`/settings/diagnostics`) hiển thị trạng thái Chrome,
  ChromeDriver, đường dẫn dữ liệu và log mà không tự tải driver.
- **Giới hạn file upload:** tối đa 5 MB, 500 dòng, 100 cột, 10.000 ký tự mỗi ô
  (chỉnh được qua `MAX_UPLOAD_BYTES`, `MAX_UPLOAD_ROWS`, `MAX_UPLOAD_COLUMNS`,
  `MAX_UPLOAD_CELL_LENGTH`). Giao diện hiển thị số dòng và xem trước dữ liệu đã tải.
- **Timeout cho AI:** request Gemini có thời gian chờ tối đa và giới hạn độ dài prompt,
  không còn treo vô hạn.
- **Landing page** (`landing/`) giới thiệu và dẫn tới bản tải mới nhất, deploy riêng.
- File `LICENSE` (MIT).

### Changed

- Bắt đầu submit trong khi form đó đang chạy trả `409 Conflict` thay vì chạy chồng.
- Trạng thái của lượt submit đã xong được giữ 60 giây rồi tự dọn.
- Lỗi phía server trả thông báo chung, chi tiết chỉ ghi vào log.
- Chia số lượt submit đều cho các luồng; từ chối số lượt hoặc số luồng nhỏ hơn 1.
- Nút submit và dropdown được nhận diện ổn định hơn (so khớp text đã chuẩn hoá).

### Removed

- Bảng theo dõi CPU/RAM trong lúc submit, cùng các route nội bộ `/system_status`,
  `/monitoring_history`, `/generate_response`, `/ai_status` và dependency `psutil`.
  Không ảnh hưởng tới luồng sử dụng chính.
- Cấu hình Docker; môi trường dev chuyển sang `uv`.

### Fixed

- Trang **About** không còn lỗi 500 (ký tự `%` trong mô tả tính năng).
- Xoá form chuyển sang `POST`, tránh xoá nhầm qua link.
- Dữ liệu form bên ngoài được escape khi xem trước.
- Link ngoài trong cửa sổ Electron mở bằng trình duyệt mặc định thay vì trong app.

### Security

- Chặn request khác nguồn (kiểm tra `Origin`/`Referer` với host của app).
- Cảnh báo khi chạy ở chế độ `FLASK_DEBUG=1`.

### Internal

- Tách `main_routes.py` thành 7 module route và 3 service; code nghiệp vụ nằm trong
  `app/domain` (không phụ thuộc Selenium), phần trình duyệt và AI nằm trong
  `app/adapters`; `config.py` chuyển vào `app/config.py`.
- Snapshot hợp đồng route, môi trường test cô lập, CI (pytest, ruff, gitleaks,
  pip-audit, npm audit) và workflow release.
- User stories trong `docs/product/user-stories.md`; quy trình làm việc gộp vào
  `docs/WORKFLOW.md`.

## [1.1.0] - 2026-05-01

### Added

- Product tour tự hiện lần đầu vào app, có thể xem lại từ sidebar.
- Trang About với workflow, tính năng, tech stack và thông tin tác giả.
- Tự phát hiện Chrome và tự tải ChromeDriver đúng version.

### Changed

- README viết lại cho người dùng cuối; version hiển thị ở footer; nút Report Bug.
- `.env` không còn bắt buộc.

### Fixed

- Không crash khi thiếu `.env` (tự sinh `SECRET_KEY`, tự tạo `DB_PATH`).
- Đường dẫn ChromeDriver rỗng không còn gây lỗi âm thầm.

## [1.0.0-beta.1] - 2026-04-30

- Bản beta đầu tiên: submit Google Form hàng loạt không cần Google Forms API, phát
  hành dạng `.zip` cho Windows 10/11.

[2.0.0]: https://github.com/PhamXuanKhang/google-form-tool/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/PhamXuanKhang/google-form-tool/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/PhamXuanKhang/google-form-tool/compare/v1.0.0-beta.1...v1.1.0
[1.0.0-beta.1]: https://github.com/PhamXuanKhang/google-form-tool/releases/tag/v1.0.0-beta.1

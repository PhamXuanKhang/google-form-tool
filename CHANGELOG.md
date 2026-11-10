# Changelog

Tất cả thay đổi đáng chú ý của Google Form Automation Tool. Định dạng theo
[Keep a Changelog](https://keepachangelog.com/vi/1.1.0/), version theo
[Semantic Versioning](https://semver.org/lang/vi/).

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

[1.2.0]: https://github.com/PhamXuanKhang/google-form-tool/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/PhamXuanKhang/google-form-tool/compare/v1.0.0-beta.1...v1.1.0
[1.0.0-beta.1]: https://github.com/PhamXuanKhang/google-form-tool/releases/tag/v1.0.0-beta.1

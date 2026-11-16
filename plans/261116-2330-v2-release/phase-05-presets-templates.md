# Phase 5 — Preset phân phối và template cấu hình

Nhánh: `feat/v2-presets-templates` (từ nhánh xanh gần nhất, bình thường là `feat/v2-mcp-core`).

## Preset (domain thuần, `app/domain/distribution_presets.py`)

- `apply_preset(option_count, preset, ordered) -> list[float]`, tổng đúng 100 (làm tròn 2 chữ
  số, phần dư dồn vào lựa chọn lớn nhất).
- Preset: `uniform` (đều), `positive_skew` và `negative_skew` (nghiêng về cuối hoặc đầu
  thang), `bell` (đỉnh ở giữa), `first_heavy` (lựa chọn đầu chiếm phần lớn). Các preset có
  hướng chỉ áp dụng cho câu có thứ tự (thang điểm, lưới thang đo); câu lựa chọn thường chỉ có
  `uniform` và `first_heavy`.
- UI trong thẻ câu hỏi (`app/static/js/form_filling/question_config.js`): hàng nút preset, áp
  dụng ngay vào các ô tỉ lệ và có thể sửa tay tiếp. Thêm "Áp dụng cho mọi câu cùng loại".
- Validator phía trình duyệt (`prefill_validator.js`) vẫn là cổng kiểm cuối; test JS hiện có
  (`tests/js/test_prefill_validator.mjs`) không sửa.

## Template

- Template là cấu hình trả lời của một form tách khỏi form: `schema_version`, `name`,
  `created_at`, `form_fingerprint` (băm thứ tự + loại + số lựa chọn của các câu), và cấu hình
  theo từng câu (khoá bằng `question_id`, kèm `text` để đối chiếu).
- Route mới:
  - `GET /forms/<form_id>/config/export` — tải file JSON.
  - `POST /forms/<form_id>/config/import` — nhận file JSON (giới hạn `MAX_UPLOAD_BYTES`),
    validate bằng pydantic, trả bản xem trước: câu khớp, câu không khớp, câu thiếu. Chỉ áp
    dụng khi body có `apply: true`. Khớp theo `question_id`, sau đó theo `text` + loại.
    Template có `schema_version` lạ hoặc sai schema → 400.
  - `POST /forms/<form_id>/duplicate_config` không cần thiết nếu export/import đã đủ; "nhân
    bản" làm ở UI bằng cách lưu template có tên vào store cục bộ: bảng TinyDB mới `templates`
    với `GET /templates`, `POST /templates`, `POST /templates/<id>/delete` (xoá dùng POST theo
    quy ước hiện có của `/forms/delete`).
- Không bao giờ lưu API key hay đường dẫn máy vào template.
- UI: ở bước cấu hình, menu "Template": lưu hiện tại, áp dụng template đã lưu, nhập file,
  xuất file. Áp dụng luôn qua bước xem trước.

## MCP

Thêm tool `apply_preset` (form_id, question_id hoặc "all", preset), `export_config`,
`import_config` (có `apply` mặc định false), `list_templates`.

## Test bắt buộc

- Mỗi preset với 2 đến 11 lựa chọn: tổng 100, không âm, đúng hình dạng (ví dụ `bell` đối xứng,
  `positive_skew` không giảm).
- Export rồi import vào chính form đó → `response_config` giống hệt trước khi export.
- Import vào form khác cấu trúc → báo đúng câu không khớp, không áp dụng phần không khớp.
- File sai schema, quá lớn, hoặc không phải JSON → 400/413, form không đổi.
- Route snapshot: chỉ thêm.

## Cuối phase

Gate; US-013; bảng route; `docs/TEST_MATRIX.md`; push; fast-forward `release/v2`; cập nhật PR.

## Rollback

`git revert`. Bảng `templates` là phụ thêm.

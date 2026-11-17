# Phase 6 — Persona và AI Autopilot

Nhánh: `feat/v2-personas-autopilot` (từ nhánh xanh gần nhất).

## Persona

- Model (`app/models.py`, chỉ thêm trường tuỳ chọn): `Form.personas: Optional[List[Persona]]`.
  `Persona` gồm `persona_id`, `name`, `weight` (0–100), `description` (tuỳ chọn), và
  `overrides: Dict[question_id, AnswerConfig]`. Câu không có override dùng cấu hình chung của
  form. Tối đa 8 persona. Tổng trọng số phải bằng 100 khi có persona.
- Sinh kế hoạch (`app/domain/response_plan.py`): khi form có persona, chia số lượt cho persona
  bằng `_allocate_counts` (`app/domain/form_processor.py:424`), rồi với mỗi persona sinh các
  hàng của nó từ cấu hình đã gộp override. Mỗi hàng ghi `persona_id`. Trộn thứ tự hàng bằng
  RNG của kế hoạch để persona không đi thành cụm. Không có persona → hành vi y như phase 2.
- Mô phỏng và báo cáo (`app/domain/run_report.py`) thêm phân tách theo persona: số lượt mỗi
  persona và phân phối trong từng persona.
- Route mới `POST /forms/<form_id>/personas` (thay toàn bộ danh sách, validate tổng trọng số,
  question_id tồn tại, tỉ lệ mỗi câu hợp lệ theo cùng luật với `/save_edit`) và
  `GET /forms/<form_id>/personas`.
- Template (phase 5, nếu đã xong) mang theo persona: thêm trường tuỳ chọn, không tăng
  `schema_version` nếu trình nhập cũ vẫn đọc được.
- UI: tab "Persona" ở bước cấu hình. Danh sách persona với thanh trọng số; chọn một persona
  thì các thẻ câu hỏi hiện cấu hình của persona đó, câu nào khác cấu hình chung thì có nhãn
  "đã ghi đè" và nút "về mặc định".

## AI Autopilot

- Dùng lại `AIResponder` (`app/adapters/ai/ai_responder.py`): `_generate_content` (đã có
  timeout và giới hạn độ dài prompt), cơ chế chọn model, và cách xử lý lỗi của
  `app/routes/ai.py` (mã lỗi, 504 khi timeout, không lộ key).
- Phương thức mới `propose_form_config(form, audience_description, want_personas)`: prompt gồm
  tiêu đề form, danh sách câu hỏi (id, loại, lựa chọn) và mô tả đối tượng; yêu cầu trả JSON
  theo schema cố định (dùng structured output của SDK nếu version đang ghim hỗ trợ; đọc tài
  liệu hiện hành). Mô tả của người dùng được đặt trong khối dữ liệu tách biệt, không phải
  phần chỉ dẫn.
- Kết quả đi qua validator thuần ở domain (`app/domain/autopilot_proposal.py`): parse bằng
  pydantic; bỏ question_id không tồn tại và lựa chọn không có trong form (ghi cảnh báo); tỉ
  lệ âm hoặc không phải số → từ chối cả đề xuất; chuẩn hoá tổng về 100 khi lệch nhỏ (≤ 1),
  lệch lớn → từ chối câu đó. Câu văn bản: giới hạn số câu trả lời gợi ý và độ dài mỗi câu.
- Route mới `POST /ai/propose_config`: body `form_id`, `api_key`, `audience` (giới hạn độ
  dài), `want_personas`. Trả đề xuất đã kiểm + cảnh báo. **Không lưu gì.** Áp dụng là bước
  riêng do người dùng bấm, đi qua `/save_edit` và `/forms/<id>/personas` hiện có.
- UI: nút "AI Autopilot" ở đầu bước cấu hình mở panel: ô mô tả đối tượng, công tắc "tạo
  persona", nút tạo; kết quả hiện dạng so sánh trước/sau cho từng câu, chọn áp dụng tất cả
  hoặc từng câu. Dùng lại luồng nhập và kiểm key hiện có.

## MCP

Thêm tool `get_personas`, `set_personas`. Không thêm tool Autopilot: agent tự là bộ đề xuất,
và MCP không nhận API key.

## Test bắt buộc

- Hai persona 60/40 với lựa chọn tách biệt (A chỉ chọn nhóm X, B chỉ chọn nhóm Y), 100 lượt:
  đúng 60 và 40 hàng; không hàng nào trộn X với Y; cùng seed cho cùng kết quả.
- Form không persona: kế hoạch trùng với kết quả của phase 2 cho cùng seed.
- Form dạng 1.x và dạng phase 2 nạp được.
- Trọng số không cộng đủ 100, quá 8 persona, question_id lạ → 400.
- Autopilot với client Gemini giả: JSON hợp lệ → đề xuất đúng; JSON hỏng, sai schema, tỉ lệ
  âm → lỗi có mã, form không đổi; question_id lạ bị bỏ kèm cảnh báo; timeout → 504.
- Sau `POST /ai/propose_config`, `response_config` trong storage không đổi.
- Key không xuất hiện trong log (theo mẫu `tests/test_ai_text_route.py`) và không có trong
  response.
- Route snapshot: chỉ thêm.

## Cuối phase

Gate; US-014; bảng route; `docs/TEST_MATRIX.md`; push; fast-forward `release/v2`; cập nhật PR.

## Rollback

`git revert`. Trường `personas` là tuỳ chọn; bản cũ bỏ qua nó khi đọc (kiểm `Form` không cấm
trường thừa trước khi dựa vào điều này; nếu cấm, ghi chú trong changelog rằng hạ cấp cần xoá
persona).

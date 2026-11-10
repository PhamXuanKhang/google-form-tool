# Phase 1 — User stories theo use case

Nhánh: `refactor/product-user-stories` (từ `review`).

## Yêu cầu

- Tạo `docs/product/user-stories.md`. Khởi điểm là 10 dòng `docs/TEST_MATRIX.md` và bảng
  Use Cases trong `docs/PROJECT_REFACTOR_AUDIT.md`. Trần khoảng 8 story; gộp dòng trùng
  (ví dụ Bulk direct submit + Prefill submit có thể là một story với hai chế độ nếu UI là một luồng).
- Mỗi story: mã `US-0NN`, "As a … I want … so that …", 3–5 acceptance criteria quan sát
  được, trạng thái `keep | change | retire`, route + module + test chứng minh.
- Trạng thái đã chốt: Form copy `keep` (ghi rõ giới hạn best-effort); Landing `keep`
  (deployable riêng); hiển thị tài nguyên khi submit `retire`.
- Liệt kê route giữ lại ở cuối file (bảng route → story). Route không thuộc story nào
  = retire. Danh sách retire phải đúng 4: `/generate_response`, `/ai_status`,
  `/monitoring_history`, `/system_status`. Nếu đọc code phát hiện thêm route mồ côi:
  **dừng hỏi user**, không tự thêm vào danh sách xoá.
- Viết theo hành vi hiện có trong code, không mô tả tính năng chưa có.
- `docs/TEST_MATRIX.md`: cột Story dùng mã `US-0NN`, đánh dấu Runtime diagnostics phần
  monitoring là `retired`. `docs/product/README.md`: trỏ tới file mới.

## Kiểm

- Mỗi route trong `grep -n "@bp.route" app/main_routes.py` có đúng một story hoặc nằm trong danh sách retire.
- Mỗi file test được tham chiếu tồn tại.
- Commit: `docs(product): add user stories per use case`.

# Phase 2 — Xoá code chết

Nhánh: `refactor/remove-dead-routes-monitoring` (từ nhánh phase 1).

## Trước khi xoá

- `grep -rn` từng route trên `app/ electron/ scripts/ tests/ landing/` (trừ `node_modules`)
  để chắc không có caller URL động. Có caller ngoài dự kiến → dừng hỏi user.

## Commit (mỗi dòng một commit, pytest + ruff xanh sau từng commit)

1. `refactor(ai): remove unused generate_response and ai_status routes`
   - Xoá 2 route trong `app/main_routes.py` (`:517`, `:697`).
   - Xoá `AIResponder.generate_responses_batch` và `AIResponder.generate_response`
     (`app/core/ai_responder.py:61`, `:88`): sau khi route chết đi, method thứ hai chỉ được
     method thứ nhất gọi (`:103`). Trước khi xoá, grep `generate_response(` trong `app/` và
     `tests/` để xác nhận; nếu còn caller khác thì chỉ xoá `generate_responses_batch`.
     Không đụng `form_processor._generate_response_for_question`.
2. `refactor(monitoring): retire resource display and monitoring routes`
   - Xoá `/system_status`, `/monitoring_history`, thư mục `app/monitoring/`,
     `tests/test_monitoring_routes.py`.
   - Gỡ trong `app/static/js/form_filling/submission.js`: `updateSystemResources` (fetch
     `/system_status` ở `:254`), lời gọi ở `:151`, `updateResourceDisplay` và interval polling.
   - Gỡ khởi tạo `window.resourceChart` trong `app/static/js/form_filling/main.js:305-…`
     (canvas `resource-chart`) và mọi tham chiếu `resourceChart` còn lại (grep).
   - Gỡ HTML panel trong `app/templates/form_filling.html` (khoảng `:248-255`, xác nhận bằng
     grep `resource-chart` / id panel), CSS chỉ dùng cho panel đó, chuỗi i18n chỉ dùng cho panel
     (cập nhật `.po` và build lại `.mo` bằng pybabel nếu có thay đổi chuỗi).
   - Progress success/fail của submission phải giữ nguyên. Nếu Chart.js chỉ còn được dùng
     cho chart khác thì giữ thư viện; chỉ xoá chart tài nguyên.
   - Kiểm: `grep -rn "system_status\|resourceChart\|resource-chart\|monitoring" app/` rỗng
     (trừ chuỗi không liên quan, ghi lý do nếu có).
3. `build(deps): drop psutil`
   - Xoá `psutil` khỏi `pyproject.toml`, chạy `uv lock`, xoá khỏi
     `google_form_tool.spec` hiddenimports (`:52-53`). Xoá mục `app.monitoring*` nếu có trong `.spec`.
   - Kiểm `grep -rn psutil app tests google_form_tool.spec pyproject.toml` rỗng.

## Cuối phase

- `tests/test_frontend_popup_global.py`, `tests/test_i18n_render.py`, `tests/test_p1_security_static.py`
  phải còn xanh (chúng quét template/JS).
- Packaging smoke + `/healthz` 200 trên backend đóng gói.
- Cập nhật `docs/ARCHITECTURE.md` dòng Diagnostics (không còn `app/monitoring/`).

## Rollback

`git revert` từng commit; không có migration dữ liệu.

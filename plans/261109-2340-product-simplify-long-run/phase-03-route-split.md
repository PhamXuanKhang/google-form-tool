# Phase 3 — Tách routes

Nhánh: `refactor/phase-3-route-split` (từ nhánh phase 2).

## Nguồn sự thật

Chỉ dùng `plans/260815-1543-phase-3-route-split/plan.md` cho DD-1..DD-3 và hai bảng phân bổ
(route → module, state → service). Sáu file `phase-0*.md` trong thư mục đó là placeholder rỗng,
**không** dùng. Bỏ qua các mục lỗi thời trong `plan.md` cũ: "1 PR" (thay bằng commit local),
"30 route" / "215 passed" (dùng số đếm thực), `ak decision add` (thay bằng file decision).

## Điều chỉnh so với plan cũ

- Không có `app/routes/monitoring.py` (2 route đã xoá ở phase 2).
- `ai.py` chỉ còn `/validate_api_key`, `/generate_ai_text_answers`.
- 7 module route: `health, pages, forms, data, ai, submissions, history`.
- Ghi chú điều chỉnh này vào đầu `plan.md` cũ, commit riêng:
  `docs(plans): align route split plan with retired routes`.

## Bước 1 — Snapshot (gate cứng, trước khi tách)

Tạo `tests/test_route_snapshot.py`, chạy trên `main_routes.py` hiện tại, phải xanh trước khi tách:

- Phần tĩnh: từ `app.url_map`, với mỗi rule thuộc blueprint `main` (22 route sau phase 2; dùng
  số đếm thực), so với bảng kỳ vọng hard-code trong test: `rule`, tập method (bỏ HEAD/OPTIONS),
  `endpoint` (`main.<func>`). Có route thừa hoặc thiếu = fail.
- Phần động: với mỗi route, gọi qua `client` fixture (storage stub, không Selenium/network):
  - happy path khi làm được không cần Selenium/network (pages, health, history, data, delete,
    submission_status, export) → assert status + tập key JSON đã sort (hoặc content-type với HTML/CSV);
  - một ca lỗi validate (body thiếu/sai) cho mỗi route POST → assert status + tập key JSON.
  - Route chỉ chạy được với Selenium/AI thật: monkeypatch adapter như test hiện có đang làm
    (tham khảo `tests/test_extract_route.py`, `tests/test_ai_text_route.py`,
    `tests/test_form_copy_routes.py`), không gọi ra ngoài.
- So sánh: status và tập key, không so giá trị động (id, timestamp).
- Commit: `test: add route contract snapshot`.

## Bước 2–5

Theo thứ tự DD-2: tách state ra `app/services/{upload_cache,submission_manager,history_export}.py`
→ tách route ra `app/routes/` với blueprint dùng chung trong `app/routes/__init__.py` (DD-1)
→ migrate test (`grep -rn "main_routes" tests` = 0, kể cả chuỗi trong `monkeypatch.setattr`)
→ `.spec` hiddenimports: bỏ `app.main_routes`, thêm package `app.routes`, 7 module
`app.routes.*`, 3 module `app.services.*` mới. Snapshot xanh sau mỗi bước.

## Bước 6 — Decision + smoke

`docs/decisions/0002-route-split.md` theo `docs/templates/decision.md`. Cập nhật
`docs/ARCHITECTURE.md` (Main Flows, Boundaries). Packaging smoke theo quy tắc chung.

## Kiểm

- Snapshot khớp; `app/main_routes.py` không còn; `wc -l app/routes/*.py` mọi file ≤ 250.
- `grep -rn "main_routes" app tests google_form_tool.spec wsgi.py` rỗng.
- Template render được (`tests/test_i18n_render.py`, `tests/test_form_copy_ui.py` xanh).

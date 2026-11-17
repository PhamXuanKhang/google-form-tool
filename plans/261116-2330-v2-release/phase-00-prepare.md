# Phase 0 — Chuẩn bị

Nhánh: `release/v2` (từ `master`).

## Bước

1. `git status` sạch, `git fetch`, `master` trùng `origin/master`. Tạo `release/v2`.
2. `uv sync --locked`. Lỗi (ví dụ Access denied trên `.venv`) → dừng hỏi user.
3. Baseline: `uv run python -m pytest -q` và `uv run ruff check app/ tests/ wsgi.py`. Ghi số
   test vào đầu `plans/reports/goal-run-261117-done.md` (bản nháp, hoàn thiện ở phase 8).
4. `gh auth status` và `git push -u origin release/v2` để chắc có quyền push. Không có quyền
   → dừng hỏi user.
5. Kiểm môi trường build: `node --version` (≥ 20), không có tiến trình `GoogleFormTool.exe`,
   port 5056 và 5123 trống (`netstat -ano`). Tiến trình lạ giữ port → không kill, dừng hỏi user.
6. Commit plan và brainstorm report nếu chúng còn untracked:
   `docs(plans): add release 2.0 plan and contract`.

## Điều kiện dừng

Bước 2, 3 hoặc 4 không đạt.

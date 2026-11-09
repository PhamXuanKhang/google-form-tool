# Phase 0 — Chuẩn bị

## Bước

1. Xác nhận user đã chạy `uv sync --locked` thành công (prereq). Kiểm: `uv sync --locked --dry-run`
   không còn thay đổi package nào.
2. `uv run python -m pytest -q` = `215 passed, 1 deselected`; `uv run ruff check app/ tests/ config.py wsgi.py` sạch.
   Nếu số khác baseline: ghi số thực làm baseline mới, không sửa test.
3. Commit tài liệu đang untracked lên `review`: `plans/260815-1543-phase-3-route-split/`,
   `plans/journals/2026-08-15-phase-2-root-cleanup-deps.md`,
   `plans/reports/brainstorm-261109-2340-product-review-simplify.md`, thư mục plan này.
   Message: `docs: add product simplification plans and phase 3 route split plan`.

## Rollback

Không có thay đổi code.

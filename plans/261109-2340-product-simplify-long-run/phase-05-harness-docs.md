# Phase 5 — Gộp harness + dọn docs

Nhánh: `refactor/harness-docs-cleanup` (từ nhánh phase 4).

## Bước (mỗi gạch đầu dòng lớn một commit)

1. `docs: collapse harness process docs into one workflow guide`
   - Tạo một doc ngắn (gợi ý `docs/WORKFLOW.md`, < 150 dòng): ba lane tiny/normal/high-risk,
     risk checklist, hard gates, nơi đặt story (`docs/product/user-stories.md`), decision
     (`docs/decisions/`), cách chạy test và packaging smoke.
   - Xoá: `docs/HARNESS.md`, `docs/HARNESS_MATURITY.md`, `docs/HARNESS_COMPONENTS.md`,
     `docs/HARNESS_BACKLOG.md`, `docs/TRACE_SPEC.md`, `docs/CONTEXT_RULES.md`,
     `docs/FEATURE_INTAKE.md` (nội dung vào doc mới), `scripts/schema/`, phần harness-cli
     trong `scripts/README.md`. Giữ `docs/templates/` nào doc mới còn trỏ tới; xoá phần còn lại.
   - `CLAUDE.md` và `AGENTS.md`: bỏ yêu cầu chạy `harness-cli` và `@docs/FEATURE_INTAKE.md`,
     trỏ sang doc mới. Giữ phần coding guidelines.
   - `.gitignore`: bỏ dòng `harness.db`, `scripts/bin/harness-cli.exe` chỉ khi chắc file local
     không còn được dùng; nếu nghi ngờ thì giữ.
   - `docs/GLOSSARY.md`, `docs/DETAILED_TEST_PLAN.md`, `docs/AGENT_CONTEXT.md`, `docs/TESTING.md`,
     `docs/README.md`: đọc từng file; giữ nếu còn đúng và có giá trị sản phẩm, gộp hoặc xoá phần
     chỉ nói về harness. Ghi lý do giữ/xoá vào commit body.
2. `docs: move refactor audit to plans reports` — `git mv docs/PROJECT_REFACTOR_AUDIT.md plans/reports/`.
3. `chore: refresh env example` — `.env.example`: bỏ "not yet integrated", sửa `DB_PATH`
   theo `Config` thực tế (đọc `app/config.py`), không thêm giá trị bí mật.
4. `docs: document landing as a separate deployable` — ghi chú trong `README.md` và
   `docs/ARCHITECTURE.md`; giữ placeholder URL (chưa có URL thật).

## Phạm vi file bổ sung

- `docs/decisions/0001-brownfield-harness-adoption.md`: bản ghi lịch sử, không viết lại;
  thêm dòng "Superseded by …" trỏ tới decision mới `docs/decisions/0003-collapse-harness.md`
  (ghi quyết định gộp harness). Cập nhật `docs/decisions/README.md`.
- `docs/product/README.md`, `docs/templates/story.md`: bỏ tham chiếu harness-cli.
- `docs/stories/`: user story giờ nằm ở `docs/product/user-stories.md`; chuyển 3 candidate epic
  trong `docs/stories/backlog.md` vào cuối file đó (mục "Backlog") rồi xoá `docs/stories/`.

## Kiểm

- `grep -rn "harness-cli\|HARNESS\|TRACE_SPEC\|FEATURE_INTAKE\|CONTEXT_RULES" --include=*.md . `
  trừ `plans/` và `docs/decisions/0001-*` rỗng.
- Mọi link markdown tương đối trong `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/` trỏ tới file tồn tại.
- pytest + ruff xanh; packaging smoke + `/healthz` 200.

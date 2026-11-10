---
title: "Product review + repo simplification (long run)"
description: "User stories theo use case, xoá code chết (4 route, app/monitoring, psutil), tách main_routes (Phase 3), domain/adapters (Phase 4), gộp harness. Chạy một mạch qua /goal."
status: completed
priority: P1
created: 2026-11-09
contract: plans/reports/brainstorm-261109-2340-product-review-simplify.md
---

# Product review + repo simplification

Outcome contract đã khoá trong goal packet (goal-warmup 2026-11-09). Plan này không
được đổi intended result, in scope, out of scope hay acceptance signals. Mọi đề xuất
đổi scope phải dừng lại hỏi user.

## Quy tắc chung (mọi phase)

- Kiểm thử: `uv run python -m pytest -q` + `uv run ruff check app/ tests/ config.py wsgi.py`
  (sau Phase 4 thay `config.py` bằng đường mới). Baseline: `215 passed, 1 deselected`.
  Số test chỉ giảm đúng bằng số test của phần bị xoá, và chỉ tăng bằng test snapshot mới
  (phase 3, 4); ghi baseline mới vào commit message mỗi khi số đổi.
- Git: mỗi phase một nhánh, nhánh sau tách từ nhánh trước (stack). Chỉ commit local,
  **không push, không mở PR**. Conventional commit, mỗi nhóm xoá một commit riêng.
- Packaging smoke ở **cuối mỗi phase** (A2, 3, 4, B):
  1. Trước build: không còn process `GoogleFormTool.exe`, port 5056 trống (`netstat -ano`).
  2. `$env:CI='true'; .\scripts\package-windows.ps1` — bắt buộc set `CI=true`, nếu không
     `build_exe.bat:93` dừng ở `pause` và run treo.
  3. Start `dist\GoogleFormTool\GoogleFormTool.exe` với `PORT=5056`,
     `GOOGLE_FORM_TOOL_NO_BROWSER=1`, ghi PID; `GET /healthz` phải trả 200 `{"status":"ok"}`;
     `taskkill /PID <pid>` rồi xác nhận port trống.
  4. `git status --porcelain`: revert thay đổi do build sinh ra (`package-lock.json`, `.mo`
     trừ khi phase cố ý sửa chuỗi i18n). Không commit `build/`, `dist/`, `release/`.
  5. Build cần network (tải electron/npm) và lỗi mạng → điều kiện dừng.
- Không làm yếu, skip hay xoá test để qua gate. Test chỉ được xoá khi nó kiểm phần bị retire.
- Không ghi plan ID, phase number vào code comment, tên test, commit message.

## Phases

| # | Phase | Nhánh | File |
|---|-------|-------|------|
| 0 | Chuẩn bị | `review` | [phase-00](./phase-00-prepare.md) |
| 1 | User stories (Track A1) | `refactor/product-user-stories` | [phase-01](./phase-01-user-stories.md) |
| 2 | Xoá code chết (Track A2) | `refactor/remove-dead-routes-monitoring` | [phase-02](./phase-02-remove-dead-code.md) |
| 3 | Tách routes (Phase 3 cũ) | `refactor/phase-3-route-split` | [phase-03](./phase-03-route-split.md) |
| 4 | Domain/adapters | `refactor/phase-4-domain-adapters` | [phase-04](./phase-04-domain-adapters.md) |
| 5 | Gộp harness + docs (Track B) | `refactor/harness-docs-cleanup` | [phase-05](./phase-05-harness-docs.md) |

Thứ tự bắt buộc 0 → 5.

## Traceability

| Phase | Contract items | Acceptance signals | Facts / assumptions / prereqs / decisions |
|---|---|---|---|
| 0 | Tiền đề cho mọi item | `uv sync --locked` thành công; baseline 215 passed | Fact: `.venv` lệch `uv.lock`, `uv sync` lỗi Access denied (prereq của user). Fact: plan Phase 3 + report đang untracked |
| 1 | In scope 1 | `docs/product/user-stories.md` ~8 story, 3–5 AC mỗi story, trạng thái; `TEST_MATRIX.md` trỏ story | Decision: Form copy keep; Landing keep; resource display retire. Assumption: 10 dòng TEST_MATRIX đủ làm khởi điểm |
| 2 | In scope 2 | 4 route + `app/monitoring/` + panel + `psutil` không còn; pytest xanh; smoke PASS; `.spec` không `psutil`/`app.monitoring` | Fact: 4 route không caller ngoài `submission.js:254`; `generate_responses_batch` chỉ route chết gọi (`main_routes.py:550`) |
| 3 | In scope 3 | Snapshot route còn lại khớp 100%; `main_routes.py` biến mất; route file ≤ 250 dòng; `.spec` không `app.main_routes`; smoke PASS | Plan chi tiết: `plans/260815-1543-phase-3-route-split/` (sửa theo tập route mới ở bước đầu phase) |
| 4 | In scope 4 | `grep -rl selenium app/domain/` rỗng; `config.py` → `app/config.py`; snapshot khớp; smoke PASS | Fact: Selenium ở `driver_manager`, `form_copier`, `form_extractor`, `form_submitter`; `from config import` ở 10 file; `.spec:25 pathex=["."]` |
| 5 | In scope 5 | Một doc harness; `CLAUDE.md`/`AGENTS.md` hết yêu cầu `harness-cli`; audit chuyển `plans/reports/`; `.env.example` đúng; `landing/` ghi chú; link docs không gãy; smoke PASS | Decision: collapse harness, giữ ba lane intake |

## Điều kiện dừng

Hoàn thành khi mọi acceptance signal ở bảng trên đạt và phase 5 có smoke PASS.

Dừng sớm khi:
- Phase 0 bước 1 hoặc 2 không đạt.
- Một gate (pytest, ruff, snapshot, smoke) vẫn đỏ sau 3 lần sửa.
- Phát hiện caller ngoài của route sắp xoá, hoặc cần quyết định sản phẩm chưa có trong contract.
- Lỗi network khi build.

Khi dừng: để nguyên nhánh và commit đã có (không `reset --hard`, không xoá nhánh), commit
WIP nếu working tree có thay đổi hợp lệ, viết
`plans/reports/goal-run-261110-stopped.md` gồm phase, lệnh lỗi, output đã lọc secret, các bước
đã thử và câu hỏi cho user. Khi hoàn thành: viết `plans/reports/goal-run-261110-done.md`
gồm danh sách nhánh, commit, số test cuối, kết quả 4 lần smoke.

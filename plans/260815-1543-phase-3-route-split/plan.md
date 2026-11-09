---
title: "Phase 3 Route Split"
description: "Tách app/main_routes.py (1215 dòng, 26 route) thành app/routes/*.py mỏng + app/services/*.py cho state, không đổi URL/contract/hành vi. Snapshot 30 route trước-sau, packaging smoke gate bắt buộc."
status: pending
priority: P1
effort: "2-3d"
tags: [refactor, routes, high-risk, phase-3]
created: 2026-08-15
blockedBy: [260815-1509-phase-2-root-cleanup-deps]
---

> **Adjustment (2026-11-10):** four routes were retired before this phase (`/generate_response`,
> `/ai_status`, `/system_status`, `/monitoring_history`). The route set is now 22, there is no
> `monitoring.py` module, and `ai.py` holds only `/validate_api_key` and `/generate_ai_text_answers`.
> That leaves 7 route modules: `health, pages, forms, data, ai, submissions, history`. Read "30 route"
> and "8 module" below as "22 route" and "7 module". Baseline test count comes from the live run.
> The sibling `phase-0*.md` files are placeholders and are not used.

# Phase 3 Route Split

Phase 3 của kế hoạch tái cấu trúc 4 phase (kế hoạch tổng). Contract gốc:
`plans/reports/brainstorm-260815-1115-repo-restructure.md` (acceptance Phase 3, dòng 43;
kế hoạch phase dòng 107). Phase 1 (test isolation) và Phase 2 (root cleanup + deps)
đã `done`. Đây là phase **high-risk** theo `docs/FEATURE_INTAKE.md` (đổi public
contract + blast radius rộng).

## Overview

`app/main_routes.py` gộp 1215 dòng: 26 route decorator + state toàn cục (upload cache,
submission registry) + orchestration (`_run_submission` thread) + sinh export CSV/JSON
ngay trong handler. Vi phạm ranh giới `docs/ARCHITECTURE.md:24` (route chỉ validate +
delegate). Phase này **tách** file thành route mỏng trong `app/routes/*.py` và state/logic
chạy trong `app/services/*.py`, **không đổi** URL, request/response shape, hành vi UI,
hay endpoint name.

> Quy ước đọc: "Phase 1-6" trong file này là **các bước bên trong plan này**. Các bước
> của kế hoạch tái cấu trúc lớn luôn gọi rõ là "kế hoạch tổng".

## Ràng buộc bất di bất dịch (từ contract kế hoạch tổng)

- **Không đổi URL, method, status, JSON shape.** 30 route giữ nguyên contract 100%.
- **Endpoint name giữ nguyên `main.*`.** Template dùng `url_for('main.<func>')` khắp nơi;
  đổi tên endpoint = vỡ UI im lặng. → Dùng **một blueprint dùng chung** (không tách thành
  nhiều blueprint). Xem DD-1.
- **`google_form_tool.spec` hiddenimports** cập nhật đồng bộ: bỏ `app.main_routes`, thêm
  8 module `app.routes.*` + 3 module `app.services.*` mới. Quên = pytest xanh, CI xanh,
  chỉ installer crash lúc runtime (contract dòng 98-99).
- **Packaging smoke là gate bắt buộc**, không phải tuỳ chọn: backend đóng gói trả
  `/healthz` ok (contract dòng 43).
- `main_routes.py` phải **biến mất** hoàn toàn.
- Không file route nào **> 250 dòng**.

## Design Decisions

### DD-1: Một blueprint dùng chung, không tách nhiều blueprint

`app/main_routes.py:27` định nghĩa `bp = Blueprint('main', __name__)`; toàn bộ 26 route
gắn `@bp.route`. Endpoint là `main.index`, `main.start_submission`… Template + JS dùng
`url_for('main.*')`. Nếu mỗi module route tạo blueprint riêng (`pages_bp`, `ai_bp`…),
endpoint đổi thành `pages.index`… → mọi `url_for('main.*')` vỡ.

**Chọn:** khai báo blueprint dùng chung `bp = Blueprint('main', __name__)` trong
`app/routes/__init__.py`; mỗi module `app/routes/*.py` `from app.routes import bp` rồi
`@bp.route(...)`. Registration `app/__init__.py:102` đổi `from app.main_routes import bp`
→ `from app.routes import bp` (phải import các module con để decorator chạy). Endpoint
name **không đổi** → `url_for` không đổi → 0 template churn. Đây là cách giữ acceptance
"snapshot 30 route khớp 100%".

### DD-2: Thứ tự tách — services trước, routes sau

Coupling map Phase 1 (`plans/260815-1127-phase-1-test-isolation/phase-04-verification-and-coupling-map.md`)
xác định 23 test chạm symbol nội bộ `main_routes`. 3 file gánh gần hết rủi ro
(`test_prefill_submission.py` 7, `test_submission_persistence.py` 5,
`test_submission_status_retention.py` 5) đều bám `active_submitters`, `_run_submission`,
`_upload_cache`, `_cleanup_finished_submitters`. Vì vậy **tách state ra services trước**
(Phase 2 trong plan này), rồi route (Phase 3), rồi migrate test (Phase 4). Tách state
trước cho phép chuyển 3 file test nặng ngay khi symbol có nhà mới.

### DD-3: Snapshot 30 route TRƯỚC khi tách (gate cứng)

Contract dòng 43 yêu cầu "snapshot 30 route (path/method/status/JSON shape) khớp 100%
trước-sau". Snapshot này **chưa tồn tại** (contract dòng 114). Phase 1 (plan này) tạo
harness snapshot chạy trên `main_routes.py` gốc, lưu baseline. Mọi phase tách sau đó
re-chạy harness so với baseline. Không có snapshot xanh → không được tách.

## Phân bổ route → module (từ scout live main_routes.py)

`app/routes/` (route mỏng, mục tiêu < 250 dòng/file):

| Module | Route (dòng hiện tại) |
|---|---|
| `health.py` | `/healthz` (121), `/diagnostics/runtime` (147) |
| `pages.py` | `/` (152), `/form_filling` GET (197), `/about` (210), `/settings/diagnostics` (220), `/form_copy` (229) |
| `forms.py` | `/forms/delete` (181), `/form_copy/extract_source` (254), `/form_copy/preview_plan` (298), `/form_copy/apply_to_target` (315), `/form_filling/extract` (349), `/form_filling/preview` (417) |
| `data.py` | `/load_data` (442), `/save_edit` (712) |
| `ai.py` | `/generate_response` (517), `/validate_api_key` (570), `/generate_ai_text_answers` (621), `/ai_status` (697) |
| `submissions.py` | `/start_submission` (845), `/stop_submission` (1009), `/submission_status` (1042) |
| `history.py` | `/submission_history/<form_id>` (1067), `/export_history/<form_id>` (1105) |
| `monitoring.py` | `/system_status` (1173), `/monitoring_history` (1194) |

`app/services/` (state + logic tách khỏi tầng route):

| Module | Nội dung tách (dòng hiện tại) | Symbol test bám |
|---|---|---|
| `upload_cache.py` | `_upload_cache` + TTL eviction + lock (29-118); patch point `time.monotonic` | `_upload_cache` (3), `time` (1) |
| `submission_manager.py` | `active_submitters` (757), `_run_submission` (975), `_cleanup_finished_submitters` | `active_submitters` (6), `_run_submission` (5), `_cleanup_finished_submitters` (2) |
| `history_export.py` | sinh CSV/JSON export (1105-1170) | — |

`/diagnostics/runtime` bám `_runtime_mode` + `sys.frozen` → về `app/routes/health.py`
(coupling map). `Config.MAX_UPLOAD_ROWS` để nguyên (đi Phase 4 kế hoạch tổng cùng `config.py`).

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Snapshot harness 30 route (gate cứng)](./phase-01-start.md) | Pending |
| 2 | [Phase 2: Tách state ra app/services](./phase-02-extract-services-state.md) | Pending |
| 3 | [Phase 3: Tách route ra app/routes](./phase-03-split-routes-into-modules.md) | Pending |
| 4 | [Phase 4: Migrate test + cập nhật .spec](./phase-04-migrate-tests-and-spec.md) | Pending |
| 5 | [Phase 5: Packaging smoke gate](./phase-05-packaging-smoke-gate.md) | Pending |
| 6 | [Phase 6: Nghiệm thu + decision record](./phase-06-verification-and-decision-record.md) | Pending |

Thứ tự bắt buộc: 1 → 2 → 3 → 4 → 5 → 6. Một nhánh + 1 PR: `refactor/phase-3-route-split`
(quyết định 4 kế hoạch tổng).

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Snapshot 30 route khớp 100% trước-sau (path/method/status/JSON shape) | P1 |
| 2 | `main_routes.py` biến mất; route nằm trong `app/routes/*.py`, endpoint vẫn `main.*` | P1 |
| 3 | State ra `app/services/{upload_cache,submission_manager,history_export}.py` | P1 |
| 4 | Không file route > 250 dòng | P1 |
| 5 | `.spec` hiddenimports cập nhật; packaging smoke PASS + backend đóng gói trả `/healthz` | P1 |
| 6 | 215 passed, 1 deselected giữ nguyên baseline; ruff sạch | P1 |
| 7 | Decision record cho việc tách blueprint + boundary mới | P2 |

## Scope

**Trong phạm vi**

- Tạo `app/routes/__init__.py` (blueprint dùng chung) + 8 module route.
- Tạo `app/services/{upload_cache,submission_manager,history_export}.py`.
- Xoá `app/main_routes.py`; sửa registration `app/__init__.py:31,102`.
- Migrate 23 coupling test (5 file) sang import symbol từ nhà mới.
- Cập nhật `google_form_tool.spec` hiddenimports (bỏ `app.main_routes`, thêm module mới).
- Tạo harness snapshot 30 route (test file mới, giữ lại trong repo).
- Decision record `docs/decisions/NNNN-route-split.md`.
- Cập nhật `docs/ARCHITECTURE.md` nếu mô tả boundary route hiện tại đã sai sau tách.

**Ngoài phạm vi**

- Không đổi URL, method, status, JSON shape, endpoint name, hành vi UI.
- Không tách `app/core/` → `app/domain/` + `app/adapters/` (Phase 4 kế hoạch tổng).
- Không di chuyển `config.py` → `app/config.py` (Phase 4 kế hoạch tổng); `Config.MAX_UPLOAD_ROWS` để nguyên.
- Không sửa logic Selenium / AI / storage.
- Không thêm feature, không tối ưu hiệu năng, không dọn dead code có sẵn.
- Không giải `harness.db` (non-goal kế hoạch tổng).

## Success Criteria

- [ ] Snapshot 30 route: path/method/status/JSON shape khớp 100% baseline (harness xanh)
- [ ] `app/main_routes.py` không còn tồn tại
- [ ] `grep -rn "url_for('main\." app/templates` vẫn resolve (endpoint `main.*` giữ nguyên)
- [ ] `wc -l app/routes/*.py` — mọi file ≤ 250 dòng
- [ ] `_upload_cache`, `active_submitters`, `_run_submission`, `_cleanup_finished_submitters` nằm trong `app/services/*.py`
- [ ] 23 coupling test migrate xong; `grep -rn "main_routes\.[A-Za-z_]*" tests/*.py` = 0
- [ ] `uv run python -m pytest -q` = 215 passed, 1 deselected
- [ ] `uv run ruff check app/ tests/ config.py wsgi.py` sạch
- [ ] `.spec` không còn `app.main_routes`; có đủ 8 `app.routes.*` + 3 `app.services.*` mới
- [ ] Packaging smoke PASS; backend đóng gói trả `/healthz` 200
- [ ] Decision record được ghi (`docs/decisions/`) + `ak decision add` nếu CLI có

## Risks

| Rủi ro | Tín hiệu phát hiện | Phản ứng đã định |
|---|---|---|
| Tách blueprint làm đổi endpoint name → `url_for` vỡ | Snapshot route lệch, hoặc template 500 lúc render | Dùng blueprint dùng chung (DD-1); snapshot chạy trước-sau mỗi phase tách |
| `.spec` hiddenimports quên module mới → installer crash runtime | pytest/CI xanh nhưng backend đóng gói không import được route | Packaging smoke gate bắt buộc (Phase 5); grep `.spec` đối chiếu danh sách module |
| Circular import khi module route import service, service import lại | `uv sync`/app khởi động `ImportError` | Blueprint trong `app/routes/__init__.py`; service không import route; import module con ở cuối `__init__` |
| State toàn cục (single-process) đứt khi chuyển module | Test submission persistence/retention fail | Chuyển nguyên `active_submitters`/`_upload_cache` thành module-level singleton trong service, giữ ngữ nghĩa single-process |
| Số coupling khác 23 khi bắt đầu (bản đồ lỗi thời) | `grep -rn "main_routes\.[A-Za-z_]*" tests/*.py` ≠ 23 | Coi grep là nguồn sự thật; cập nhật danh sách migrate theo grep thực |
| Snapshot 30 route không phủ hết edge (auth, error shape) | Route lỗi lọt qua snapshot | Snapshot cả status code + JSON keys cho cả happy path lẫn lỗi validate chính |
| PyInstaller không chạy được trên máy nghiệm thu (không Windows) | Không build được smoke | Ghi là gate Windows; không merge nếu smoke chưa PASS trên Windows |

## References

- Contract: `plans/reports/brainstorm-260815-1115-repo-restructure.md` (acceptance dòng 43; phase dòng 107; ràng buộc endpoint/`.spec` dòng 96-99)
- Coupling map: `plans/260815-1127-phase-1-test-isolation/phase-04-verification-and-coupling-map.md`
- Phase 2 (blockedBy): `plans/260815-1509-phase-2-root-cleanup-deps/plan.md`
- Blueprint: `app/main_routes.py:27` (`bp = Blueprint('main', __name__)`); registration `app/__init__.py:31,102`
- `.spec` hiddenimports: `google_form_tool.spec:80-92`
- Boundary chuẩn: `docs/ARCHITECTURE.md:24`

<!-- slug: phase-3-route-split -->

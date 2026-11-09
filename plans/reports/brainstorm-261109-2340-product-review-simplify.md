# Brainstorm — Rà soát product + đơn giản hoá repo

Date: 2026-11-09
Branch at capture: `review`
Mode: `--advice` (kongming đã duyệt hướng đi: go, có giới hạn thời gian)
Status: contract accepted, ready for plan

Mở rộng contract `plans/reports/brainstorm-260815-1115-repo-restructure.md`.
Phase 1, 2 đã xong; Phase 3 (`plans/260815-1543-phase-3-route-split/`) chưa chạy.
Contract cũ coi "viết spec sản phẩm" là non-goal; đợt này kéo nó vào scope.

## Contract

### Outcome

Mỗi tính năng còn lại trong repo đều gắn với một user story có acceptance criteria
và trạng thái keep/change/retire. Code, route, dependency và process docs không
phục vụ story nào thì bị xoá. Sau đó Phase 3 và 4 chạy trên tập route đã thu gọn,
theo layout layer đã chốt (`routes/services/domain/adapters`).

### Constraints

- Route còn giữ lại không đổi URL, method, status, JSON shape, endpoint `main.*`.
- Mỗi lần xoá là một commit riêng; full pytest xanh trước và sau.
- Mọi thay đổi chạm module được đóng gói (`google_form_tool.spec` hiddenimports,
  dependency) kết thúc bằng packaging smoke + backend đóng gói trả `/healthz`.
- Track A có giới hạn thời gian: đầu ra duy nhất Phase 3 cần là danh sách route
  cuối cùng. Có danh sách đó thì sửa plan Phase 3 rồi chạy, không chờ docs hoàn hảo.
- Giữ layout layer (quyết định đã chốt, kongming đồng ý). Đặt tên file route và
  service theo tính năng (`routes/submissions.py`, `services/history_export.py`).

### Non-goals

- Không rewrite sang feature-folder (`app/features/*`).
- Không thêm tính năng, không đổi UI ngoài phần bị retire.
- Không gỡ script inline khỏi template (Phase 6 cũ vẫn ngoài scope).
- Không tách `landing/` ra repo riêng.

### Acceptance criteria

| Track | Bằng chứng |
| --- | --- |
| A — Product | `docs/product/user-stories.md` có khoảng 8 story (khởi điểm là 10 dòng `docs/TEST_MATRIX.md`), mỗi story 3–5 acceptance criteria + trạng thái; `TEST_MATRIX.md` trỏ tới đúng story |
| A — Xoá code | `/generate_response`, `/ai_status`, `/monitoring_history`, `/system_status` không còn; `app/monitoring/` không còn; panel tài nguyên trong `submission.js` gỡ; `psutil` khỏi `pyproject.toml`, `uv.lock`, `.spec`; không còn orphan (`AIResponder.generate_responses_batch` nếu chỉ route chết dùng); pytest xanh; packaging smoke PASS |
| B — Repo | Harness gộp còn 1 doc ngắn giữ intake lanes; xoá `HARNESS.md`, `HARNESS_MATURITY.md`, `HARNESS_COMPONENTS.md`, `TRACE_SPEC.md`, `scripts/schema/`, yêu cầu chạy `harness-cli` trong `CLAUDE.md`/`AGENTS.md`; `PROJECT_REFACTOR_AUDIT.md` chuyển sang `plans/reports/`; `.env.example` hết dòng stale; `landing/` ghi rõ là deployable riêng |
| Phase 3/4 | Như contract cũ, nhưng snapshot trên tập route đã thu gọn (26 − 4 = 22 decorator; số đếm thực lấy từ grep lúc chạy) |

## Quyết định đã chốt (user, 2026-11-09)

| # | Quyết định | Chọn |
| --- | --- | --- |
| 1 | Harness layer | Gộp thành 1 doc ngắn, giữ intake lanes, bỏ CLI/trace/maturity/SQL |
| 2 | Hiển thị tài nguyên khi submit | Retire: xoá `app/monitoring/`, `/system_status`, panel UI, `psutil` |
| 3 | Form copy MVP | Giữ nguyên, viết user story kèm giới hạn hiện có |
| 4 | `landing/` | Giữ trong repo, ghi là deployable riêng, sửa URL placeholder khi deploy |
| 5 | Thứ tự | Track A trước Phase 3; Track B sau khi Phase 3 merge |
| 6 | Layout | Giữ layer, không feature-folder |

## Trade-offs

- **Product review trước Phase 3 (chọn):** dựa vào giả định không client ngoài
  nào gọi 3 route chết. Hỏng đầu tiên khi Electron hoặc script build URL động —
  kiểm bằng grep `electron/` và packaging smoke.
- **Phase 3 trước rồi review:** rẻ về lịch nhưng snapshot và di chuyển code chết,
  rồi phải sửa snapshot lần nữa.
- **Feature-folder:** dựa vào giả định các tính năng ít chia sẻ code. Sai ở đây:
  form copy, submit, AI cùng dùng model Form/Question, Selenium extraction, storage.

Better approaches: none ngoài điều chỉnh thứ tự — hướng user yêu cầu là đúng
(bằng chứng: 4 route không caller UI, 3 trong số đó không test; ~1.800 dòng
process docs trong khi `docs/product/` rỗng).

## Bằng chứng nền

- Route không caller UI và không test: `app/main_routes.py:517` `/generate_response`,
  `:697` `/ai_status`, `:1194` `/monitoring_history`.
- `/system_status` (`:1173`) chỉ do `app/static/js/form_filling/submission.js:254`
  gọi; test `tests/test_monitoring_routes.py:37` sẽ xoá theo.
- `psutil` chỉ dùng trong `app/monitoring/*` (`pyproject.toml:19`, `google_form_tool.spec:53`).
- `scripts/bin/harness-cli.exe` và `harness.db` bị `.gitignore` (dòng 40, 44) nên
  clone sạch không chạy được CLI mà `CLAUDE.md` yêu cầu.
- `.env.example` ghi Gemini "not yet integrated" và `DB_PATH=app/services/db.json`
  — cả hai stale.

## Thứ tự thực thi đề xuất

1. Track A1: viết `docs/product/user-stories.md`, chốt danh sách route giữ lại.
2. Track A2: xoá 4 route + `app/monitoring/` + panel UI + `psutil` (commit riêng từng nhóm), packaging smoke.
3. Sửa `plans/260815-1543-phase-3-route-split/plan.md` theo route mới (bỏ module `monitoring.py`, giảm snapshot), rồi chạy Phase 3.
4. Phase 4 như contract cũ.
5. Track B: gộp harness, dọn docs, `.env.example`, ghi chú `landing/`.

## Rủi ro chưa khép

1. Scope creep trên nhiều mặt trận cùng lúc với một người bảo trì. Giảm thiểu: Track B chờ Phase 3 merge.
2. Module chỉ được nạp qua dynamic import hoặc PyInstaller hiddenimports. Giảm thiểu: packaging smoke sau mỗi đợt xoá.
3. Track A biến thành dự án viết docs. Giảm thiểu: trần ~8 story, khởi điểm từ TEST_MATRIX.

## Handoff

Next: `/ak:plan --advice` cho Track A, rồi sửa plan Phase 3, rồi `/ak:cook --advice` từng phase.

# Brainstorm — Repo restructure (Phase 1–4)

Date: 2026-08-15
Branch at capture: `review`
Status: contract accepted, ready for plan

## Contract

### Outcome

Ranh giới kiến trúc khớp `docs/ARCHITECTURE.md`: route mỏng trong `app/routes/*`,
logic thuần trong `app/domain/`, I/O ngoài trong `app/adapters/`, state chạy trong
`app/services/`. Dependency quản lý bằng `pyproject.toml` + `uv.lock`. Docker gỡ
hoàn toàn. Test chạy trong sandbox không cần elevation và không đụng dữ liệu thật
của người dùng.

### Constraints

- Không đổi URL, request/response shape, hành vi UI. 30 route giữ nguyên contract.
- `google_form_tool.spec` cập nhật đồng bộ ở mọi phase di chuyển module; packaging
  smoke là gate bắt buộc, không phải tuỳ chọn.
- Gate version `package.json` <-> `app/__init__.py` (`release.yml:78-88`) giữ nguyên.
  `pyproject.toml` dùng `dynamic = ["version"]`, không hard-code version.
- Đường packaging đã PASS (`scripts/package-windows.ps1` -> `build_exe.bat` ->
  PyInstaller -> electron-builder) không đổi kiến trúc.
- Windows-first; script mới chạy được trên PowerShell.
- Phase 1 trước Phase 3. ~20 file test đang patch theo tên module `app.main_routes`.

### Non-goals

- Phase 5 (tái cấu trúc `docs/`, viết spec sản phẩm 9 feature) và Phase 6 (gỡ script
  inline khỏi template). Docs chỉ cập nhật phần bị Phase 1–4 ảnh hưởng.
- `harness.db` là nguồn sự thật cục bộ — không giải quyết đợt này.
- Không thêm feature, không tối ưu hiệu năng, không đổi UI, không dọn dead code có sẵn.
- Không versioned REST API, không tách frontend.

### Acceptance criteria

| Phase | Bằng chứng |
| --- | --- |
| 1 | 215 test PASS; pytest chạy trong sandbox không cần elevation; `%APPDATA%\GoogleFormTool\db.json` không đổi mtime sau full suite; 0 lần `monkeypatch.setattr(main_routes, "get_storage_service"` còn lại |
| 2 | `uv sync` từ clone sạch thành công; `uv.lock` commit; pip-audit gate còn chạy; CI xanh; Docker files xoá, không còn tham chiếu |
| 3 | Snapshot 30 route (path/method/status/JSON shape) khớp 100% trước-sau; `main_routes.py` biến mất; không file route > 250 dòng; packaging smoke PASS + backend đóng gói trả `/healthz` ok |
| 4 | `grep -rl selenium app/domain/` rỗng; nhóm test domain < 2s không mock Selenium; packaging smoke PASS lần 2; `npx gitnexus analyze --force` re-index sạch |

## Quyết định đã chốt

| # | Quyết định | Chọn |
| --- | --- | --- |
| 1 | Docker lane | Bỏ hẳn: `Dockerfile`, `docker-compose.yml`, `.dockerignore` |
| 2 | Dependency management | `pyproject.toml` + `uv.lock` commit; xoá hẳn `requirements.txt` |
| 3 | Phạm vi | Phase 1–4 đầy đủ |
| 4 | Nhánh | Nhánh mới mỗi phase: `refactor/phase-{n}-{slug}`, 1 PR/phase |
| 5 | `config.py` | Chuyển `config.py` -> `app/config.py`, kèm `TestConfig` |

Lý do chọn uv.lock (quyết định 2): sản phẩm phát hành binary có checksum
(`SHA256SUMS.txt`), nên reproducible build là thuộc tính sản phẩm chứ không phải
sở thích tooling. Không lock thì cùng một commit có thể build ra hành vi Selenium
khác nhau giữa hai lần release.

## Bằng chứng nền

Vi phạm boundary (`docs/ARCHITECTURE.md:24` yêu cầu route chỉ validate + delegate):

- `app/main_routes.py:29-118` — upload cache + TTL eviction + lock.
- `app/main_routes.py:757-841` — submission registry toàn cục, validate numeric, TTL cleanup.
- `app/main_routes.py:975` — `_run_submission()` orchestration thread trong tầng route.
- `app/main_routes.py:1105-1170` — sinh CSV/JSON export trong handler.
- `app/main_routes.py:466-490` — temp file + parse mapping JSON.

Test không cách ly:

- `app/__init__.py:80` — `create_app(testing=True)` chỉ set `TESTING`, không override
  `DB_PATH`/`LOG_DIR`.
- `app/services/__init__.py:7` — `get_storage_service()` đọc thẳng `Config.DB_PATH`
  (`%APPDATA%\GoogleFormTool\db.json`).
- ~20 file test bù bằng `monkeypatch.setattr(main_routes, "get_storage_service", ...)`.
- `docs/PROJECT_REFACTOR_AUDIT.md:60` đã ghi nhận `PermissionError` khi ghi
  `%APPDATA%\GoogleFormTool\logs\app.log` trong sandbox.

State toàn cục: `app/main_routes.py:29` (`_upload_cache`), `:757` (`active_submitters`).
Ràng buộc single-process này chưa được ghi ở docs nào.

`app/core/` trộn 2 nhóm — thuần logic: `form_processor.py`, `prefill_link_generator.py`,
`form_copy_planner.py`; có Selenium: `form_extractor.py`, `form_submitter.py`,
`form_copier.py`, `driver_manager.py`; có network: `ai_responder.py`.

uv đã là chuẩn thực tế, chỉ thiếu `pyproject.toml`: `release.yml:120-127`,
`build_exe.bat:86,100`, `scripts/run_local.ps1:25`, `README.md:89`.

## Hai điều chỉnh so với review ban đầu

1. `build_exe.bat` KHÔNG xoá được — `scripts/package-windows.ps1:6,40` gọi nó để build
   backend sidecar. Sau khi có `pyproject.toml`, nhánh `if exist pyproject.toml ->
   uv sync` (`build_exe.bat:73-78`) chuyển từ dead branch thành đường chạy đúng.
2. `google_form_tool.spec` `hiddenimports` liệt kê module path cứng (`app.main_routes`,
   `app.core.form_extractor`, `app.core.form_submitter`, `app.core.form_processor`,
   `app.core.ai_responder`, `app.core.prefill_link_generator`, `app.services.storage_service`).
   Quên sửa -> pytest xanh, CI xanh, chỉ installer crash lúc runtime.

## Kế hoạch phase

| # | Phase | Lane | Nội dung |
| --- | --- | --- | --- |
| 1 | Test isolation | normal | `TestConfig` (temp DB + temp LOG_DIR); storage provider qua `app.extensions`; fixture chung trong `tests/conftest.py`; gỡ ~20 monkeypatch lặp |
| 2 | Root cleanup + deps | normal | `pyproject.toml` (dynamic version) + `uv.lock`; gộp pytest/ruff config; xoá Docker 3 file, `requirements.txt`, `.agents/`, `.codex/`, `tests/test_resource.md`; gộp CLAUDE.md vào AGENTS.md; sửa CI/release sang uv; pip-audit qua `uv export`; sửa README onboarding |
| 3 | Tách routes | high-risk | Snapshot test 30 route TRƯỚC khi tách; `main_routes.py` -> `app/routes/{health,pages,forms,data,ai,submissions,history,monitoring}.py`; state ra `app/services/{upload_cache,submission_manager,history_export}.py`; cập nhật `.spec`; decision record |
| 4 | Domain/adapter | normal | `app/core/` -> `app/domain/` + `app/adapters/{browser,ai}/`; `config.py` -> `app/config.py` (11 import site + `.spec` pathex); marker pytest cho nhóm domain; cập nhật `.spec`; GitNexus re-index |

## Rủi ro chưa khép

1. PyInstaller hiddenimports — pytest/CI không bắt được. Giảm thiểu: mỗi phase di
   chuyển module kết thúc bằng packaging smoke thật.
2. Snapshot 30 route chưa tồn tại. Phase 3 phải tạo trước khi tách — công việc phát
   sinh thật, không có sẵn.
3. `from config import Config` ở 11 vị trí + `pathex=["."]` trong `.spec`.
4. Phase 3 và 4 là high-risk theo `docs/FEATURE_INTAKE.md`: chạy `gitnexus_impact`
   trước từng symbol, `gitnexus_detect_changes` trước commit.

## Handoff

Next: plan skill -> `/ak:cook` từng phase. Nhánh `refactor/phase-1-test-isolation` trước.

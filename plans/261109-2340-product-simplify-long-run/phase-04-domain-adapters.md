# Phase 4 — Domain / adapters + config

Nhánh: `refactor/phase-4-domain-adapters` (từ nhánh phase 3).

## Phân bổ

| Từ `app/core/` | Đến |
|---|---|
| `form_processor.py`, `prefill_link_generator.py`, `form_copy_planner.py` | `app/domain/` |
| `form_extractor.py`, `form_submitter.py`, `form_copier.py`, `driver_manager.py` | `app/adapters/browser/` |
| `ai_responder.py` | `app/adapters/ai/` |

`app/core/` biến mất. Nếu một module domain đang import Selenium hoặc module adapter
(phát hiện qua grep), tách phần đó ra adapter thay vì để domain phụ thuộc Selenium.

## Commit

1. `refactor(config): move config.py into app package` — `config.py` → `app/config.py`;
   sửa 10 import site (`app/__init__.py`, `app/logging_config.py`, `app/services/__init__.py`,
   các module core, route modules, `tests/conftest.py`, `tests/test_runtime_config.py`,
   `tests/test_runtime_diagnostics_route.py`); kiểm `wsgi.py`, `build_exe.bat`,
   `.spec` (`pathex`, datas) và `pyproject.toml` (ruff/pytest paths) còn đúng.
2. `refactor(domain): split core into domain and adapters` — `git mv` theo bảng trên; sửa
   import ở routes, services, tests (cả `monkeypatch.setattr` theo chuỗi đường dẫn);
   cập nhật `.spec` hiddenimports: bỏ mọi `app.core.*`, thêm package `app.domain`,
   `app.adapters`, `app.adapters.browser`, `app.adapters.ai` và đủ 8 module đã chuyển
   (kể cả `form_copier`, `form_copy_planner` vốn chưa có trong `.spec`).
3. Thêm marker pytest `domain` trong `pyproject.toml` cho test của 3 module domain;
   `uv run python -m pytest -q -m domain` chạy < 2s. Không yêu cầu "không import Selenium" ở
   runtime: `tests/conftest.py` và `app/__init__.py` nạp route nên Selenium vẫn được import;
   đổi điều đó là ngoài scope.

## Kiểm

- `grep -rl selenium app/domain/` rỗng; `grep -rn "app.core\|from config import" app tests wsgi.py google_form_tool.spec` rỗng.
- Snapshot route từ phase 3 vẫn khớp.
- `docs/ARCHITECTURE.md` cập nhật đường dẫn mới.
- Packaging smoke + `/healthz` 200.

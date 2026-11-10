---
phase: 1
title: "pyproject + uv.lock + config gộp"
status: done
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: pyproject + uv.lock + config gộp

## Overview

Tạo `pyproject.toml` (dynamic version, runtime deps, dev group, gộp cấu hình
`ruff` + `pytest`), sinh và commit `uv.lock`, rồi xoá `requirements.txt`,
`pytest.ini`, `ruff.toml`.

## Requirements

**Functional**

- `uv sync` từ clone sạch tạo môi trường đủ chạy app + test + build.
- Version pyproject suy ra động từ `app/__init__.py:__version__` (không hard-code).
- Cấu hình lint/test đọc từ `pyproject.toml` (một nguồn), hành vi giữ nguyên.

**Non-functional**

- Không đổi tập dependency runtime. Pin nào đang cứng thì giữ cứng.

## Architecture

`pyproject.toml`:

- `[build-system]` = `hatchling` (DD-1).
- `[project]`: `name`, `requires-python = ">=3.11"`, `dynamic = ["version"]`,
  `dependencies` chép nguyên từ `requirements.txt` (giữ pin).
- `[tool.hatch.version] path = "app/__init__.py"` → đọc `__version__`.
- `[tool.hatch.build.targets.wheel] packages = ["app"]`.
- `[dependency-groups] dev = ["pytest==8.4.0", "ruff", "pyinstaller", "pip-audit"]`
  (DD-2). `pytest` giữ pin như `requirements.txt`.
- `[tool.pytest.ini_options]`: chép từ `pytest.ini` (`addopts`, `markers`).
- `[tool.ruff]`: `line-length = 100`, `extend-exclude`; `[tool.ruff.lint] select = ["E9","F"]`
  (chép từ `ruff.toml`, đổi `[lint]` → `[tool.ruff.lint]`).

Deps runtime (từ `requirements.txt`): `Flask==3.1.0`, `selenium==4.32.0`,
`webdriver-manager==4.0.2`, `python-dotenv==1.1.0`, `tinydb==4.8.2`,
`pydantic==2.11.5`, `psutil==5.9.5`, `google-genai>=1.0.0,<2.0.0`,
`waitress>=2.1.0`, `Flask-Babel>=4.0.0`, `openpyxl>=3.1.0`.
Lưu ý: `pytest==8.4.0` trong `requirements.txt` là dev → chuyển sang dev group,
**không** để ở `[project.dependencies]`.

## Related Code Files

- Create: `pyproject.toml`
- Create: `uv.lock` (sinh bằng `uv lock`)
- Delete: `requirements.txt`, `pytest.ini`, `ruff.toml`

## Implementation Steps

1. Viết `pyproject.toml` theo Architecture. Đặt `name = "google-form-automation-tool"`.
2. Chạy `uv lock` để sinh `uv.lock`; kiểm tra không lỗi resolve.
3. Chạy `uv sync` (gồm dev group); xác nhận môi trường tạo được.
4. Xác minh version động: `uv version` (hoặc `uv run python -c "import app; print(app.__version__)"`) in `1.1.0`.
5. Chạy `uv run python -m pytest -q` → phải **215 passed, 1 deselected**.
6. Chạy `uv run ruff check app/ tests/ config.py wsgi.py` → sạch.
7. Xoá `requirements.txt`, `pytest.ini`, `ruff.toml`.
8. Chạy lại bước 5-6 sau khi xoá để chắc cấu hình đã đọc từ pyproject.

## Success Criteria

- [ ] `uv sync` thành công từ clone sạch; `uv.lock` tồn tại và được `git add`
- [ ] `uv version` (hoặc import) in `1.1.0`; `pyproject.toml` không có dòng version hard-code
- [ ] `uv run python -m pytest -q` = 215 passed, 1 deselected
- [ ] `uv run ruff check app/ tests/ config.py wsgi.py` sạch
- [ ] `requirements.txt`, `pytest.ini`, `ruff.toml` đã xoá
- [ ] Tập package trong `uv export` khớp tập runtime của `requirements.txt` cũ

## Risk Assessment

**Version metadata không đọc được.**
Giả định: regex mặc định của `[tool.hatch.version] path=` khớp `__version__ = "1.1.0"`.
Tín hiệu: `uv lock`/`uv sync` báo lỗi "Unable to determine version".
Phản ứng: khai báo tường minh `[tool.hatch.version] source = "regex"` +
`pattern = '^__version__ = "(?P<version>[^"]+)"'`; nếu vẫn vỡ, replan sang đọc version
từ file phụ — nhưng không hard-code (constraint kế hoạch tổng).

**uv.lock resolve khác baseline.**
Giả định: giữ pin cứng thì resolve ra đúng version đang chạy.
Tín hiệu: số test lệch 215, hoặc `uv export` liệt version khác `requirements.txt`.
Phản ứng: đối chiếu từng dòng `uv export` với `requirements.txt` trước khi xoá file gốc;
lệch ở đâu, siết range ở đó.

---
phase: 2
title: "CI / release / build sang uv"
status: done
priority: P1
effort: "3h"
dependencies: [1]
---

# Phase 2: CI / release / build sang uv

## Overview

Chuyển mọi đường cài dependency từ `pip install -r requirements.txt` sang `uv`:
`ci.yml` (test + lint + pip-audit), `release.yml` (build installer), và
`build_exe.bat` (bỏ nhánh fallback `requirements.txt`).

## Requirements

**Functional**

- CI chạy test/lint/security-scan qua uv; pip-audit gate vẫn chạy `--strict`.
- Release build installer qua `uv sync` thay vì `uv pip install -r requirements.txt`.
- `build_exe.bat` dựa vào `pyproject.toml` + `uv sync`; không còn nhánh requirements.

**Non-functional**

- Không đổi kiến trúc chuỗi packaging. Chỉ đổi bước cài deps.

## Architecture

**`.github/workflows/ci.yml`**

- `test` job: dùng `astral-sh/setup-uv@v6` (hoặc `pip install uv`), `uv sync`,
  chạy `uv run python -m pytest --junitxml=pytest-results.xml`. Bỏ/đổi
  `cache-dependency-path: requirements.txt` (dòng 34) → cache theo `uv.lock`.
- `lint` job: `uv sync --only-group dev` (hoặc `uvx ruff`), `uv run ruff check ...`.
- `security-scan` job (DD-3): thay `pip-audit -r requirements.txt --strict` (dòng 123)
  bằng:
  ```bash
  uv export --format requirements-txt --no-emit-project -o requirements.audit.txt
  uv run --with pip-audit pip-audit -r requirements.audit.txt --strict
  ```
  Bỏ `cache-dependency-path: requirements.txt` (dòng 102). Giữ gitleaks + npm audit
  nguyên trạng.

**`.github/workflows/release.yml`**

- Dòng 126-127: `uv pip install --python .venv\Scripts\python.exe -r requirements.txt pyinstaller`
  → `uv sync` (pyinstaller đã ở dev group của Phase 1). Giữ `uv venv --python 3.11`
  nếu `build_exe.bat` cần `.venv\Scripts\python.exe`, hoặc để `uv sync` tự tạo `.venv`.
- **Không đụng** job `pre-check` (gate version dòng 55-95) — giữ nguyên.

**`build_exe.bat`**

- Bước `[2/4]` cài PyInstaller riêng (dòng 49-68): có thể giữ (an toàn) hoặc để
  `uv sync` lo. Tối thiểu: giữ nguyên vì `.spec` cần PyInstaller.
- Bước `[3/4]` (dòng 71-110): rút gọn — khi có `pyproject.toml` luôn chạy `uv sync`;
  bỏ các nhánh fallback `-r requirements.txt` (dòng 86, 88, 100, 102) vì file đã xoá.
  Giữ thông báo lỗi `uv sync failed`.

## Related Code Files

- Modify: `.github/workflows/ci.yml` (test, lint, security-scan jobs)
- Modify: `.github/workflows/release.yml` (build-and-publish job; KHÔNG đụng pre-check)
- Modify: `build_exe.bat` (bước [3/4]; bỏ nhánh requirements.txt)

## Implementation Steps

1. Sửa `ci.yml` test job sang uv (setup-uv + `uv sync` + `uv run pytest`).
2. Sửa `ci.yml` lint job sang uv.
3. Sửa `ci.yml` security-scan: pip-audit qua `uv export` (DD-3); bỏ cache pip theo requirements.
4. Sửa `release.yml` bước Sync deps → `uv sync`; giữ pre-check nguyên.
5. Sửa `build_exe.bat` bước [3/4]: chỉ còn nhánh `uv sync`, bỏ fallback requirements.txt.
6. `grep -rn "requirements.txt" .github/ build_exe.bat` → phải 0.
7. Kiểm tra cú pháp YAML (`uv run python -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"`).

## Success Criteria

- [ ] `grep -rn "requirements.txt"` trong `.github/` và `build_exe.bat` = 0
- [ ] YAML của cả hai workflow parse hợp lệ
- [ ] Job `pre-check` (gate version) trong `release.yml` không đổi
- [ ] Bước pip-audit vẫn tồn tại, dùng `uv export`, giữ `--strict`
- [ ] `build_exe.bat` chỉ còn đường `uv sync` cho cài deps
- [ ] (Nếu chạy được local) `build_exe.bat debug` tới bước sync không lỗi

## Risk Assessment

**CI cache vỡ sau khi bỏ requirements.txt.**
Giả định: `setup-python cache: pip` cần `cache-dependency-path`.
Tín hiệu: job fail ngay bước setup, log "No file matched to requirements.txt".
Phản ứng: chuyển sang `astral-sh/setup-uv` với `enable-cache: true` (cache theo `uv.lock`),
hoặc bỏ hẳn cache pip.

**pip-audit đổi nguồn làm sai gate.**
Giả định: `uv export` liệt đúng tập runtime như `requirements.txt`.
Tín hiệu: CVE-count khác trước mà không có bump version nào.
Phản ứng: dùng `--no-emit-project` để loại chính app khỏi export; đối chiếu tập package
export với `requirements.txt` cũ (đã lưu trong git history) trước khi tin gate.

**release.yml đổi cách tạo venv làm `build_exe.bat` mất `.venv\Scripts\python.exe`.**
Giả định: `uv sync` tạo `.venv` ở root repo mà `build_exe.bat` trông đợi.
Tín hiệu: bước Build backend fail "`.venv not found`".
Phản ứng: giữ `uv venv --python 3.11` trước `uv sync`, hoặc set `UV_PROJECT_ENVIRONMENT=.venv`.

---
phase: 4
title: "Nghiệm thu"
status: done
priority: P1
dependencies: [3]
effort: "2h"
---

# Phase 4: Nghiệm thu

## Overview

Kiểm chứng toàn bộ success criteria của `plan.md` bằng lệnh thật, gồm mô phỏng
clone sạch `uv sync`, full pytest, ruff, pip-audit, và sweep grep. Không sửa code
ở phase này trừ khi có FAIL phải quay lại phase tương ứng.

## Requirements

**Functional**

- Mọi tiêu chí trong `plan.md` → Success Criteria được chứng minh bằng output lệnh.
- Acceptance Phase 2 của kế hoạch tổng đạt: `uv sync` từ clone sạch; `uv.lock` commit;
  pip-audit gate còn chạy; CI xanh; Docker gỡ, không còn tham chiếu.

**Non-functional**

- Không nới tiêu chí. FAIL → quay lại phase, không sửa tại chỗ ở đây.

## Architecture

Nghiệm thu chỉ đọc + chạy lệnh. Điểm rủi ro nhất là "clone sạch": môi trường dev
hiện có `.venv` cũ sinh từ pip, có thể che lỗi resolve của `uv.lock`. Vì vậy phải
mô phỏng clone sạch (env tách biệt) chứ không tin `.venv` sẵn có.

## Related Code Files

- Read-only toàn bộ. Deliverable là kết quả nghiệm thu ghi lại trong report.

## Implementation Steps

1. Chạy trọn bộ Verification, ghi output thật.
2. Đối chiếu từng dòng `plan.md` → Success Criteria: PASS/FAIL kèm bằng chứng.
3. FAIL → quay lại phase liên quan (1/2/3).
4. `git diff --stat` xác nhận scope: `app/` chỉ 1 dòng `main_routes.py`.
5. Mở PR nhánh `refactor/phase-2-root-cleanup-deps`.

## Verification

```powershell
# 0. uv có sẵn (cài nếu thiếu)
uv --version   # nếu thiếu: python -m pip install uv

# 1. Clone-sạch: sync vào env tách biệt (không dùng .venv dev cũ)
$env:UV_PROJECT_ENVIRONMENT = ".venv-verify"
uv sync
uv run python -c "import app; print(app.__version__)"   # -> 1.1.0

# 2. Full suite (đúng baseline Phase 1)
uv run python -m pytest -q                               # -> 215 passed, 1 deselected

# 3. Lint — cùng phạm vi CI
uv run ruff check app/ tests/ config.py wsgi.py

# 4. pip-audit qua uv export (như CI)
uv export --format requirements-txt --no-emit-project -o requirements.audit.txt
uv run --with pip-audit pip-audit -r requirements.audit.txt --strict
Remove-Item requirements.audit.txt

# 5. File đã xoá
Test-Path Dockerfile, docker-compose.yml, .dockerignore, requirements.txt, pytest.ini, ruff.toml, tests\test_resource.md
#   -> tất cả False

# 6. Không còn tham chiếu
Select-String -Path .github\workflows\*.yml, build_exe.bat, README.md -Pattern 'requirements\.txt'
Select-String -Path README.md, .github\workflows\*.yml, scripts\*.ps1, build_exe.bat -Pattern 'docker' -CaseSensitive:$false
#   -> cả hai rỗng

# 7. Gate version release.yml không đổi + đồng bộ
node -p "require('./package.json').version"              # -> 1.1.0
Select-String -Path app\__init__.py -Pattern '__version__'   # -> 1.1.0

# 8. Scope diff runtime
git diff --stat app/         # chỉ app/main_routes.py, 1 dòng

# 9. uv.lock trong index
git status --short uv.lock    # phải được add
```

## Success Criteria

- [ ] `uv sync` clone-sạch thành công; import `app.__version__` = 1.1.0
- [ ] `pytest -q` = 215 passed, 1 deselected
- [ ] `ruff check` sạch
- [ ] pip-audit `--strict` chạy qua `uv export`, không CVE mới
- [ ] Tất cả file mục 5 đã xoá (Test-Path = False)
- [ ] Sweep `requirements.txt` và `docker` = rỗng
- [ ] `package.json` == `app/__init__.py` == 1.1.0; gate `pre-check` release.yml không đổi
- [ ] `git diff --stat app/` chỉ 1 dòng `main_routes.py`
- [ ] `uv.lock` được commit

## Risk Assessment

**`.venv` dev cũ che lỗi resolve.**
Giả định: `uv sync` vào env tách biệt phản ánh đúng clone sạch.
Tín hiệu: local xanh nhưng CI (từ clone thật) đỏ ở bước sync.
Phản ứng: luôn nghiệm thu qua `UV_PROJECT_ENVIRONMENT=.venv-verify` (env mới), không tin `.venv` sẵn.

**Số test lệch baseline vì skip âm thầm.**
Giả định: 215 passed là mốc đúng (từ Phase 1 / `docs/PROJECT_REFACTOR_AUDIT.md:59`).
Tín hiệu: tổng số test khác 215.
Phản ứng: `uv run pytest -q -rs` xem lý do skip (vd thiếu `node` cho
`test_js_prefill_validator.py`) trước khi kết luận PASS/FAIL.

**Packaging smoke chưa chạy ở phase này.**
Giả định: Phase 2 không di chuyển module nên `.spec` không đổi; packaging vẫn PASS.
Tín hiệu: acceptance kế hoạch tổng Phase 2 không đòi packaging smoke (khác Phase 3/4).
Phản ứng: packaging smoke là **tuỳ chọn** ở đây; nếu chạy được Windows, chạy
`build_exe.bat debug` tới bước sync để xác nhận đường uv, không bắt buộc full installer.

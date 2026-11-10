---
phase: 3
title: "Gỡ Docker, file rác, gộp docs"
status: done
priority: P2
dependencies: [2]
effort: "2h"
---

# Phase 3: Gỡ Docker, file rác, gộp docs

## Overview

Xoá Docker (3 file) + tham chiếu README, xoá `tests/test_resource.md`, sửa chuỗi
lỗi nhắc `requirements.txt` trong `app/main_routes.py`, cập nhật README onboarding
sang uv-first, và gộp `CLAUDE.md` (trùng nội dung) thành loader mỏng trỏ `AGENTS.md`.

## Requirements

**Functional**

- Không còn file/tham chiếu Docker trong repo (trừ plans/reports là tài liệu lịch sử).
- README hướng dẫn onboarding bằng uv, không còn mục Docker.
- `CLAUDE.md` không lặp lại mục 1-4 của `AGENTS.md`.

**Non-functional**

- Chỉ sửa duy nhất 1 dòng trong `app/` (chuỗi lỗi), không đổi logic.

## Architecture

**Xoá**

- `Dockerfile`, `docker-compose.yml`, `.dockerignore`.
- `tests/test_resource.md` (chỉ là link form test; chỉ được nhắc trong brainstorm — orphan).
- `.agents/`, `.codex/` — **đã không tồn tại** (xác minh `ls -d`); bước này là no-op ghi nhận.

**`README.md`**

- Bỏ mục "### Docker nâng cao" (dòng ~135-139) và dòng Known Issues về Docker (dòng 68).
- Trong "Setup Flask backend": bỏ nhánh `pip install -r requirements.txt` (dòng 90-91),
  để `uv sync` là đường chính; giữ `python wsgi.py` (hoặc đổi `uv run python wsgi.py`).

**`app/main_routes.py:589`**

- Chuỗi lỗi hiện: `"AI dependency is not installed. Run pip install -r requirements.txt."`
  → đổi thành `"... Run uv sync (or uv pip install google-genai)."`. Chỉ đổi text,
  không đổi luồng.

**`CLAUDE.md` (DD-4)**

- Giữ tiêu đề + dòng mô tả + khối `<!-- HARNESS:BEGIN -->...END -->` (đã `@AGENTS.md`).
- Bỏ mục 1-4 trùng (dòng 7-65). Kết quả: `CLAUDE.md` là loader mỏng; `AGENTS.md` là bản chính.

## Related Code Files

- Delete: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `tests/test_resource.md`
- Modify: `README.md` (bỏ Docker + requirements.txt onboarding)
- Modify: `app/main_routes.py` (chỉ dòng 589, chuỗi lỗi)
- Modify: `CLAUDE.md` (bỏ mục 1-4 trùng)
- Read-only: `AGENTS.md` (bản chính, giữ nguyên)

## Implementation Steps

1. Xoá 3 file Docker + `tests/test_resource.md`.
2. `ls -d .agents .codex` → xác nhận đã absent (no-op).
3. Sửa `README.md`: bỏ mục Docker, dòng Known Issues Docker, nhánh requirements.txt onboarding.
4. Sửa chuỗi lỗi `app/main_routes.py:589`.
5. Rút gọn `CLAUDE.md` còn loader mỏng (bỏ mục 1-4).
6. Sweep: `grep -ri "docker" README.md .github/ scripts/ build_exe.bat *.spec` = 0.
7. Sweep: `grep -rn "requirements.txt" README.md app/` = 0.
8. Chạy lại `uv run python -m pytest -q` để chắc sửa chuỗi lỗi không làm vỡ test nào chạm nó.

## Success Criteria

- [ ] `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `tests/test_resource.md` đã xoá
- [ ] `grep -ri docker` trong README/CI/scripts/build/spec = 0
- [ ] `grep -rn requirements.txt` trong README/app = 0
- [ ] `CLAUDE.md` không còn mục 1-4; vẫn có khối Harness `@AGENTS.md`
- [ ] README onboarding dùng uv; không còn mục Docker
- [ ] `uv run python -m pytest -q` = 215 passed, 1 deselected (không đổi)
- [ ] `git diff app/` chỉ hiện 1 dòng chuỗi lỗi ở `main_routes.py`

## Risk Assessment

**Có test đọc chuỗi lỗi `main_routes.py:589`.**
Giả định: không test nào assert nguyên văn "pip install -r requirements.txt".
Tín hiệu: pytest fail ở test AI-responder sau khi đổi text.
Phản ứng: `grep -rn "requirements.txt" tests/`; nếu có, cập nhật assertion theo text mới.

**README còn link/tham chiếu Docker ngoài mục đã biết.**
Giả định: Docker chỉ xuất hiện ở 2 chỗ đã liệt kê.
Tín hiệu: sweep `grep -ri docker README.md` vẫn ra dòng.
Phản ứng: xoá tất cả tham chiếu còn lại; không để README claim tính năng đã gỡ.

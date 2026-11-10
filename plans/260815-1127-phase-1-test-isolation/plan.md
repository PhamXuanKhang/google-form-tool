---
title: "Phase 1 Test Isolation"
description: "Cách ly test khỏi dữ liệu người dùng thật và gỡ coupling storage theo tên module, mở đường cho việc tách route ở Phase 3."
status: done
priority: P1
effort: "1d"
tags: [refactor, testing, phase-1]
created: 2026-08-15
---

# Phase 1 Test Isolation

Phase 1 của kế hoạch tái cấu trúc 4 phase. Contract gốc:
`plans/reports/brainstorm-260815-1115-repo-restructure.md`.

## Overview

Chạy `pytest` hiện tại ghi vào dữ liệu thật của người dùng và cần quyền elevation.
Nguyên nhân: `Config` đọc env lúc import và tính đường dẫn cố định về
`%APPDATA%\GoogleFormTool`; `app/logging_config.py:66` mở file log ngay khi import;
`app/services/__init__.py:7` đọc thẳng `Config.DB_PATH`.

Test bù lại bằng cách vá `app.main_routes.get_storage_service` ở 36 chỗ trong 11 file.
Cách vá này bám vào **tên module** `app.main_routes`, nên Phase 3 của kế hoạch tổng
(tách `main_routes.py` thành `app/routes/*`) sẽ làm vỡ toàn bộ. Phase 1 phải xong trước.

> Lưu ý cách đọc: "Phase 1-4" không kèm chú thích là **các bước bên trong plan này**.
> Các bước của kế hoạch tái cấu trúc 4 phase luôn được gọi rõ là "kế hoạch tổng".

Phase này **không đổi hành vi runtime**. Mọi thay đổi nằm ở đường dẫn cấu hình lúc
test và một seam nhỏ trong `app/services/__init__.py`.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | `pytest` không đọc/ghi `%APPDATA%\GoogleFormTool` nữa | P1 |
| 2 | `pytest` chạy được trong sandbox không cần elevation | P1 |
| 3 | Test tiêm storage giả qua seam độc lập tên module, không patch `main_routes` | P1 |
| 4 | Lập bản đồ các coupling `main_routes` còn lại để kế hoạch tổng Phase 3 không bất ngờ | P2 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Env Path Isolation](./phase-01-env-path-isolation.md) | Done |
| 2 | [Phase 2: Storage Provider Seam](./phase-02-storage-provider-seam.md) | Done |
| 3 | [Phase 3: Migrate Test Stubs](./phase-03-migrate-test-stubs.md) | Done |
| 4 | [Phase 4: Verification And Coupling Map](./phase-04-verification-and-coupling-map.md) | Done |

Thứ tự bắt buộc: 1 → 2 → 3 → 4. Phase 3 phụ thuộc seam của Phase 2.

## Design Decisions

### DD-1: Env-before-import thay vì `TestConfig`

`TestConfig` **không giải được** bài toán, bằng chứng:

- `app/logging_config.py:66` gọi `configure_logging()` lúc import module. `create_app()`
  chạy sau đó nên mọi override qua `app.config` đều quá muộn.
- `configure_logging()` bỏ qua handler đã tồn tại theo tên (`app/logging_config.py:52`),
  nên gọi lại với thư mục temp **không** thay handler cũ.
- `app/services/__init__.py:7` đọc `Config.DB_PATH` (class attribute), không đọc
  `app.config`; và `app/main_routes.py:991` gọi nó trong **background thread**
  (`_run_submission`, spawn tại `app/main_routes.py:942`) nơi không có app context —
  seam kiểu `current_app.config` sẽ vỡ đúng ở đường ghi lịch sử submission.

Cách chạy được: đặt `LOG_DIR`, `DB_PATH`, `SECRET_KEY` vào `os.environ` ở đầu
`tests/conftest.py`, **trước** mọi import `app`/`config`.

Hệ quả cho Phase 4 của kế hoạch tổng: chỉ di chuyển `config.py` → `app/config.py`,
không thêm `TestConfig`.

### DD-2: Provider seam ở tầng module, không phải app extension

`get_storage_service()` tra một provider ở module-global. Ba tính chất cần thiết:

- chạy được trong thread không có app context (`_run_submission`);
- `main_routes` giữ tham chiếu `from app.services import get_storage_service` — vẫn là
  cùng một function object, nên override có hiệu lực mà không cần patch;
- không phụ thuộc tên module, nên Phase 3 tách route không làm vỡ test.

Phase 3 có thể nâng seam này thành provider gắn với app khi tách
`submission_manager`; đây là bước rẻ nhất để bỏ đi sau.

### DD-3: Không đụng `configure_logging()` lúc import

Xoá lời gọi ở `app/logging_config.py:66` sạch hơn về mặt thiết kế nhưng đổi hành vi
logging runtime: module nào dùng `logger` trước `create_app()` sẽ mất file log.
Phase 1 cam kết không đổi hành vi runtime, nên giữ nguyên và cách ly bằng env.

## Scope

**Trong phạm vi**

- `tests/conftest.py`: bootstrap env + fixture `storage_stub`.
- `app/services/__init__.py`: seam `set_storage_provider` / `get_storage_service`.
- 11 file test, 36 chỗ patch `get_storage_service`.
- Bản đồ coupling `main_routes` còn lại, giao cho Phase 3.

**Ngoài phạm vi**

- Không đổi hành vi runtime, không đổi route, không đổi contract.
- Không tách `_upload_cache` / `active_submitters` (Phase 3 sở hữu).
- Không sửa 23 coupling `main_routes` còn lại — chỉ lập bản đồ.
- Không đụng `pyproject.toml`, Docker, packaging (Phase 2 của kế hoạch tổng).
- Không di chuyển `config.py` (Phase 4 của kế hoạch tổng).

## Success Criteria

- [x] Full suite PASS: 215 passed, 1 deselected — bằng con số trước khi đổi
- [x] `pytest` chạy trong sandbox hạn chế, không cần elevation
- [x] `%APPDATA%\GoogleFormTool\db.json` không đổi mtime sau khi chạy full suite
- [x] `%APPDATA%\GoogleFormTool\logs\app.log` không đổi mtime sau khi chạy full suite
- [x] `grep -rn 'main_routes, "get_storage_service"' tests/` trả về 0 kết quả
- [x] `ruff check app/ tests/ config.py wsgi.py` sạch — cùng phạm vi với CI
      (`.github/workflows/ci.yml:81`). `ruff` chưa cài sẵn trong `.venv`; cài trước khi nghiệm thu
- [x] Bản đồ coupling tồn tại trong `phase-04` và liệt kê đủ 23 điểm còn lại
- [x] `git diff --stat app/` chỉ chạm `app/services/__init__.py`

## Risks

| Rủi ro | Tín hiệu phát hiện | Phản ứng đã định |
|---|---|---|
| `tests/conftest.py` không được nạp trước module app nào | Log test vẫn xuất hiện ở `%APPDATA%` | Chuyển bootstrap sang `conftest.py` ở root repo |
| `.env` ở root ghi đè env của conftest | `Config.DB_PATH` trỏ về đường dẫn thật khi debug | `load_dotenv()` mặc định không override; nếu sai, đổi sang `load_dotenv(override=False)` tường minh |
| `importlib.reload(config)` trong `test_runtime_config.py` làm rò cấu hình | Test khác fail tuỳ thứ tự chạy | Không đọc `config.Config` trễ trong seam; giữ `from config import Config` bind sớm |
| Test còn dùng storage thật ngoài dự kiến | File `db.json` xuất hiện trong temp dir sau khi chạy | Chấp nhận — temp dir là đích đúng; chỉ chặn nếu trỏ về `%APPDATA%` |

## References

- Contract: `plans/reports/brainstorm-260815-1115-repo-restructure.md`
- Bằng chứng lỗi quyền ghi: `docs/PROJECT_REFACTOR_AUDIT.md:60`
- Ranh giới kiến trúc: `docs/ARCHITECTURE.md:21-26`

<!-- slug: phase-1-test-isolation -->

---
phase: 1
title: "Env Path Isolation"
status: done
priority: P1
effort: "2h"
dependencies: []
---

# Phase 1: Env Path Isolation

## Overview

Chuyển mọi đường dẫn ghi của test (`LOG_DIR`, `DB_PATH`, `SECRET_KEY`, `DRIVERS_DIR`)
về một thư mục tạm, bằng cách set `os.environ` ở đầu `tests/conftest.py` trước mọi
import `app`/`config`.

## Requirements

**Functional**

- Sau khi chạy full suite, không file nào dưới `%APPDATA%\GoogleFormTool` bị tạo hoặc sửa.
- Suite chạy được trong sandbox không có quyền ghi `%APPDATA%`.
- 215 test vẫn PASS, không đổi assertion nào.

**Non-functional**

- Không đổi code runtime. Diff phase này chỉ chạm `tests/conftest.py`.
- Thư mục tạm bị dọn khi phiên pytest kết thúc.

## Architecture

Ba thứ ghi ra ngoài workspace lúc **import**, không phải lúc `create_app()`:

| Nguồn ghi | Vị trí | Kích hoạt lúc |
|---|---|---|
| Thư mục app-data + file `secret_key` | `config.py:26,32` qua `_load_or_create_secret_key()` | import `config` |
| Thư mục logs + `app.log` | `app/logging_config.py:66` gọi `configure_logging()` | import `app.logging_config` |
| `db.json` | `app/services/__init__.py:8` | lần đầu gọi `get_storage_service()` |

`Config` gán giá trị ở thân class (`config.py:38-65`), tức đọc `os.getenv` đúng một
lần lúc import. Vậy env phải có mặt **trước** import đầu tiên.

`config.py:8` gọi `load_dotenv()`. Mặc định của python-dotenv là **không** ghi đè
biến môi trường đã tồn tại, nên `os.environ` do conftest đặt sẽ thắng `.env` ở root.
Đây là tính chất load-bearing của thiết kế này.

`SECRET_KEY` phải được set: nếu thiếu, `config.py:46` gọi `_load_or_create_secret_key()`
và hàm này `mkdir` + ghi file vào thư mục app-data thật (`config.py:26-32`).

Thứ tự nạp của pytest: `tests/conftest.py` được import trước mọi module test, nên nó là
điểm bootstrap hợp lệ duy nhất mà không cần plugin ngoài.

## Related Code Files

- Modify: `tests/conftest.py`
- Read-only reference: `config.py`, `app/logging_config.py`, `app/services/__init__.py`

## Implementation Steps

1. Chèn khối bootstrap vào **đầu** `tests/conftest.py`, phía trên mọi import `app`:

   ```python
   """Create fixtures for unit testing."""
   # Test paths must be redirected before app/config import: Config reads env at
   # class-definition time and logging opens its file handler at import time.
   import atexit
   import os
   import shutil
   import tempfile

   _TEST_DATA_DIR = tempfile.mkdtemp(prefix="gft-tests-")
   os.environ["LOG_DIR"] = os.path.join(_TEST_DATA_DIR, "logs")
   os.environ["DB_PATH"] = os.path.join(_TEST_DATA_DIR, "db.json")
   os.environ["DRIVERS_DIR"] = os.path.join(_TEST_DATA_DIR, "drivers")
   os.environ.setdefault("SECRET_KEY", "test-secret-key")
   atexit.register(shutil.rmtree, _TEST_DATA_DIR, True)
   ```

2. Giữ nguyên toàn bộ import và fixture hiện có bên dưới khối này.
3. Chạy `pytest -q` và so sánh số test với baseline.
4. Kiểm tra thư mục tạm: `db.json` và `logs/app.log` phải xuất hiện ở đó.

## Verification

```powershell
# Baseline trước khi sửa
.\.venv\Scripts\python.exe -m pytest -q

# Chụp mtime dữ liệu thật
$db  = "$env:APPDATA\GoogleFormTool\db.json"
$log = "$env:APPDATA\GoogleFormTool\logs\app.log"
$before = @{ db = (Get-Item $db -EA SilentlyContinue).LastWriteTimeUtc
             log = (Get-Item $log -EA SilentlyContinue).LastWriteTimeUtc }

.\.venv\Scripts\python.exe -m pytest -q

$after = @{ db = (Get-Item $db -EA SilentlyContinue).LastWriteTimeUtc
            log = (Get-Item $log -EA SilentlyContinue).LastWriteTimeUtc }
if ($before.db -ne $after.db)   { throw "db.json bị ghi trong lúc test" }
if ($before.log -ne $after.log) { throw "app.log bị ghi trong lúc test" }
```

## Success Criteria

- [x] 215 passed, 1 deselected — bằng baseline
- [x] `db.json` và `app.log` thật không đổi mtime sau full suite
- [x] `pytest` chạy được không cần elevation
- [x] `git diff --name-only` chỉ liệt kê `tests/conftest.py`
- [ ] `ruff check .` sạch — không xác minh được: `ruff` chưa cài trong `.venv` của môi trường này

## Risk Assessment

**`test_runtime_config.py` reload `config` với env rỗng.**
`tests/test_runtime_config.py:7-9,25-26` chủ động set `DB_PATH`/`LOG_DIR`/`DRIVERS_DIR`
thành `""` rồi `importlib.reload(config)` để khẳng định đường dẫn fallback về APPDATA.
Bootstrap của phase này không ảnh hưởng vì monkeypatch chạy sau và test chỉ khẳng định
trên đối tượng vừa reload. `reload` tạo class `Config` **mới**; các module đã import
vẫn giữ tham chiếu class cũ nên không rò sang test khác.
Tín hiệu hỏng: test khác fail khi đổi thứ tự chạy (`pytest -p no:randomly` vs mặc định).
Phản ứng: bọc reload bằng fixture tự phục hồi `importlib.reload(config)` ở teardown.

**Logging handler dùng lại giữa các test.**
`configure_logging()` bỏ qua handler trùng tên (`app/logging_config.py:52`), nhưng
fixture autouse `setup_logging` (`tests/conftest.py:15-22`) đã thay
`logger.handlers = [caplog.handler]` mỗi test nên handler luôn được tạo lại theo
`LOG_DIR` hiện hành. Không cần đổi gì.
Tín hiệu hỏng: `test_logging_configuration_adds_file_handler_without_duplicates` fail.
Phản ứng: kiểm tra thứ tự fixture, không nới lỏng assertion.

**Thư mục tạm không được dọn khi pytest bị kill.**
Chấp nhận. `atexit` không chạy khi bị SIGKILL; rác nằm trong temp của OS.
Phản ứng: không xử lý — chi phí lớn hơn lợi ích.

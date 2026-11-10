---
phase: 2
title: "Storage Provider Seam"
status: done
priority: P1
effort: "1h"
dependencies: [1]
---

# Phase 2: Storage Provider Seam

## Overview

Thêm một provider có thể override vào `app/services/__init__.py` để test tiêm storage
giả mà không cần vá thuộc tính module của `app.main_routes`. Đây là thay đổi runtime
duy nhất của cả Phase 1.

## Requirements

**Functional**

- `get_storage_service()` giữ nguyên chữ ký và hành vi mặc định.
- Khi có provider được cài, `get_storage_service()` trả về thứ provider tạo ra.
- Hoạt động trong thread không có app context.
- 15 call site `with get_storage_service() as storage:` trong `app/main_routes.py`
  (`:162, :188, :239, :305, :331, :372, :429, :477, :536, :650, :730, :906, :991, :1076, :1117`)
  không phải sửa dòng nào.

**Non-functional**

- Không thêm dependency mới.
- Đường mặc định không tốn thêm I/O nào so với hiện tại.

## Architecture

`app/main_routes.py:16` bind `from app.services import get_storage_service` lúc import.
Vì đó là **cùng một function object**, việc tra provider bên trong thân hàm có hiệu lực
với mọi call site đã bind — kể cả sau khi kế hoạch tổng Phase 3 tách route sang module khác.

Vì sao không dùng `current_app.config` hay `app.extensions`:
`app/main_routes.py:991` gọi `get_storage_service()` bên trong `_run_submission`
(định nghĩa tại `app/main_routes.py:975`), chạy ở daemon thread spawn tại
`app/main_routes.py:944`. Thread không kế thừa app context, nên seam dựa vào app sẽ ném
`RuntimeError: Working outside of application context` đúng ở đường ghi lịch sử submission.

```
test                       app/services              call sites
  |                             |                        |
  set_storage_provider(f) ----> _storage_provider = f     |
                                |                         |
                                |<---- get_storage_service()  (main_routes, thread, Phase 3 routes)
                                |
                          f() hoặc StorageService(Config.DB_PATH)
```

`Config` được bind sớm (`from config import Config`), không tra lại lúc gọi. Điều này
cố ý: `tests/test_runtime_config.py` dùng `importlib.reload(config)`, tra trễ sẽ khiến
cấu hình bị reload rò sang test khác.

## Related Code Files

- Modify: `app/services/__init__.py`
- Read-only reference: `app/main_routes.py:16,991`, `app/services/storage_service.py`

## Implementation Steps

1. Viết lại `app/services/__init__.py`:

   ```python
   from pathlib import Path
   from config import Config
   from app.services.storage_service import StorageService

   # Overridable factory. Tests install a stub so route code can be exercised
   # without touching the on-disk TinyDB. Threads use this too, so it must not
   # depend on a Flask application context.
   _storage_provider = None


   def set_storage_provider(provider):
       """Install a storage factory. Pass None to restore the default."""
       global _storage_provider
       _storage_provider = provider


   def get_storage_service():
       if _storage_provider is not None:
           return _storage_provider()
       db_path = Config.DB_PATH
       Path(db_path).parent.mkdir(parents=True, exist_ok=True)
       return StorageService(db_path)
   ```

2. Kiểm tra `app/services/__init__.py` vẫn export `StorageService` cho
   `tests/conftest.py:33` (`from app.services import StorageService`).
3. Chạy full suite — phải PASS mà chưa cần sửa file test nào, vì provider mặc định
   giữ nguyên hành vi cũ.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Kiểm tra thủ công seam hoạt động trong thread. **Không dùng here-string `@'...'@` làm
đối số cho `python -c`**: PowerShell 5.1 bóc dấu nháy khi truyền cho native exe, Python
nhận `print(herestring arg ok)` và ném `SyntaxError` — đã kiểm chứng. Ghi ra file tạm
rồi chạy:

```powershell
$probe = Join-Path $env:TEMP "seam-probe.py"
@'
import threading
from app.services import get_storage_service, set_storage_provider

set_storage_provider(lambda: "stub")
out = []
t = threading.Thread(target=lambda: out.append(get_storage_service()))
t.start()
t.join()
assert out == ["stub"], out
set_storage_provider(None)
print("thread seam ok")
'@ | Set-Content -Path $probe -Encoding utf8

.\.venv\Scripts\python.exe $probe    # phải in: thread seam ok
Remove-Item $probe
```

Lint: `ruff` **chưa cài** trong `.venv` của môi trường này (`python -m ruff` →
`No module named ruff`). CI cài riêng và chạy phạm vi hẹp hơn `.`
(`.github/workflows/ci.yml:75,81`). Muốn nghiệm thu lint tại chỗ thì cài trước:

```powershell
.\.venv\Scripts\python.exe -m pip install ruff
.\.venv\Scripts\python.exe -m ruff check app/ tests/ config.py wsgi.py
```

## Success Criteria

- [x] 215 passed, 1 deselected — chưa sửa file test nào
      (baseline này đã chạy lại sau Phase 1 vào 2026-08-15 và vẫn đúng)
- [x] Seam hoạt động trong thread (lệnh kiểm tra ở trên in `thread seam ok`)
- [x] `git diff --name-only app/` chỉ liệt kê `app/services/__init__.py`
- [ ] `ruff check app/ tests/ config.py wsgi.py` sạch — cùng phạm vi với CI.
      Hoãn sang CI: `.venv` không có `pip` (`No module named pip`), không cài được `ruff`
      tại chỗ trong môi trường này.
- [x] Đã liệt kê 15 call site (mục Requirements) và xác nhận không call site nào phải sửa
      (`grep -c "with get_storage_service() as storage:" app/main_routes.py` → 15)

## Risk Assessment

**Provider rò giữa các test.**
Nếu một test cài provider mà không reset, các test sau dùng nhầm stub.
Tín hiệu: test PASS khi chạy riêng nhưng FAIL khi chạy cả suite.
Phản ứng: fixture autouse ở Phase 3 reset provider sau **mọi** test, không chỉ test có
dùng `storage_stub`.

**Provider rò giữa các thread.**
`_storage_provider` là biến module dùng chung, không thread-local. Trong test đây là
điều mong muốn (thread phải thấy stub). Trong runtime provider luôn là `None`.
Tín hiệu: hành vi lạ nếu ai đó cài provider ở code sản phẩm.
Phản ứng: seam này chỉ dành cho test — ghi rõ trong docstring, không thêm cơ chế chặn.

**`global` statement.**
Ruff cấu hình `select = ["E9", "F"]` (`ruff.toml`), không bật rule cấm `global`.
Không có rủi ro lint.

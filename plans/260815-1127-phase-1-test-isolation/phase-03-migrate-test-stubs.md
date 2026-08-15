---
phase: 3
title: "Migrate Test Stubs"
status: done
priority: P1
effort: "3h"
dependencies: [2]
---

# Phase 3: Migrate Test Stubs

## Overview

Thay 36 lời gọi `monkeypatch.setattr(main_routes, "get_storage_service", ...)` ở 11 file
test bằng fixture `storage_stub` dùng seam của Phase 2. Sau phase này không test nào
còn phụ thuộc `app.main_routes` để tiêm storage.

## Requirements

**Functional**

- `grep -rn 'main_routes, "get_storage_service"' tests/` trả về 0 kết quả.
- Mọi assertion giữ nguyên. Không nới lỏng, không xoá test nào.
- Provider được reset sau mỗi test, kể cả khi test fail.

**Non-functional**

- Không đổi cấu trúc thư mục `tests/` (việc đó thuộc kế hoạch tổng, không thuộc Phase 1).
- Các class `FakeStorage`/`FakeStorageContext` cục bộ giữ nguyên tại chỗ — gom chung là
  scope khác.

## Architecture

Fixture nằm ở `tests/conftest.py`, một chỗ teardown duy nhất:

```python
from app.services import set_storage_provider


@pytest.fixture(autouse=True)
def _reset_storage_provider():
    """Ngăn stub của một test rò sang test sau."""
    yield
    set_storage_provider(None)


@pytest.fixture
def storage_stub():
    """Cài storage giả cho route code trong phạm vi một test."""
    def install(storage):
        set_storage_provider(lambda: storage)
        return storage
    return install
```

Quy tắc chuyển đổi:

```python
# trước
monkeypatch.setattr(main_routes, "get_storage_service", lambda: FakeStorage(form))

# sau
storage_stub(FakeStorage(form))
```

Trường hợp test cần giữ tham chiếu để assert:

```python
# trước
storage = FakeStorageContext()
monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

# sau
storage = storage_stub(FakeStorageContext())
```

Sau khi chuyển, gỡ `monkeypatch` khỏi chữ ký test **chỉ khi** test không còn dùng nó
cho việc khác; nhiều test vẫn patch `FormSubmitter`, `FormExtractor`, `time.sleep`.
Tương tự, gỡ `import app.main_routes as main_routes` chỉ khi file không còn tham chiếu
`main_routes` nào — 5 file vẫn cần vì chạm `active_submitters` / `_run_submission`.

## Related Code Files

- Modify: `tests/conftest.py`
- Modify (số chỗ cần chuyển):

  | File | Số chỗ | Còn dùng `main_routes` sau khi chuyển? |
  |---|---|---|
  | `tests/test_prefill_submission.py` | 7 | có — `_run_submission`, `active_submitters` |
  | `tests/test_form_copy_routes.py` | 6 | không |
  | `tests/test_submission_persistence.py` | 5 | có — `_run_submission`, `active_submitters` |
  | `tests/test_submission_history_route.py` | 4 | không |
  | `tests/test_delete_form_route.py` | 3 | không |
  | `tests/test_save_edit_route.py` | 3 | không |
  | `tests/test_extract_route.py` | 2 | không |
  | `tests/test_form_processor.py` | 2 | không |
  | `tests/test_i18n_render.py` | 2 | không |
  | `tests/test_ai_text_route.py` | 1 | không |
  | `tests/test_submission_status_retention.py` | 1 | có — `active_submitters`, `_cleanup_finished_submitters` |
  | **Tổng** | **36** | |

## Implementation Steps

1. Thêm hai fixture vào `tests/conftest.py`.
2. Chuyển từng file theo thứ tự tăng dần độ khó, chạy `pytest <file>` sau mỗi file:
   1. `test_ai_text_route.py`, `test_i18n_render.py`, `test_extract_route.py` (1-2 chỗ mỗi file)
   2. `test_form_processor.py`, `test_delete_form_route.py`, `test_save_edit_route.py`
   3. `test_submission_history_route.py`, `test_form_copy_routes.py`
   4. `test_submission_status_retention.py`, `test_submission_persistence.py`, `test_prefill_submission.py`
3. Trong mỗi file: gỡ tham số `monkeypatch` và `import app.main_routes as main_routes`
   khi và chỉ khi không còn dùng.
4. Chạy full suite sau mỗi nhóm.
5. Chạy `ruff check tests/` để bắt import thừa (rule `F401` đang bật).

## Verification

```powershell
# từng nhóm
.\.venv\Scripts\python.exe -m pytest tests/test_form_copy_routes.py -q

# toàn bộ
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check tests/

# tiêu chí chính
Select-String -Path tests\*.py -Pattern 'main_routes, "get_storage_service"'   # phải rỗng
```

Kiểm tra rò provider giữa các test bằng cách đảo thứ tự:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_submission_persistence.py tests/test_extract_route.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_extract_route.py tests/test_submission_persistence.py
```

## Success Criteria

- [x] 0 kết quả cho `main_routes, "get_storage_service"` trong `tests/`
- [x] 215 passed, 1 deselected
- [x] `ruff check tests/` sạch — không còn import `main_routes` thừa
- [x] Hai lệnh đảo thứ tự file đều PASS
- [x] Không file test nào bị xoá, không assertion nào bị nới lỏng
- [x] `git diff app/` rỗng ở phase này

## Risk Assessment

**Chuyển sót ở lời gọi nhiều dòng.**
`tests/test_prefill_submission.py` có lời gọi `monkeypatch.setattr` trải trên nhiều dòng
(`:149-151` và tương tự), grep một dòng dễ đếm thiếu — đây chính là lý do con số đúng là
36 chứ không phải 31.
Tín hiệu: `Select-String` cuối phase vẫn còn kết quả.
Phản ứng: dùng đúng pattern `main_routes, "get_storage_service"` (không neo vào
`monkeypatch.setattr(`) làm tiêu chí nghiệm thu.

**Test dựa vào việc `monkeypatch` tự hoàn tác theo thứ tự.**
`monkeypatch` hoàn tác theo LIFO ở cuối test; fixture `_reset_storage_provider` chạy ở
teardown fixture. Với storage stub, thứ tự này không quan trọng vì không có state chồng lấn.
Tín hiệu: fail chỉ khi chạy cả suite.
Phản ứng: dùng hai lệnh đảo thứ tự ở trên để khoanh vùng, không đoán.

**Fixture autouse mới va với `setup_logging` autouse sẵn có.**
Hai fixture autouse độc lập, không cùng chạm tài nguyên.
Tín hiệu: lỗi thứ tự fixture khi collect.
Phản ứng: nếu có, đặt `_reset_storage_provider` phụ thuộc tường minh vào không gì cả và
giữ nó ở cuối file conftest.

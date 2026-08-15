---
phase: 4
title: "Verification And Coupling Map"
status: done
priority: P1
effort: "2h"
dependencies: [3]
---

# Phase 4: Verification And Coupling Map

## Overview

Nghiệm thu toàn bộ Phase 1 theo acceptance criteria đã chốt, và bàn giao bản đồ 23
coupling `app.main_routes` còn lại cho Phase 3 của kế hoạch tổng (tách route).

## Requirements

**Functional**

- Toàn bộ success criteria trong `plan.md` được kiểm chứng bằng lệnh, không suy luận.
- Bản đồ coupling nêu rõ từng điểm sẽ chuyển về module nào sau khi tách route.

**Non-functional**

- Không sửa code trong phase này. Đây là phase nghiệm thu và tài liệu.

## Architecture

Phase 1 chỉ gỡ coupling storage. 23 điểm còn lại là test chạm trực tiếp symbol nội bộ
của `main_routes`; chúng sẽ đứt khi Phase 3 (kế hoạch tổng) di chuyển symbol. Bản đồ này
tồn tại để việc đó là công việc đã lường trước, không phải sự cố.

### Bản đồ coupling còn lại

| Symbol | Số điểm | File test | Chủ sở hữu sau Phase 3 |
|---|---|---|---|
| `active_submitters` | 6 | `test_prefill_submission.py` (2), `test_submission_persistence.py` (2), `test_submission_status_retention.py` (2) | `app/services/submission_manager.py` |
| `_run_submission` | 5 | `test_prefill_submission.py` (1), `test_submission_persistence.py` (3), `test_submission_status_retention.py` (1) | `app/services/submission_manager.py` |
| `_upload_cache` | 3 | `test_prefill_submission.py` (3) | `app/services/upload_cache.py` |
| `_cleanup_finished_submitters` | 2 | `test_submission_status_retention.py` (2) | `app/services/submission_manager.py` |
| `_runtime_mode` | 2 | `test_runtime_diagnostics_route.py` (2) | `app/routes/health.py` |
| `sys` (patch `frozen`) | 3 | `test_runtime_diagnostics_route.py` (3) | `app/routes/health.py` |
| `time` (patch `monotonic`) | 1 | `test_prefill_submission.py` (1) | `app/services/upload_cache.py` |
| `Config.MAX_UPLOAD_ROWS` | 1 | `test_form_processor.py` (1) | `app/config.py` (Phase 4 kế hoạch tổng) |
| **Tổng** | **23** | 5 file | |

Ba file mang gần hết rủi ro: `test_prefill_submission.py` (7), `test_submission_persistence.py` (5),
`test_submission_status_retention.py` (5). Phase 3 của kế hoạch tổng nên chuyển ba file
này ngay sau khi tách `submission_manager` và `upload_cache`, trước khi tách các route khác.

## Related Code Files

- Create: mục "Bản đồ coupling còn lại" trong file này là deliverable
- Modify: `docs/ARCHITECTURE.md` — chỉ khi cần một dòng về seam storage
- Read-only: toàn bộ `tests/`

## Implementation Steps

1. Chạy trọn bộ lệnh nghiệm thu ở mục Verification, ghi lại output thật.
2. Đối chiếu từng mục trong `plan.md` → Success Criteria; đánh dấu PASS/FAIL kèm bằng chứng.
3. Nếu có FAIL: quay lại phase tương ứng, không nới tiêu chí.
4. Chạy `git diff --stat` để xác nhận scope thay đổi đúng dự kiến.
5. Thêm một dòng vào `docs/ARCHITECTURE.md` mô tả seam storage, chỉ khi mô tả boundary
   hiện tại đã sai sau thay đổi. Không viết lại tài liệu.
6. Mở PR cho nhánh `refactor/phase-1-test-isolation`.

## Verification

```powershell
# 1. Suite đầy đủ
.\.venv\Scripts\python.exe -m pytest -q

# 2. Lint — cùng phạm vi CI; ruff chưa cài sẵn trong .venv
.\.venv\Scripts\python.exe -m pip install ruff
.\.venv\Scripts\python.exe -m ruff check app/ tests/ config.py wsgi.py

# 3. Không còn coupling storage
Select-String -Path tests\*.py -Pattern 'main_routes, "get_storage_service"'

# 4. Dữ liệu thật không bị chạm (xem script mtime ở phase-01)

# 5. Phạm vi diff runtime
git diff --stat app/          # chỉ app/services/__init__.py
git diff --stat -- . ':!app' ':!tests'   # phải rỗng

# 6. Sandbox: chạy pytest không elevation
```

## Success Criteria

- [x] 215 passed, 1 deselected — đúng bằng baseline trước Phase 1
- [x] `ruff check app/ tests/ config.py wsgi.py` sạch — cùng phạm vi với CI
- [x] 0 kết quả cho `main_routes, "get_storage_service"`
- [x] `db.json` và `app.log` thật không đổi mtime
- [x] `pytest` PASS trong sandbox không cần elevation
- [x] `git diff --stat app/` chỉ hiện `app/services/__init__.py`
- [x] Không file nào ngoài `app/services/__init__.py` và `tests/` bị sửa
- [x] Bản đồ 23 coupling đầy đủ và khớp với `grep` thực tế

## Risk Assessment

**Số test đổi so với baseline.**
Baseline `215 passed, 1 deselected` lấy từ `docs/PROJECT_REFACTOR_AUDIT.md:59`. Nếu số
khác đi mà không phải do ta thêm/bớt test, tức có test bị skip âm thầm (ví dụ
`test_js_prefill_validator.py` skip khi thiếu `node`).
Tín hiệu: tổng số test lệch.
Phản ứng: chạy `pytest -q -rs` để xem lý do skip trước khi kết luận PASS.

**Bản đồ coupling lỗi thời ngay khi viết xong.**
Phase 3 sẽ đọc bản đồ này sau vài ngày.
Tín hiệu: `grep` ở đầu Phase 3 (kế hoạch tổng) ra số khác 23.
Phản ứng: coi `grep` là nguồn sự thật, bản đồ chỉ là điểm khởi đầu — ghi rõ lệnh
tái tạo: `grep -rn "main_routes\.[A-Za-z_]*" tests/*.py`.

**Sandbox test có thể vẫn fail vì lý do khác `%APPDATA%`.**
Ví dụ `webdriver-manager` cố tải driver, hoặc `.env` thiếu.
Tín hiệu: lỗi không phải `PermissionError` trên đường dẫn app-data.
Phản ứng: ghi nhận là hạn chế môi trường riêng, không tính là FAIL của Phase 1; chỉ tiêu
chí `%APPDATA%` mới ràng buộc.

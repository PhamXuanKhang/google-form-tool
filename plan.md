# Plan: Hoàn thiện và Cải tiến Google Form Automation Tool

## Context
Project đã chạy được luồng chính (extract → configure → submit) nhưng còn nhiều bug nghiêm trọng, code chết, và features đã quy hoạch nhưng chưa thực thi. Plan này chia thành 3 mức ưu tiên (P0 → P2) để team biết làm gì trước.

## Trạng thái hiện tại (snapshot — updated 2026-04-26)
- ✅ FormExtractor parse được 12 loại câu hỏi qua `data-params`.
- ✅ FormSubmitter multithreading + stop graceful.
- ✅ MetricsCollector CPU/network/thread real-time.
- ✅ `StorageService` đã fix — 22 tests pass (P0.2 done).
- ✅ `WebViewManager` đã xoá — không sử dụng (P1.4 done).
- ✅ `FormProcessor.load_data_from_file()` đã implement CSV/JSON (P1.1 done).
- ✅ Chrome paths hardcode đã loại bỏ — chỉ dùng `Config` (P0.4 done).
- ✅ `active_submitters` dict (keyed by form_id) — multi-user safe (P1.2 done).
- ✅ `conftest.py` đã fix — `create_app(testing=True)` (P0.3 done).
- ✅ `FLASK_DEBUG` từ env, mặc định False (P0.5 done).
- ✅ `.env.example` đã tạo (P0.1 done).
- ✅ Selenium retry decorator cho `StaleElementReferenceException` (P1.3 done).
- ⚠️ `GEMINI_API_KEY` có nhưng chưa dùng (P2.1 pending).
- ⚠️ Flask-Babel có docs nhưng chưa cài (P2.2 pending).

---

## P0 — Bug Fixes & Security ✅ DONE

### P0.1 — ✅ Secrets management
- `.env` chưa từng commit (verified via `git log`).
- `.env.example` đã tạo với placeholder values.
- **Action for user**: Rotate `GEMINI_API_KEY` và `SECRET_KEY` nếu nghi ngờ bị lộ.

### P0.2 — ✅ `StorageService` fixed
- Viết lại toàn bộ với API nhất quán.
- 22 tests pass.

### P0.3 — ✅ `conftest.py` fixed
- `create_app(testing=True)` hoạt động.
- Xoá `priority_tags` không tồn tại trong model.

### P0.4 — ✅ Chrome paths unified
- `main_routes.py` dùng `Config.CHROME_BINARY_PATH` / `Config.CHROME_DRIVER_PATH`.
- Không còn hardcode.

### P0.5 — ✅ Debug mode controlled
- `FLASK_DEBUG` env var, mặc định `False`.
- Production: dùng Waitress (Windows) hoặc Gunicorn (Linux).

---

## P1 — Core Features Hoàn Thiện ✅ MOSTLY DONE

### P1.1 — ✅ `FormProcessor.load_data_from_file()` implemented
- Hỗ trợ CSV và JSON.
- Không cần thêm dependency (dùng `csv` và `json` built-in).
- Mapping column → question_id (optional, mặc định dùng column name).
- **Còn thiếu**: UI button "Load from file" trong `form_filling.html` + route integration.

### P1.2 — ✅ `active_submitters` dict (multi-user safe)
- Keyed by `form_id`.
- `_cleanup_finished_submitters()` dọn dẹp tự động.
- `stop_submission` và `submission_status` nhận `form_id` parameter.

### P1.3 — ✅ Selenium retry decorator
- `@retry_on_stale(max_retries=3, delay=0.3)` cho `_fill_question()`.
- Đã thêm vào cả `form_extractor.py` và `form_submitter.py`.

### P1.4 — ✅ `WebViewManager` xoá
- Không được import ở đâu → xoá hoàn toàn.

### P1.5 — ⏳ Test suite (partial)
- 23 tests pass (storage + extractor integration).
- **Còn thiếu**: tests cho `FormProcessor`, route tests với mock.
- **Target**: coverage > 60%.

---

## P2 — Cải tiến & Mở rộng

### P2.1 — ✅ Gemini AI integration
**Đã hoàn thành**:
- `app/core/ai_responder.py`: `AIResponder` class với caching
- Routes: `/generate_response` (use_ai=true), `/validate_api_key`, `/ai_status`
- UI: Step 2 có option "AI Generate" với input API key
- API key lưu localStorage (không env) — user tự quản lý
- Thêm `google-generativeai` vào requirements.txt

### P2.2 — ✅ Flask-Babel i18n
**Đã hoàn thành**:
- `Flask-Babel>=4.0.0` trong requirements.txt
- `babel.cfg` cấu hình extraction
- `app/translations/en/LC_MESSAGES/messages.po` — English
- `app/translations/vi/LC_MESSAGES/messages.po` — Tiếng Việt
- Language selector dropdown trong navbar (base.html)
- `get_locale()` trong `app/__init__.py` — session/query param/Accept-Language

### P2.3 — ⏸️ Migrate TinyDB → SQLite (deferred)
**Trigger**: khi `db.json` > 10 MB hoặc concurrent write thành bottleneck.
**Hành động**: đổi sang SQLite + SQLAlchemy. Pydantic models giữ nguyên, chỉ thay layer storage.
**Status**: Deferred — TinyDB đủ cho scope hiện tại.

### P2.4 — ✅ Dockerize
**Đã hoàn thành**:
- `Dockerfile` multi-stage build, `python:3.11-slim`, cài Chromium + chromedriver
- `docker-compose.yml` với volume cho data persistence
- `.dockerignore` loại bỏ files không cần thiết
- Health check endpoint

### P2.5 — ✅ Production deploy
**Đã hoàn thành**:
- `waitress>=2.1.0` trong requirements.txt
- `app.py` với docs cho Waitress/Gunicorn
- Docker CMD dùng Waitress
- `FLASK_DEBUG=0` mặc định

### P2.6 — ✅ UX improvements (partial)
**Đã hoàn thành**:
- Export submission history → CSV (`/export_history/<form_id>` route)
- Export button trong modal (index.html)
- Dark mode toggle (đã có từ trước)
**Còn lại**:
- Progress bar real-time chính xác
- Schedule submission (cron-like)

---

## Critical Files Reference

| File | Status |
|---|---|
| `app/services/storage_service.py` | ✅ Fixed |
| `app/__init__.py` | ✅ Fixed + Flask-Babel init |
| `tests/conftest.py` | ✅ Fixed |
| `app/main_routes.py` | ✅ Fixed (Chrome paths + session-based submitter + export) |
| `app/core/form_processor.py` | ✅ `load_data_from_file()` implemented |
| `app/core/form_extractor.py`, `form_submitter.py` | ✅ Retry decorator added |
| `app/core/webview_manager.py` | ✅ Deleted |
| `app/core/ai_responder.py` | ✅ Gemini AI integration complete |
| `Dockerfile` | ✅ Multi-stage build with Chromium |
| `docker-compose.yml` | ✅ Volume + health check |
| `app/translations/` | ✅ EN + VI translations |
| `babel.cfg` | ✅ Extraction config |

## Verification (sau mỗi phase)

```bash
# Smoke
python app.py                # mở http://localhost:5000, extract 1 form thật, submit thử 2 lần.

# Tests
pytest tests/ -v             # tất cả pass sau P0.

# Lint (nên thêm)
flake8 app/ --max-line-length=100
mypy app/ --ignore-missing-imports
```

## Definition of Done

- **P0 done**: ✅ tests pass 100% (23), Chrome paths unified, debug=False mặc định, `.env.example` created.
- **P1 done**: ✅ `load_data_from_file()` (CSV/JSON), multi-user safe (`active_submitters` dict), Selenium retry decorator, UI file upload, 37 tests.
- **P2 done**: ✅ Gemini AI với UI input (P2.1), ✅ Flask-Babel i18n (P2.2), ✅ Docker (P2.4), ✅ Production deploy (P2.5), ✅ Export history (P2.6).
- **P2 deferred**: ⏸️ SQLite migration (P2.3 — not needed yet), ⏳ scheduled submissions, real-time progress bar.

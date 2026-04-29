# Google Form Automation Tool

## Overview
Web application Flask cho phép tự động extract cấu trúc câu hỏi của bất kỳ Google Form nào (qua Selenium parse `data-params`), cấu hình xác suất chọn từng đáp án, sau đó submit hàng loạt với multithreading. Có monitoring CPU/network/thread real-time và lưu lịch sử submission qua TinyDB.

## Goals
- Tự động hoá end-to-end: extract → configure → submit Google Form không cần Google Forms API.
- Hỗ trợ 12 loại câu hỏi (text, multiple choice, checkbox, scale, grid, date, time, ...).
- Cho phép user tinh chỉnh xác suất chọn đáp án và danh sách câu trả lời tuỳ biến trước khi submit.
- Multithreading để submit số lượng lớn với delay ngẫu nhiên, tracking success/fail real-time.
- Web UI đơn giản (Flask + Jinja2 + vanilla JS), không phụ thuộc framework frontend.

## Current Tech Stack
Python 3.x / Flask 3.1 / Selenium 4.32 (Chrome) / TinyDB 4.8 (JSON) / Pydantic 2.11 / python-dotenv / psutil / pytest / Jinja2 + vanilla JS + CSS / Flask-Babel (i18n) / Google Generative AI (Gemini) / Waitress (production WSGI).

## Workflow (Current)

```
[Browser UI - form_filling.html]
  ↓ nhập Google Form URL
  ↓ POST /form_filling/extract → [Flask Server]
        ↓ kiểm tra TinyDB (skip nếu đã có)
        ↓ FormExtractor (Selenium): parse data-params → Form object (Pydantic)
        ↓ StorageService.save_form() → db.json
  ↓ GET /form_filling/preview → render câu hỏi để user cấu hình
  ↓ user chỉnh xác suất / câu trả lời tuỳ biến
  ↓ POST /save_edit → FormProcessor.apply_user_edits()
  ↓ POST /start_submission → [Flask Server]
        ↓ FormSubmitter: tạo N threads, mỗi thread mở Chrome
        ↓ fill_page() → _fill_question() theo type → click Next/Submit
        ↓ track success/fail qua threading.Event
  ↓ GET /submission_status (poll) → JSON status real-time
        ↓ MetricsCollector: CPU + network + thread monitoring
```

## Commands
```bash
# Cài dependencies
pip install -r requirements.txt

# Chạy web app (development)
python wsgi.py
# Truy cập http://localhost:5000

# Chạy web app (production - Waitress)
python -m waitress --host=0.0.0.0 --port=5000 app:app

# Docker
docker-compose up -d              # Build + run container
docker-compose logs -f            # Xem logs
docker-compose down               # Stop + remove

# CLI extract độc lập (lưu ra extracted_form_data.json)
python extract_form.py <google_form_url>
python extract_form.py <google_form_url> --visible

# Tests
pytest tests/ -v
pytest tests/test_storage_service.py -v          # unit
pytest tests/test_form_extractor.py -v           # integration (cần Chrome)

# i18n (Flask-Babel)
pybabel extract -F babel.cfg -o messages.pot .   # Extract strings
pybabel update -i messages.pot -d app/translations  # Update .po files
pybabel compile -d app/translations              # Compile to .mo
```

Yêu cầu cài đặt thủ công: **Chrome binary** + **ChromeDriver** đúng phiên bản, cấu hình path qua `.env`. Docker image có sẵn Chromium.

## Architecture (Flask Web App)

### Layered View
- **Web Layer**: `app/main_routes.py` — Blueprint `main`, gồm UI routes + REST API endpoints.
- **Templates**: `app/templates/` — Jinja2 (`base.html`, `index.html`, `form_filling.html`, `about.html`).
- **Static**: `app/static/js/` (vanilla JS, không framework) + `app/static/css/`.
- **Core (Business Logic)**: `app/core/` — `FormExtractor`, `FormSubmitter`, `FormProcessor`.
- **Service Layer**: `app/services/storage_service.py` — TinyDB wrapper, context manager.
- **Models**: `app/models.py` — Pydantic: `Form`, `Page`, `Question`, `AnswerConfig`, `AnswerOption`, `Submission`, `ResponseConfig`, `FormData`.
- **Monitoring**: `app/monitoring/` — Singleton `MetricsCollector` + CPU/Network/Thread monitors qua `psutil`.
- **Config**: `config.py` đọc `.env` qua `python-dotenv`.
- **Logging**: `app/logging_config.py` — logging tập trung, không dùng `print`.

### Module Map (Key Paths)
- `app.py` — entry point, gọi `create_app()` chạy Flask ở `0.0.0.0:5000`.
- `app/__init__.py` — Application Factory `create_app()`, đăng ký blueprint, Flask-Babel init.
- `app/main_routes.py` — toàn bộ routes UI + REST endpoints; `active_submitters` dict (keyed by form_id).
- `app/core/form_extractor.py` — `FormExtractor`: Selenium parse `data-params`, navigate multi-page, hỗ trợ 12 loại câu hỏi.
- `app/core/form_submitter.py` — `FormSubmitter`: thread pool mỗi thread mở 1 Chrome, fill + submit, `threading.Event` stop graceful.
- `app/core/form_processor.py` — `FormProcessor`: random response (lorem ipsum, email, scale), apply user edits, load data from CSV/JSON.
- `app/core/ai_responder.py` — `AIResponder`: Gemini AI integration, context-aware response generation.
- `app/services/storage_service.py` — `StorageService`: TinyDB CRUD `Form` + `Submission`.
- `app/models.py` — Pydantic models (deterministic ID từ URL: `Form.get_id_from_url`, `Form.from_url`).
- `app/monitoring/metrics_collector.py` — Singleton facade gom CPU + Network + Thread monitors.
- `app/translations/` — Flask-Babel translations (EN, VI).
- `app/utils.py` — `generate_uuid_from_url()` (deterministic UUID từ URL).
- `extract_form.py` — CLI script độc lập, output `extracted_form_data.json`.
- `Dockerfile`, `docker-compose.yml` — Docker deployment config.

### Data Flow
1. User nhập URL Google Form trong `form_filling.html`.
2. `POST /form_filling/extract` → kiểm tra TinyDB (deterministic ID từ URL); nếu chưa có, gọi `FormExtractor` → lưu `Form` vào `db.json`.
3. `GET /form_filling/preview` → trả JSON cấu trúc form để render UI cấu hình.
4. User chỉnh xác suất + answers tuỳ biến → `POST /save_edit` → `FormProcessor.apply_user_edits()`.
5. `POST /start_submission` → khởi tạo `FormSubmitter` (lưu vào `active_submitters[form_id]`) → spawn N threads.
6. Mỗi thread mở Chrome, navigate URL, gọi `fill_page()` → `_fill_question()` theo type → submit.
7. Frontend poll `GET /submission_status` → status real-time từ `FormSubmitter.get_status()` + metrics.
8. `StorageService.add_submission()` lưu kết quả batch vào `db.json`.

### Integration Points
- **Selenium + ChromeDriver**: bắt buộc Chrome binary + ChromeDriver phiên bản tương thích.
- **TinyDB**: file JSON `app/services/db.json`, không cần DB server.
- **Google Gemini AI**: tích hợp qua `app/core/ai_responder.py`. API key nhập từ UI (không từ env) → lưu localStorage.
- **Google Forms**: KHÔNG dùng official API — chỉ parse HTML qua Selenium.
- **Flask-Babel**: i18n support (EN/VI). Switch language qua dropdown trong navbar.

### Docker Support
- `Dockerfile`: Multi-stage build, `python:3.11-slim`, cài Chromium + chromedriver từ apt.
- `docker-compose.yml`: 1 service, volume `form_data` cho TinyDB persistence.
- `.dockerignore`: loại bỏ `.git`, `tests/`, `*.md` (trừ README).
- Health check: `http://localhost:5000/` mỗi 30s.
- Production server: Waitress (không dùng Flask dev server).

### Config, Secrets, and Security
- `.env` chứa: `SECRET_KEY`, `DB_PATH`, `CHROME_BINARY_PATH`, `CHROME_DRIVER_PATH`, `GEMINI_API_KEY`, `FLASK_DEBUG`.
- KHÔNG commit `.env`. Đảm bảo `.gitignore` chứa nó. Xem `.env.example` cho template.
- `Config` class trong `config.py` đọc từ `.env`, các module đọc qua `Config`.

### Observability and Reliability
- Logging qua `app/logging_config.py`, không dùng `print`.
- `MetricsCollector` (Singleton) cung cấp CPU/network/thread metrics real-time cho UI.
- `FormSubmitter` dùng `threading.Event` để stop gracefully.
- Selenium có retry decorator cho `StaleElementReferenceException`.

## Key Patterns
- **Application Factory + Blueprint**: `create_app()` + blueprint `main`.
- **Service Layer**: `StorageService` tách DB logic khỏi routes; dùng context manager (`with`).
- **Singleton**: `MetricsCollector.get_instance()`.
- **Pydantic Validation**: tất cả data đi qua `Form`, `Question`, `AnswerConfig` validate strict.
- **Deterministic ID**: `Form.get_id_from_url(url)` → cùng URL → cùng ID, tránh duplicate.
- **Threading**: `FormSubmitter` dùng thread pool + shared stop event, không async/await.

## Question Types Supported (FormExtractor)
12 loại Google Form questions: short answer, paragraph, multiple choice, checkbox, dropdown, linear scale, multiple choice grid, checkbox grid, date, time, file upload, rating. Mỗi type có handler riêng trong `_fill_question()` của `FormSubmitter`.

## Code Style
- snake_case functions/variables, PascalCase classes, UPPER_CASE constants.
- Type hints đầy đủ (style Python 3.9+: `List[str]`, `Optional[str]`).
- Docstrings tiếng Anh kiểu Google/NumPy.
- Pydantic models cho mọi data structure rời (không dùng dict trần).
- Logging qua `logging_config`, KHÔNG dùng `print`.

## Environment Variables
Xem `.env` (không commit). Keys:
- `SECRET_KEY` — Flask session/CSRF key.
- `DB_PATH` — đường dẫn `db.json` cho TinyDB.
- `CHROME_BINARY_PATH` — đường dẫn Chrome binary.
- `CHROME_DRIVER_PATH` — đường dẫn ChromeDriver.
- `FLASK_DEBUG` — `0` (default) hoặc `1` để bật debug mode.

Note: `GEMINI_API_KEY` được user nhập qua UI và lưu localStorage, không cần env var.

## Agent Behavior

**Think Before Coding** — Đọc `app/core/`, `app/models.py`, `app/main_routes.py` trước khi sửa. Nêu rõ assumptions.

**Simplicity First** — Không over-engineer. TinyDB + Flask đủ cho scope hiện tại.

**Surgical Changes** — Chỉ chạm những gì cần. Không refactor lan man.

**Goal-Driven Execution** — Với task nhiều bước:
```text
1. [Bước] → verify: [cách kiểm tra]
2. [Bước] → verify: [cách kiểm tra]
```

## Rules
- LUÔN chạy `pytest tests/ -v` sau khi sửa `app/core/` hoặc `app/services/`.
- LUÔN đọc Chrome paths qua `Config`, KHÔNG hardcode trong route hoặc module.
- KHÔNG commit `.env`, `db.json` (runtime data), API keys, SECRET_KEY.
- KHÔNG sửa `extracted_form_data.json` (output của CLI script — chỉ commit khi cần làm sample).
- Provider/handler câu hỏi mới PHẢI cập nhật cả `FormExtractor._parse_question()` và `FormSubmitter._fill_question()`.
- External calls (Selenium, Gemini sau này) PHẢI có error handling + timeout.
- Selenium WebDriver PHẢI close (context manager hoặc try/finally) tránh leak Chrome process.
- `active_submitters` dict cho phép multi-user concurrent submission (keyed by form_id).

## Verification
Sau mỗi thay đổi:
```bash
pytest tests/ -v
python wsgi.py        # smoke test, mở http://localhost:5000
```

## Recurring Mistakes
<!-- Thêm lỗi mới vào đây mỗi khi AI mắc lỗi lặp. Format: -->
<!-- - [Ngày] Lỗi: ... → Fix: ... -->

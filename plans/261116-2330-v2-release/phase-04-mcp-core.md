# Phase 4 — MCP server lõi và Claude skill

Nhánh: `feat/v2-mcp-core` (từ `feat/v2-simulation-report`).

Mục tiêu: một agent thêm MCP server này vào là làm được trọn luồng extract → cấu hình → mô
phỏng → chạy → đọc báo cáo, thay cho việc người dùng tự cấu hình trong UI.

## Mô hình tiến trình (đã chốt)

MCP server là tiến trình stdio **proxy tới backend đang chạy qua HTTP localhost**. Nó không mở
`db.json` và không import service ghi dữ liệu.

- Lý do: TinyDB chỉ khoá trong một tiến trình (`app/services/storage_service.py:12`) và
  registry đợt chạy nằm trong bộ nhớ backend (`app/services/submission_manager.py:10`).
- Tìm backend: đọc `<APP_DATA>/runtime.json` (ghi ở phase 2), gọi `GET /healthz`. Không có
  file, pid không còn, hoặc healthz lỗi → mọi tool trả lỗi rõ ràng: "Google Form Automation
  Tool chưa chạy. Hãy mở app rồi thử lại." Không tự khởi động backend.
- POST không có `Origin` đã qua kiểm tra same-origin (`app/routes/__init__.py:28-30`); không
  nới lỏng guard đó. Chỉ kết nối tới `127.0.0.1`.
- Giới hạn 500/10 và 409 khi đang chạy tự áp dụng vì đi qua cùng route.

## Triển khai

- Đọc tài liệu hiện hành của Python MCP SDK trước khi viết (tên package, API server stdio,
  cách khai báo tool và schema, cách test bằng client trong bộ nhớ). Ghim version trong
  `pyproject.toml`, `uv lock`, chạy `pip-audit` như CI.
- `app/mcp_server.py`: không import `app.create_app` hay `wsgi`; chỉ dùng thư viện HTTP chuẩn
  (`urllib`) hoặc client đã có sẵn trong dependency, và SDK MCP. Không in gì ra stdout ngoài
  giao thức; log đi stderr hoặc file trong `LOG_DIR`.
- Tool (tên dạng snake_case, mô tả ngắn nói rõ khi nào dùng, schema đầu vào chặt):

  | Tool | Route | Ghi chú |
  | --- | --- | --- |
  | `app_status` | `/healthz`, `/diagnostics/runtime` | Version, Chrome/ChromeDriver sẵn sàng hay chưa |
  | `list_forms` | route JSON mới `GET /forms` | Thêm route trả danh sách tóm tắt (id, title, url, số câu) |
  | `extract_form` | `/form_filling/extract` | Nhận URL Google Form |
  | `get_form` | route JSON mới `GET /forms/<form_id>` | Câu hỏi, lựa chọn, cấu hình hiện tại |
  | `set_answer_config` | `/save_edit` | Tỉ lệ từng lựa chọn, câu trả lời văn bản |
  | `simulate` | `/simulate` | Trả tóm tắt + mẫu |
  | `start_run` | `/start_submission` | Bắt buộc `num_submissions`; mặc định 1 luồng |
  | `run_status` | `/submission_status` | |
  | `stop_run` | `/stop_submission` | Bắt buộc `form_id`; không cho dừng tất cả qua MCP |
  | `list_runs`, `get_report` | `/runs`, `/runs/<id>` | |
  | `retry_failed` | `/runs/<id>/retry` | |

  Kiểm xem `/form_filling/extract` và `/save_edit` có phụ thuộc Flask session không (US-001
  AC4 nhắc "current session"). Nếu có, proxy giữ cookie jar trong tiến trình, hoặc thêm tham
  số `form_id` tường minh theo hướng chỉ thêm; không đổi hành vi hiện có.
- Kết quả tool là JSON gọn: cắt danh sách dài, không trả đường dẫn nội bộ hay stack trace.
  Lỗi HTTP 4xx chuyển thành lỗi tool kèm thông báo của backend.
- `start_run` qua MCP không nhận API key; AI text cần key thì agent hướng người dùng làm trong UI.

## Đóng gói

- `wsgi.py:49` in ra stdout và cờ console của `GoogleFormTool.exe` cố định lúc build
  (`google_form_tool.spec:10`), nên MCP là **exe console thứ hai trong cùng bundle**: thêm một
  `Analysis`/`EXE` thứ hai trong `google_form_tool.spec` (script vào `app/mcp_server.py`, tên
  `GoogleFormToolMcp`, `console=True`), gộp vào cùng `COLLECT` để dùng chung thư viện.
- Kiểm `scripts/package-windows.ps1`, `build_exe.bat` và `electron-builder.yml`
  (`extraResources` từ `dist/GoogleFormTool`) để exe mới theo vào installer.
- Chạy từ source: `uv run python -m app.mcp_server`.

## Settings và skill

- Trang Settings thêm mục "Kết nối agent (MCP)": đường dẫn thật tới exe MCP (hoặc lệnh `uv`
  khi chạy từ source, lấy từ runtime mode trong `app/config.py`), khối JSON cấu hình để dán
  vào Claude Desktop, lệnh `claude mcp add` cho Claude Code, nút sao chép. Thêm khoá tương
  ứng vào `/diagnostics/runtime` (chỉ thêm).
- `skills/google-form-automation/SKILL.md`: frontmatter `name`, `description` (nêu rõ khi nào
  kích hoạt); thân bài: điều kiện (app đang mở), quy trình chuẩn (app_status → extract/get →
  đề xuất cấu hình và hỏi người dùng → simulate → trình bày phân phối → chỉ start_run sau khi
  người dùng đồng ý → run_status → get_report), giới hạn (500/10, không tạo/sửa form), và
  nguyên tắc chỉ chạy trên form người dùng sở hữu hoặc được phép kiểm thử. Trang Settings có
  nút tải/xem file này.

## Test bắt buộc

- Test tool qua client MCP trong bộ nhớ với backend là Flask test client hoặc HTTP giả: mỗi
  tool gọi đúng route, đúng body; lỗi 400/404/409 thành lỗi tool.
- Không có `runtime.json` hoặc healthz lỗi → thông báo "hãy mở app".
- `stop_run` thiếu `form_id` bị từ chối ở tầng schema.
- `import app.mcp_server` không import `selenium`, `flask` hay `app.services.storage_service`
  (kiểm `sys.modules` trong subprocess).
- Route snapshot: chỉ thêm `GET /forms`, `GET /forms/<form_id>`.
- Smoke đóng gói: build, start backend đóng gói trên port 5056, spawn `GoogleFormToolMcp.exe`
  bằng pipe, gửi `initialize` rồi `tools/list`, khẳng định mọi dòng stdout parse được thành
  JSON-RPC và danh sách tool đủ; gọi `app_status` trả version. Dừng cả hai tiến trình, xác
  nhận port trống. Viết thành script trong `scripts/` để phase 8 chạy lại.

## Cuối phase

- Gate + packaging smoke + smoke MCP.
- Decision record `docs/decisions/0005-mcp-proxy.md`.
- User story US-012; bảng route; `docs/TEST_MATRIX.md`; `docs/ARCHITECTURE.md` (entry point
  mới, ranh giới "MCP không chạm storage").
- Push; fast-forward `release/v2`; cập nhật PR.

## Điều kiện dừng riêng

Exe MCP đóng gói không chạy được qua pipe sau 2 lần sửa: giữ đường chạy từ source
(`python -m app.mcp_server`), ghi rõ trong Settings và báo cáo là bản đóng gói chưa có exe MCP,
và coi acceptance 7 là chưa đạt (PR ở lại draft theo quy tắc phase 8).

## Rollback

`git revert`; gỡ dependency và mục `.spec`.

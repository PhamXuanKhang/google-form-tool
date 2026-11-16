# Brainstorm — Bản 2.0: tính năng khác biệt, giao diện mới, MCP

Date: 2026-11-16
Branch at capture: `master` (85d14b6, v1.2.0)
Mode: `--advice` (kongming: go có điều kiện, các chỉnh sửa đã nhập vào contract)
Status: contract accepted, plan tại `plans/261116-2330-v2-release/plan.md`

## Nghiên cứu sản phẩm tương tự

| Sản phẩm | Loại | Có gì | Thiếu gì |
| --- | --- | --- | --- |
| Borang | Extension, freemium | Submit nhiều lần, random/tỉ lệ (premium), import CSV, AI answer, hẹn giờ, chỉnh tốc độ | Không xem trước phân phối, không báo cáo sau khi gửi |
| FormBlitz, GFormTasker | Extension | Random/balanced, delay | Không cấu hình phân phối chi tiết, không lịch sử |
| AutoForm (GitHub, mraheja) | Script Python | Random/tuần tự/xác suất theo câu, rải trong N phút | Sửa file config bằng tay, không UI |
| Apify Google Form Bulk Submitter | Dịch vụ trả phí (khoảng $20/1.000 lượt) | Submit từ JSON/CSV | Dữ liệu rời máy, không sinh câu trả lời |
| Autofillm, FormPilot, AI Form Filler (Gemini) | Extension AI | Persona từ prompt, gõ giống người, điền một form | Chỉ điền từng lượt, không chạy hàng loạt |
| Các repo "form spammer" | Script | Đọc `FB_PUBLIC_LOAD_DATA_`, gửi nhanh | Không kiểm soát, không báo cáo |

Nguồn là trang store và trang nhà phát triển, chưa kiểm chứng bằng cách dùng thử.

Định vị 2.0: biết trước kết quả trước khi gửi, câu trả lời nhất quán theo persona, đối chiếu
thực tế với mục tiêu sau khi gửi, và điều khiển được bằng agent qua MCP. Chưa công cụ nào
trong bảng gộp đủ bốn điểm này.

## Use case tổng hợp

| Use case | Người dùng | Tính năng 2.0 |
| --- | --- | --- |
| Kiểm thử form trước khi phát hành (logic rẽ nhánh, câu bắt buộc, dashboard phản hồi) | Người tạo form | Mô phỏng, báo cáo, gửi lại lượt lỗi |
| Sinh dữ liệu thử có cấu trúc cho demo hoặc pipeline phân tích | Người làm dữ liệu | Persona, preset, template |
| Cấu hình nhanh form dài mà không chỉnh tay từng câu | Mọi người dùng | AI Autopilot, preset |
| Chạy đợt dài mà không giữ máy ở trạng thái gửi dồn | Mọi người dùng | Chạy rải, pause/resume |
| Giao việc cho agent bằng một câu lệnh | Người dùng Claude/agent | MCP server + skill |

## Contract

### Outcome

Bản 2.0.0 trên một PR vào `master`, gồm 7 nhóm:

1. Giao diện mới: design system riêng, app shell có sidebar, dark mode thật, asset đóng gói
   offline, chuyển bước mượt, dashboard tiến độ realtime.
2. Mô phỏng trước khi gửi: sinh N câu trả lời trong app, biểu đồ phân phối từng câu và bảng
   mẫu, không gọi tới Google.
3. Báo cáo sau khi gửi: bản ghi từng lượt, biểu đồ thực tế so với mục tiêu, gửi lại lượt lỗi,
   export.
4. Persona + AI Autopilot: persona có trọng số với phân phối riêng; Gemini đề xuất cấu hình
   cả form từ mô tả bằng lời, người dùng xem rồi mới áp dụng.
5. Chạy rải theo thời gian: rải lượt gửi trong một khung giờ, tạm dừng/tiếp tục, tiếp tục được
   sau khi mở lại app.
6. Preset và template: preset một chạm, lưu/nhân bản/xuất/nhập cấu hình JSON.
7. MCP server + Claude skill: agent extract, cấu hình, mô phỏng, chạy, dừng và đọc báo cáo.

### Constraints

- Giữ Flask + Jinja + JS thuần; không thêm bước build frontend.
- Route hiện có giữ nguyên URL, method, status, JSON shape; route mới chỉ thêm.
- Lưu trữ chỉ thêm trường tuỳ chọn và store mới; form lưu từ 1.x vẫn mở được.
- Giữ giới hạn 500 lượt mỗi đợt và 10 luồng, cho cả UI lẫn MCP.
- API key Gemini không ghi log, không lưu, không trả về.
- Lane high-risk theo `docs/WORKFLOW.md`: có decision record và packaging smoke sau mỗi phase
  chạm `.spec` hoặc dependency.
- Goal run không có tài khoản Google hay Gemini key thật: kiểm chứng tự động dùng adapter giả.
- Git: nhánh xếp chồng theo phase, push, một PR vào `master`. Không tag, không publish.

### Non-goals

- Agent tạo/sửa Google Form và sửa Copy Form cho form thật (dời sang 2.1).
- Viết lại sang React/SPA.
- Xoay proxy/IP, vượt captcha, vượt đăng nhập, giả lập nhiều tài khoản Google.
- Chỉnh dữ liệu để đạt chỉ số thống kê định trước (Cronbach's alpha, độ phù hợp SEM). App
  định vị là công cụ kiểm thử form và sinh dữ liệu thử.
- Auto-update, code signing, đóng gói macOS/Linux.
- MCP tự bật backend khi app đang đóng.

### Acceptance criteria

| # | Bằng chứng |
| --- | --- |
| 1 | Test render 6 trang không chứa URL asset `http(s)` ngoài; asset nằm dưới `app/static/vendor/` |
| 2 | Route mô phỏng trả phân phối và mẫu; test chứng minh không khởi tạo Selenium driver; với seed cố định, kết quả mô phỏng trùng với các lượt được lưu khi chạy bằng driver giả, ở cả hai chế độ gửi |
| 3 | 500 lượt từ 10 luồng đều được lưu vào file JSONL trong khi `db.json` không đổi một byte; dòng cuối bị cắt cụt vẫn đọc được; route báo cáo trả thực tế so với mục tiêu; gửi lại chỉ chạy các lượt lỗi |
| 4 | Với các persona tách biệt, mọi đáp án trong một lượt đến từ cùng một persona và tỉ lệ persona đúng trọng số; phản hồi Gemini giả lập sai schema bị từ chối, đúng schema chỉ áp dụng sau bước xác nhận |
| 5 | Test với đồng hồ giả và submitter giả, mô phỏng khởi động lại bằng engine thứ hai trên cùng store: không lượt nào gửi hai lần, `in_flight` thành `unknown`, số lượt đến hạn mỗi nhịp bị chặn trên |
| 6 | Xuất rồi nhập template cho cấu hình giống hệt; preset cho tổng 100% |
| 7 | Packaging smoke khởi chạy exe MCP qua pipe, gửi `initialize` và `tools/list`, stdout chỉ chứa JSON-RPC; test khẳng định mọi module `app.*` có trong `.spec`; có `SKILL.md`; trang Settings hiện cấu hình MCP để dán |
| Chung | pytest và ruff xanh; số test không giảm so với baseline; packaging smoke `/healthz` 200; version 2.0.0; changelog, README, user stories, test matrix, decision record; PR mở và CI xanh |

## Quyết định đã chốt (user, 2026-11-16)

| # | Quyết định | Chọn |
| --- | --- | --- |
| 1 | Tính năng 2.0 | Cả bốn nhóm đề xuất, cộng MCP server + skill |
| 2 | Hướng UI | Giữ Jinja, dựng design system riêng |
| 3 | Agent tạo/sửa form | Dời sang 2.1 |
| 4 | Git | Push nhánh, mở PR; không tag, không publish |

## Trade-offs

- **Giữ Jinja + design system (chọn):** dựa vào giả định JS thuần đủ cho dashboard realtime và
  trang persona. Hỏng trước tiên khi trang persona cần state phức tạp; khi đó tách module JS.
- **Viết lại React:** hỏng trước tiên ở pipeline đóng gói và i18n trong một lần chạy không
  người trông.
- **MCP proxy qua HTTP localhost (chọn):** hỏng khi app đang đóng hoặc không biết port; xử lý
  bằng file runtime (port, pid) và thông báo "hãy mở app".
- **MCP mở thẳng TinyDB:** hỏng bằng mất cập nhật, vì TinyDB ghi lại cả file và chỉ khoá trong
  một tiến trình (`app/services/storage_service.py:12`); registry đợt chạy cũng chỉ nằm trong
  bộ nhớ backend (`app/services/submission_manager.py:10`).
- **Bản ghi từng lượt trong JSONL (chọn) so với trong `db.json`:** ghi vào `db.json` làm mỗi
  lượt ghi lại cả file; tắt cứng giữa lúc ghi có thể cắt cụt dữ liệu form đã lưu.

Better approaches: none — hướng được yêu cầu là đúng, điều chỉnh duy nhất là dời tạo/sửa form
sang 2.1 (bằng chứng: `app/adapters/browser/form_copier.py:158` chưa có đường ghi thật; OAuth
là hard gate trong `docs/WORKFLOW.md`).

## Bằng chứng nền

- CDN: `app/templates/base.html:7-8,107-108`; `app/templates/form_filling.html:6,333-334,342`.
- Lịch sử chỉ lưu số tổng: `app/models.py:124`.
- Hai bộ sinh câu trả lời khác nhau: rút độc lập (`app/domain/form_processor.py:236`) và phân
  bổ theo quota (`:267`); không có seed.
- Same-origin cho phép POST không có `Origin`/`Referer`: `app/routes/__init__.py:28-30`.
- Port backend: 5123 dưới Electron (`electron/backendProcess.js:5`), 5000 khi chạy từ source
  (`wsgi.py:36`).
- Electron tắt backend bằng `taskkill /F`: `electron/backendProcess.js:91`.
- `wsgi.py:49` in ra stdout; cờ console của exe cố định lúc build (`google_form_tool.spec:10`).

## Rủi ro chưa khép

1. Phạm vi 9 phase cho một lần chạy (lần trước 6). Quy tắc dừng trong plan giữ phần đã xong
   phát hành được.
2. Thẩm mỹ giao diện không tự kiểm bằng test; user xem bằng mắt sau khi chạy.
3. Exe MCP dạng stdio sau khi đóng gói chưa được kiểm chứng; smoke ở acceptance 7 trả lời
   trong lúc chạy.
4. Hành vi thật của Google Forms và Gemini không được kiểm trong goal run.

## Handoff

Next: `/goal` với `plans/261116-2330-v2-release/plan.md`, có `--advice`.

# Phase 1 — Nền giao diện

Nhánh: `feat/v2-ui-foundation` (từ `release/v2`).

Mục tiêu: app render đầy đủ khi không có mạng, có design system riêng và app shell mới. Chưa
thêm tính năng. Các phase sau dựng màn hình mới trên nền này.

## Hiện trạng

- CDN: `app/templates/base.html:7-8,107-108` (Bootstrap 5.3.6, Font Awesome 6.7.2, Popper);
  `app/templates/form_filling.html:6,333-334,342` (driver.js 1.3.1, ECharts 5.4.3, Chart.js
  không ghim version).
- CSS riêng chỉ khoảng 90 dòng (`app/static/css/styles.css`, `components/`).
- Navbar ngang + banner ảnh + footer (`base.html:15-105`); dark mode là một nút gọi
  `toggleDarkMode()` trong `app/static/js/scripts.js`.

## Commit

1. `build(ui): vendor frontend assets for offline use`
   - Tải đúng các version đang dùng vào `app/static/vendor/` (Bootstrap CSS/JS bundle, Font
     Awesome CSS + webfonts, driver.js, ECharts). Bundle Bootstrap đã gồm Popper nên bỏ thẻ
     Popper riêng.
   - Kiểm xem Chart.js và ECharts có cùng được dùng không (`grep -n "Chart(\|echarts" app/static/js`).
     Giữ một thư viện biểu đồ; chuyển phần còn lại sang thư viện được giữ.
   - Thay mọi thẻ CDN bằng `url_for('static', ...)`. Kiểm tra SRI của file tải về khớp hash
     đang ghi trong template trước khi xoá thuộc tính `integrity`.
   - Thêm test: render 6 trang (`/`, `/form_filling`, `/form_copy`, `/settings/diagnostics`,
     `/about`, và trang lỗi nếu có) không chứa `src=`/`href=` trỏ tới `http(s)://` cho script,
     stylesheet, font. Link điều hướng ra ngoài (GitHub, LinkedIn) không tính.
   - Thêm `app/static/vendor` vào kiểm tra của `tests/test_p1_security_static.py` nếu test đó
     quét static, để không báo sai trên file vendor.
2. `feat(ui): add design tokens and theme system`
   - `app/static/css/tokens.css`: biến CSS cho màu (nền, bề mặt, viền, chữ, accent, trạng
     thái), cỡ chữ, khoảng cách, bo góc, đổ bóng, thời lượng chuyển động. Hai bộ giá trị
     light và dark qua `[data-theme]` trên `<html>`, map sang biến `--bs-*` của Bootstrap để
     component Bootstrap ăn theo.
   - Dark mode: mặc định theo `prefers-color-scheme`, lưu lựa chọn vào `localStorage`, áp
     dụng trước khi vẽ (script inline ngắn trong `<head>`) để không nháy màu.
   - Tôn trọng `prefers-reduced-motion`: tắt animation không thiết yếu.
3. `feat(ui): replace navbar with sidebar app shell`
   - `base.html`: sidebar trái cố định (logo, 5 mục điều hướng hiện có, chọn ngôn ngữ, nút
     theme, version), vùng nội dung cuộn độc lập. Thu gọn thành icon khi cửa sổ hẹp (Electron
     `minWidth` 960). Bỏ banner ảnh và footer liên hệ; chuyển liên hệ và Report Bug sang trang
     About hoặc cuối sidebar.
   - Giữ nguyên tên endpoint `main.*`, biến `active_page`, `?lang=` và `app_version`.
4. `feat(ui): restyle pages on the design system`
   - Sáu template: `index.html`, `form_filling.html`, `form_copy.html`,
     `settings_diagnostics.html`, `about.html`, `base.html`.
   - Trang Form Filling: stepper ngang phía trên thay cho danh sách bước bên trái; chuyển
     bước có transition; thẻ câu hỏi dạng card gọn; trạng thái rỗng, đang tải (skeleton thay
     spinner toàn màn hình), và lỗi đều có thiết kế riêng.
   - Trang Home: lưới thẻ form với tìm kiếm, trạng thái rỗng có lời mời hành động.
   - Toast dùng chung cho thông báo (thay `alert()` nếu còn; grep trước).
   - **Giữ nguyên mọi `id`, `name` và hàm toàn cục mà JS và test đang dùng** (ví dụ
     `sidebar-step-N`, `badge-step-N`, `step-N`, `extract-form`, `form-url-input`,
     `step-2-questions`, `settings-*`, `start-button`, `stop-button`, `submission-progress`,
     `success-rate`, `completed-count`, `total-count`, `elapsed-time`, `statusToast`,
     `toast-message`, `startProductTour`). Trước khi sửa: `grep -rn "getElementById\|querySelector" app/static/js`
     và đọc `tests/test_form_copy_ui.py`, `tests/test_frontend_popup_global.py`,
     `tests/test_i18n_render.py`, `tests/test_p1_security_static.py` để lập danh sách.
   - Product tour (driver.js) phải còn chạy: cập nhật selector nếu phần tử đổi chỗ.

## Hướng thẩm mỹ

Công cụ desktop tập trung, không phải landing page: mật độ thông tin vừa phải, một màu accent,
bề mặt phẳng với viền mảnh, chữ hệ thống (không tải webfont ngoài), chuyển động ngắn
(150–200 ms) chỉ ở chuyển bước, mở panel và cập nhật số liệu. Tương phản chữ đạt WCAG AA ở cả
hai theme. Mọi phần tử tương tác có focus ring nhìn thấy được và dùng được bằng bàn phím.

## Cuối phase

- Gate: pytest, ruff, route snapshot (không đổi), test "không asset ngoài" mới.
- Tự kiểm bằng mắt: chạy `uv run python wsgi.py` với `GOOGLE_FORM_TOOL_NO_BROWSER=1` trên port
  cố định, mở từng trang bằng công cụ trình duyệt có sẵn ở cả hai theme, chụp ảnh, xem ảnh và
  sửa lỗi bố cục. Dừng tiến trình khi xong. Không có công cụ trình duyệt → ghi vào báo cáo là
  chưa kiểm bằng mắt.
- Packaging smoke: `/healthz` 200; thêm `GET /static/vendor/<một file>` trả 200 trên backend
  đóng gói (thư mục `app/static` đã nằm trong `datas` của `.spec`).
- Viết US-009 (giao diện offline, theme, điều hướng) vào `docs/product/user-stories.md` và
  dòng tương ứng trong `docs/TEST_MATRIX.md`.
- Push nhánh. Fast-forward `release/v2`, push, mở **draft PR** `release/v2` → `master` với
  bảng trạng thái phase.

## Rollback

`git revert` từng commit; không đổi dữ liệu.

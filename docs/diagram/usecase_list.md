# Google Form Automation Tool — Use Case List

> Tổng hợp use case hiện có và roadmap nâng cấp thành Electron desktop app + installer + landing page + Google Form Copy.

---

### 🟢 PHASE 1 — Current Core / Stabilize (P0) — 34 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| A1 | Nhập Google Form respondent URL | Extract |
| A2 | Validate Google Form URL | Extract |
| A3 | Extract form title và description | Extract |
| A4 | Extract multi-page form structure | Extract |
| A5 | Extract question types cơ bản | Extract |
| A6 | Cache extracted form theo deterministic ID | Extract |
| A7 | Preview extracted form JSON/UI | Extract |
| B1 | Cấu hình xác suất chọn đáp án multiple choice/dropdown | Configure |
| B2 | Cấu hình xác suất checkbox độc lập | Configure |
| B3 | Cấu hình câu trả lời text/email/date/time tùy chỉnh | Configure |
| B4 | Generate random responses | Configure |
| B5 | Upload CSV/JSON/XLSX làm data-driven responses | Configure |
| B6 | Map uploaded columns vào question IDs | Configure |
| B7 | Save manual answer configuration | Configure |
| B8 | Configure branch submit behavior cho option | Configure |
| C1 | Start bulk submission | Submit |
| C2 | Chọn số lượng submissions | Submit |
| C3 | Chọn concurrent threads | Submit |
| C4 | Chọn min/max random delay | Submit |
| C5 | Submit bằng prefill link mode | Submit |
| C6 | Submit bằng DOM fill mode | Submit |
| C7 | Stop active submission gracefully | Submit |
| C8 | Poll submission status realtime | Submit |
| C9 | Hiển thị success/fail/success rate | Submit |
| C10 | Cảnh báo high failure rate | Submit |
| D1 | Xem CPU/network/thread metrics realtime | Monitoring |
| D2 | Xem monitoring history | Monitoring |
| E1 | Lưu submission history vào TinyDB | History |
| E2 | Xem submission history theo form | History |
| E3 | Export history CSV | History |
| E4 | Export history JSON | History |
| E5 | Search recent forms | History |
| E6 | Delete stored form | History |
| F1 | Switch language EN/VI | UX |

### 🟡 PHASE 2 — Desktop App + Installer (P1) — 22 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| G1 | Launch app như Electron desktop window | Desktop |
| G2 | Electron tự start local Flask backend | Desktop |
| G3 | Electron chờ backend health check trước khi load UI | Desktop |
| G4 | Electron tắt backend khi app quit | Desktop |
| G5 | App không auto-open browser ngoài khi chạy trong Electron | Desktop |
| G6 | Hiển thị loading/error screen khi backend startup fail | Desktop |
| G7 | Open external links bằng default browser | Desktop |
| G8 | App dùng icon/title/window size như desktop app thật | Desktop |
| H1 | Resolve Chrome binary tự động | Runtime |
| H2 | Resolve ChromeDriver tự động | Runtime |
| H3 | Download/cache ChromeDriver vào writable app data | Runtime |
| H4 | Optional bundle Chromium/driver để cài offline | Runtime |
| H5 | Hiển thị diagnostics Chrome/driver/app data path | Runtime |
| H6 | User không cần cài Python global | Runtime |
| I1 | Build Python backend sidecar bằng PyInstaller | Packaging |
| I2 | Bundle backend sidecar vào Electron app | Packaging |
| I3 | Build Windows NSIS `.exe` installer | Packaging |
| I4 | Build/evaluate Windows `.msi` installer | Packaging |
| I5 | Install app từ Start Menu/Desktop shortcut | Packaging |
| I6 | Uninstall app an toàn, không phá user data mặc định | Packaging |
| I7 | Release artifact lên GitHub Releases | Packaging |
| I8 | Version metadata đồng bộ giữa app/build/README | Packaging |

### 🟠 PHASE 3 — Google Form Copy MVP (P1) — 24 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| J1 | Mở trang Copy Form trong app | Copy |
| J2 | Nhập source Google Form respondent URL | Copy |
| J3 | Extract source form để copy | Copy |
| J4 | Preview source form structure | Copy |
| J5 | Tạo copy plan từ extracted form | Copy |
| J6 | Hiển thị capability matrix supported/partial/unsupported | Copy |
| J7 | Hiển thị warnings cho unsupported features | Copy |
| J8 | Nhập target Google Form editable public link | Copy |
| J9 | Validate target edit link format/accessibility | Copy |
| J10 | User xác nhận sở hữu/kiểm soát target form | Copy Safety |
| J11 | Apply copy plan vào target form bằng Selenium editor automation | Copy |
| J12 | Set target form title/description | Copy |
| J13 | Copy short answer questions | Copy |
| J14 | Copy paragraph questions | Copy |
| J15 | Copy multiple choice questions/options | Copy |
| J16 | Copy checkbox questions/options | Copy |
| J17 | Copy dropdown questions/options | Copy |
| J18 | Copy linear scale ở mức partial | Copy |
| J19 | Copy date/time ở mức partial | Copy |
| J20 | Report native grid/file upload/rating/quiz/theme/branching là unsupported nếu chưa hỗ trợ | Copy |
| J21 | Show per-question copy result | Copy Result |
| J22 | Show final copy report success/partial/failure | Copy Result |
| J23 | Persist copy job/report nếu cần xem lại | Copy Result |
| J24 | Không claim exact clone khi no-login/public-link only | Copy Safety |

### 🔵 PHASE 4 — Landing Page + Release UX (P2) — 13 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| K1 | User truy cập landing page Vercel | Landing |
| K2 | Xem hero/product positioning | Landing |
| K3 | Xem feature list | Landing |
| K4 | Xem install steps | Landing |
| K5 | Xem limitations/safety note | Landing |
| K6 | Tải Windows `.exe` installer | Landing |
| K7 | Tải Windows `.msi` nếu có | Landing |
| K8 | Xem release version/latest changelog | Landing |
| K9 | Landing link tới GitHub Releases/latest | Landing |
| K10 | Landing responsive mobile/desktop | Landing |
| K11 | README link tới landing/download page | Landing |
| K12 | Release checklist trước khi publish | Release |
| K13 | Document SmartScreen/code signing caveat | Release |

### 🟣 PHASE 5 — Advanced Coverage / Future (P2/P3) — 19 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| L1 | Extract required flag chính xác hơn | Advanced Extract |
| L2 | Extract question description/help text | Advanced Extract |
| L3 | Preserve native multiple choice grid | Advanced Extract |
| L4 | Preserve native checkbox grid | Advanced Extract |
| L5 | Detect Other option | Advanced Extract |
| L6 | Extract validation rules | Advanced Extract |
| L7 | Extract branching/page navigation metadata | Advanced Extract |
| L8 | Support file upload questions rõ ràng hơn | Advanced Extract |
| L9 | Support rating questions rõ ràng hơn | Advanced Extract |
| M1 | Copy native grids chính xác | Advanced Copy |
| M2 | Copy required flag | Advanced Copy |
| M3 | Copy question descriptions | Advanced Copy |
| M4 | Copy validation rules nếu feasible | Advanced Copy |
| M5 | Copy branching nếu feasible | Advanced Copy |
| M6 | Diff target form trước khi apply | Advanced Copy |
| M7 | Dry-run mode cho copy | Advanced Copy |
| M8 | Rollback/restore target form nếu copy fail | Advanced Copy |
| N1 | Auto-update desktop app | Desktop Future |
| N2 | Code-sign installer để giảm SmartScreen warning | Desktop Future |

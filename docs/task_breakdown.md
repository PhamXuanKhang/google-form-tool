# Google Form Automation Tool — Master Task Breakdown

> Tổng hợp từ roadmap nâng cấp app hiện tại thành Electron desktop app + Windows installer + Vercel landing page + Google Form Copy MVP.
> Cập nhật dựa trên current Flask/Selenium architecture, review findings, và `docs/diagram/usecase_list.md`.

---

## 📌 Quy ước đọc tài liệu

| Ký hiệu | Ý nghĩa |
|---------|--------|
| 🟥 P0 | Must-have — blocking nếu thiếu |
| 🟧 P1 | Should-have — cần cho UX hoàn chỉnh |
| 🟦 P2 | Nice-to-have — Phase sau |
| `[UC: Xx]` | Use case ID tương ứng trong `docs/diagram/usecase_list.md` |
| `→` | Output chuyển thành input của task tiếp theo |

**Vai trò triển khai đề xuất:**
- **Backend/Core** — Flask routes, Selenium core, TinyDB, models, tests.
- **Desktop/Packaging** — Electron shell, PyInstaller sidecar, electron-builder, installer scripts.
- **Frontend/UX** — Jinja templates, vanilla JS modules, CSS, landing page.
- **QA/Release** — automated tests, manual Windows smoke, GitHub Release, docs.

---

## ═══════════════════════════════════════
## PHASE 1 — Desktop Shell Foundation
### Mục tiêu: App hiện tại chạy được trong Electron window, không mở browser ngoài
---

### Task 1-A — Electron shell bootstrap
**Người phụ trách:** Desktop/Packaging
**Use cases:** G1, G2, G3, G4, G5

#### Subtasks

**[1-A.1] Tạo root Electron project** 🟥 P0
- **Input:** Flask app hiện tại (`wsgi.py`, `app/main_routes.py`, templates/static).
- **Output:** `package.json`, `electron/main.js`, `electron/preload.js` tối thiểu; `npm run electron:dev` khởi động Electron được.
- **Ghi chú:** Không rewrite UI sang React ở phase này; Electron chỉ wrap Flask UI.

**[1-A.2] Backend process supervisor** 🟥 P0
- **Input:** `wsgi.py` có thể nhận env `PORT`.
- **Output:** `electron/backendProcess.js` spawn Python backend, set `GOOGLE_FORM_TOOL_NO_BROWSER=1`, set port, kill backend khi Electron quit.
- **Ghi chú:** Dev mode có thể spawn `python wsgi.py`; packaged mode spawn PyInstaller sidecar.

**[1-A.3] Backend readiness health check** 🟥 P0
- **Input:** Flask route mới `/healthz`.
- **Output:** Electron poll `/healthz`, chỉ load app khi ready; timeout thì show error screen.
- **Ghi chú:** Health endpoint trả JSON nhẹ, không gọi Selenium/TinyDB nặng.

**[1-A.4] Disable external browser auto-open under Electron** 🟥 P0
- **Input:** Current `wsgi.py` auto-open browser khi frozen.
- **Output:** Nếu `GOOGLE_FORM_TOOL_NO_BROWSER=1`, backend không gọi `webbrowser.open()`.
- **Ghi chú:** Tránh UX bị mở cả Electron lẫn browser mặc định.

**[1-A.5] Native app window polish cơ bản** 🟧 P1
- **Input:** `app/static/images/app_icon.ico`.
- **Output:** BrowserWindow title/icon/size hợp lý; external links mở default browser.
- **Ghi chú:** Reuse existing icon.

**Verify**
- `npm run electron:dev`
- Đóng Electron → backend process tắt.
- `pytest tests/ -v`

---

### Task 1-B — Desktop runtime config
**Người phụ trách:** Backend/Core + Desktop/Packaging
**Use cases:** H3, H5, H6

#### Subtasks

**[1-B.1] Chuẩn hóa app-data paths** 🟥 P0
- **Input:** `config.py` hiện dùng `%APPDATA%\GoogleFormTool`.
- **Output:** DB, secret key, logs, downloaded drivers đều dùng writable app-data path.
- **Ghi chú:** Không ghi runtime data vào install directory.

**[1-B.2] Add diagnostics endpoint** 🟧 P1
- **Input:** Driver manager + config paths.
- **Output:** `/diagnostics/runtime` trả app data path, DB path, Chrome path, driver path, mode dev/frozen/electron.
- **Ghi chú:** UI dùng endpoint này cho troubleshooting.

**[1-B.3] Error messages actionable hơn** 🟧 P1
- **Input:** Existing extraction driver startup errors.
- **Output:** User thấy hướng dẫn kiểm tra Chrome/driver thay vì raw stack trace.
- **Ghi chú:** Reuse existing error handling trong `/form_filling/extract`.

**Verify**
- Unit test config path với temp env nếu feasible.
- Smoke diagnostics endpoint trong browser/Electron.

---

## ═══════════════════════════════════════
## PHASE 2 — Driver Strategy + Windows Installer
### Mục tiêu: User tải installer, cài app, không cần Python/ChromeDriver thủ công
---

### Task 2-A — Chrome/ChromeDriver resolution desktop-safe
**Người phụ trách:** Backend/Core
**Use cases:** H1, H2, H3, H4, H5

#### Subtasks

**[2-A.1] Move managed ChromeDriver cache vào app data** 🟥 P0
- **Input:** `app/core/driver_manager.py` hiện có logic `drivers/chromedriver` cạnh exe.
- **Output:** webdriver-manager/Selenium Manager cache hoặc copied driver nằm trong `%APPDATA%\GoogleFormTool\drivers`.
- **Ghi chú:** Cài vào `Program Files` thường không writable.

**[2-A.2] Driver resolution order rõ ràng** 🟥 P0
- **Input:** Env vars `CHROME_BINARY_PATH`, `CHROME_DRIVER_PATH`.
- **Output:** Order: env → bundled resources → app-data managed → installed Chrome common paths → Selenium fallback.
- **Ghi chú:** Log resolved path, không log secrets.

**[2-A.3] Optional bundled Chromium/driver mode** 🟧 P1
- **Input:** Packaging artifact hoặc `drivers/chrome` directory.
- **Output:** App có thể chạy trên máy chưa cài Chrome nếu bundle được Chromium.
- **Ghi chú:** Tradeoff là installer size tăng mạnh.

**[2-A.4] Runtime diagnostics UI** 🟧 P1
- **Input:** `/diagnostics/runtime`.
- **Output:** About/Settings hiển thị Chrome found, driver found, app data path.
- **Ghi chú:** Giúp support user non-technical.

**Verify**
- `pytest tests/test_extract_route.py -v`
- Manual extract trên máy không có `.env`.
- Windows VM smoke nếu bundle Chromium.

---

### Task 2-B — PyInstaller sidecar packaging
**Người phụ trách:** Desktop/Packaging
**Use cases:** I1, I2, H6

#### Subtasks

**[2-B.1] Reuse và cập nhật PyInstaller spec** 🟥 P0
- **Input:** `google_form_tool.spec`, `build_exe.bat`.
- **Output:** Backend executable build ổn định, bundle templates/static/translations/Selenium dependencies.
- **Ghi chú:** Có thể giữ console trong debug build, tắt console cho release.

**[2-B.2] Build script cho backend artifact** 🟥 P0
- **Input:** Existing `build_exe.bat`.
- **Output:** Script tạo artifact mà Electron packaging có thể consume.
- **Ghi chú:** Output path cố định để `electron-builder` include.

**[2-B.3] Packaged backend launch contract** 🟥 P0
- **Input:** `electron/backendProcess.js`, backend sidecar path.
- **Output:** Electron launch đúng backend trong packaged app.
- **Ghi chú:** Dev mode và packaged mode tách rõ.

**Verify**
- Chạy build PyInstaller.
- Electron dev/package launch đúng backend artifact.

---

### Task 2-C — Electron-builder Windows installers
**Người phụ trách:** Desktop/Packaging + QA/Release
**Use cases:** I3, I4, I5, I6, I7, I8

#### Subtasks

**[2-C.1] Add electron-builder config** 🟥 P0
- **Input:** Electron shell + backend artifact.
- **Output:** `electron-builder.yml` hoặc config trong `package.json`, NSIS `.exe` target.
- **Ghi chú:** Include icon, appId, productName, files/resources.

**[2-C.2] Windows package script** 🟥 P0
- **Input:** Backend build step + electron-builder.
- **Output:** `scripts/package-windows.ps1` chạy build end-to-end.
- **Ghi chú:** Script nên fail fast nếu backend artifact thiếu.

**[2-C.3] MSI evaluation** 🟧 P1
- **Input:** electron-builder MSI/WiX constraints.
- **Output:** Quyết định build `.msi` ngay hoặc defer; document lý do.
- **Ghi chú:** `.exe` NSIS đủ cho MVP download/install.

**[2-C.4] Version sync** 🟧 P1
- **Input:** Version đang lệch giữa README, `app/__init__.py`, build script.
- **Output:** Một nguồn version chính hoặc script sync.
- **Ghi chú:** Tránh landing/download ghi sai version.

**[2-C.5] Release checklist** 🟧 P1
- **Input:** Installer artifact.
- **Output:** Checklist test cài/gỡ, SmartScreen note, GitHub Release steps.
- **Ghi chú:** Code signing là future nếu chưa có cert.

**Verify**
- `scripts/package-windows.ps1`
- Install/uninstall trên Windows.
- Launch app từ Start Menu/Desktop shortcut.

---

## ═══════════════════════════════════════
## PHASE 3 — Google Form Copy MVP
### Mục tiêu: Copy form best-effort không đăng nhập, dùng source respondent URL + target public edit link
---

### Task 3-A — Copy planner models + capability matrix
**Người phụ trách:** Backend/Core
**Use cases:** J3, J4, J5, J6, J7, J20, J24

#### Subtasks

**[3-A.1] Add copy report models** 🟥 P0
- **Input:** Existing `Form`, `Page`, `Question`, `AnswerOption` trong `app/models.py`.
- **Output:** Pydantic models như `CopyOperation`, `CopyWarning`, `CopyPlan`, `CopyResult`.
- **Ghi chú:** Giữ models nhỏ, phục vụ planner/routes/UI.

**[3-A.2] Implement `form_copy_planner.py`** 🟥 P0
- **Input:** Extracted `Form`.
- **Output:** Pure function/class tạo copy plan, giữ order, map question types sang operations.
- **Ghi chú:** Không dùng Selenium trong planner để test nhanh.

**[3-A.3] Capability matrix** 🟥 P0
- **Input:** Current supported question types.
- **Output:** supported: short answer, paragraph, multiple choice, checkbox, dropdown; partial: linear scale/date/time; unsupported: grids/file upload/rating/quiz/theme/branching/validation.
- **Ghi chú:** UI dùng matrix để không claim exact clone.

**[3-A.4] Planner tests** 🟥 P0
- **Input:** Fixture `Form` objects.
- **Output:** `tests/test_form_copy_planner.py` cover supported/partial/unsupported warnings.
- **Ghi chú:** Đây là lớp ổn định nhất của copy feature.

**Verify**
- `pytest tests/test_form_copy_planner.py -v`

---

### Task 3-B — Copy Form backend routes
**Người phụ trách:** Backend/Core
**Use cases:** J1, J2, J3, J5, J8, J9, J21, J22

#### Subtasks

**[3-B.1] Render Copy Form page route** 🟥 P0
- **Input:** Flask blueprint `app/main_routes.py`.
- **Output:** `GET /form_copy` render `form_copy.html`.
- **Ghi chú:** Pass `active_page="form_copy"`.

**[3-B.2] Extract source endpoint** 🟥 P0
- **Input:** Source Google Form URL.
- **Output:** `POST /form_copy/extract_source` reuse `FormExtractor`, storage cache, return form summary.
- **Ghi chú:** Reuse error handling từ `/form_filling/extract`.

**[3-B.3] Preview plan endpoint** 🟥 P0
- **Input:** `form_id` hoặc source form payload.
- **Output:** `POST /form_copy/preview_plan` trả `CopyPlan` + warnings.
- **Ghi chú:** Không mutate target.

**[3-B.4] Apply endpoint skeleton** 🟥 P0
- **Input:** `form_id`, target edit link, ownership confirmation.
- **Output:** `POST /form_copy/apply_to_target` validate input và gọi copier.
- **Ghi chú:** Refuse nếu chưa confirm ownership.

**[3-B.5] Route tests** 🟥 P0
- **Input:** Mock extractor/planner/copier.
- **Output:** `tests/test_form_copy_routes.py` cover invalid URL, missing target, no confirmation, success, partial warnings.

**Verify**
- `pytest tests/test_form_copy_routes.py -v`
- `pytest tests/ -v`

---

### Task 3-C — Selenium target editor automation MVP
**Người phụ trách:** Backend/Core
**Use cases:** J9, J11, J12, J13, J14, J15, J16, J17, J18, J19, J21, J22

#### Subtasks

**[3-C.1] Implement `form_copier.py` skeleton** 🟥 P0
- **Input:** `CopyPlan`, target edit URL, driver paths.
- **Output:** Class mở target edit link, validate editable UI, return `CopyResult`.
- **Ghi chú:** Always close WebDriver in `finally`.

**[3-C.2] Title/description operations** 🟥 P0
- **Input:** Source form title/description.
- **Output:** Target title/description updated.
- **Ghi chú:** Selectors của Google Forms editor cần isolated helper methods.

**[3-C.3] Basic question create operations** 🟧 P1
- **Input:** Copy operations for short answer, paragraph, multiple choice, checkbox, dropdown.
- **Output:** Target questions/options created best-effort.
- **Ghi chú:** Nếu selector fail thì record warning, không crash toàn job nếu có thể.

**[3-C.4] Partial type handling** 🟧 P1
- **Input:** linear scale/date/time operations.
- **Output:** Copy partial hoặc warn rõ nếu chưa thao tác ổn định.
- **Ghi chú:** Không im lặng bỏ qua.

**[3-C.5] Mocked Selenium tests** 🟧 P1
- **Input:** Fake driver/elements.
- **Output:** `tests/test_form_copier.py` verify operation order and error handling.
- **Ghi chú:** Full integration với Google Forms là manual smoke do UI external brittle.

**Verify**
- `pytest tests/test_form_copier.py -v`
- Manual smoke với disposable public editable target form.

---

### Task 3-D — Copy Form UI
**Người phụ trách:** Frontend/UX
**Use cases:** J1, J2, J4, J6, J7, J8, J10, J21, J22, J24

#### Subtasks

**[3-D.1] Navbar và template** 🟥 P0
- **Input:** `app/templates/base.html`.
- **Output:** Navbar item “Copy Form”, `app/templates/form_copy.html`.
- **Ghi chú:** Reuse Bootstrap cards/wizard style hiện có.

**[3-D.2] Frontend JS flow** 🟥 P0
- **Input:** New copy endpoints.
- **Output:** `app/static/js/form_copy/main.js` handle extract → preview plan → target link → apply → report.
- **Ghi chú:** Keep vanilla JS pattern như `form_filling`.

**[3-D.3] Safety confirmation UX** 🟥 P0
- **Input:** Ownership confirmation requirement.
- **Output:** Apply button disabled until user confirms target is theirs/editable/disposable.
- **Ghi chú:** Copy operation can mutate target form.

**[3-D.4] Capability/warnings display** 🟧 P1
- **Input:** `CopyPlan.warnings`.
- **Output:** UI shows supported/partial/unsupported list before apply.
- **Ghi chú:** Avoid “copy y sì” wording in UI.

**[3-D.5] Render tests** 🟧 P1
- **Input:** Flask test client.
- **Output:** Update `tests/test_i18n_render.py` or new render test.

**Verify**
- Browser/Electron smoke: invalid URL, preview warnings, disabled apply, mocked success.

---

## ═══════════════════════════════════════
## PHASE 4 — Vercel Landing Page + Release Flow
### Mục tiêu: User có landing page để tải installer và hiểu cách cài/dùng
---

### Task 4-A — Landing page project
**Người phụ trách:** Frontend/UX
**Use cases:** K1, K2, K3, K4, K5, K10

#### Subtasks

**[4-A.1] Create `landing/` app** 🟧 P1
- **Input:** Product copy từ README, assets hiện có.
- **Output:** `landing/package.json`, page/layout, `vercel.json` nếu cần.
- **Ghi chú:** Landing tách riêng khỏi Flask app.

**[4-A.2] Landing content sections** 🟧 P1
- **Input:** Features hiện có và roadmap Copy Form/Desktop.
- **Output:** Hero, feature grid, install steps, limitations, screenshots/banner.
- **Ghi chú:** Nói rõ app chạy local desktop, không cần login.

**[4-A.3] Responsive polish** 🟦 P2
- **Input:** Landing page layout.
- **Output:** Mobile/desktop responsive.

**Verify**
- `cd landing && npm run dev`
- Vercel preview.

---

### Task 4-B — Download and release wiring
**Người phụ trách:** QA/Release + Desktop/Packaging
**Use cases:** K6, K7, K8, K9, K11, K12, K13, I7

#### Subtasks

**[4-B.1] GitHub Release artifact strategy** 🟧 P1
- **Input:** Installer output from Phase 2.
- **Output:** Stable latest download URL or release asset naming convention.
- **Ghi chú:** Landing should link to Releases, not store binary in repo.

**[4-B.2] Landing download buttons** 🟧 P1
- **Input:** Release URLs.
- **Output:** Download `.exe`; optional `.msi` if available.

**[4-B.3] README update** 🟧 P1
- **Input:** Landing URL and release flow.
- **Output:** README points users to landing/latest release with correct version.

**[4-B.4] Release workflow** 🟦 P2
- **Input:** Local packaging script.
- **Output:** `.github/workflows/release.yml` builds/uploads artifact or documented manual release.
- **Ghi chú:** Automate after local packaging is stable.

**Verify**
- Download link resolves.
- Release checklist completed on test release.

---

## ═══════════════════════════════════════
## PHASE 5 — Documentation + Verification Hardening
### Mục tiêu: Docs rõ ràng, test plan đủ để ship từng milestone
---

### Task 5-A — Documentation deliverables
**Người phụ trách:** QA/Release
**Use cases:** all

#### Subtasks

**[5-A.1] Maintain use case list** 🟥 P0
- **Input:** Current roadmap.
- **Output:** `docs/diagram/usecase_list.md` cập nhật khi scope thay đổi.

**[5-A.2] Maintain task breakdown** 🟥 P0
- **Input:** Implementation phases.
- **Output:** `docs/task_breakdown.md` cập nhật theo progress.

**[5-A.3] Add diagrams nếu cần** 🟦 P2
- **Input:** Use cases and flows.
- **Output:** Mermaid diagrams cho desktop startup, filling flow, copy flow, release flow.
- **Ghi chú:** Có thể thêm dưới `docs/diagram/`.

---

### Task 5-B — Test and smoke matrix
**Người phụ trách:** QA/Release + Backend/Core + Desktop/Packaging
**Use cases:** all critical flows

#### Subtasks

**[5-B.1] Python regression suite** 🟥 P0
- **Input:** Existing tests.
- **Output:** `pytest tests/ -v` green after every backend/core change.

**[5-B.2] Copy feature tests** 🟥 P0
- **Input:** New planner/routes/copier modules.
- **Output:** Targeted tests for `test_form_copy_planner.py`, `test_form_copy_routes.py`, `test_form_copier.py`.

**[5-B.3] Electron smoke checklist** 🟧 P1
- **Input:** Electron app.
- **Output:** Manual checklist: launch, health, close, external links, invalid URL flow.

**[5-B.4] Windows installer smoke checklist** 🟧 P1
- **Input:** Installer artifact.
- **Output:** Clean VM install, launch, extract, submit small batch, uninstall.

**[5-B.5] Copy manual smoke checklist** 🟧 P1
- **Input:** Disposable source/target Google Forms.
- **Output:** Copy report verified, target mutated as expected, unsupported types warned.

---

## 🔗 Dependency Map

```
1-A Electron shell ───────────────► 1-B runtime config
1-B runtime config ───────────────► 2-A driver strategy
2-A driver strategy ──────────────► 2-B PyInstaller sidecar
2-B sidecar ──────────────────────► 2-C installer
3-A copy planner ─────────────────► 3-B copy routes
3-B copy routes ──────────────────► 3-C Selenium copier
3-B copy routes ──────────────────► 3-D Copy UI
2-C installer ────────────────────► 4-B download/release wiring
4-A landing page ─────────────────► 4-B download/release wiring
All phases ───────────────────────► 5-B verification matrix
```

---

## 📎 Tài liệu tham chiếu

| Document | Dùng cho |
|---------|---------|
| `CLAUDE.md` | Project architecture, commands, rules |
| `docs/diagram/usecase_list.md` | Use case IDs và phase scope |
| `docs/task_breakdown.md` | Implementation tasks |
| `README.md` | Product copy, current install/build instructions |
| `build_exe.bat` | Existing PyInstaller build flow |
| `google_form_tool.spec` | Existing backend executable bundle config |
| `wsgi.py` | Flask/Waitress entrypoint |
| `app/core/driver_manager.py` | Chrome/ChromeDriver resolution |
| `app/core/form_extractor.py` | Source Google Form extraction |
| `app/core/form_submitter.py` | Existing submit automation |
| `app/models.py` | Pydantic data model |
| `app/main_routes.py` | Existing UI/API routes |
| `tests/` | Regression test patterns |

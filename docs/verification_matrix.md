# Verification Matrix

Task 5 keeps this file as the single QA matrix for P0/P1 verification. Mermaid flow diagrams are deferred because they are P2 scope.

## Automated regression matrix

Run the full suite after backend/core changes and before release candidates:

```powershell
pytest tests/ -v
```

| Area | Command | Expected result |
|------|---------|-----------------|
| Full regression | `pytest tests/ -v` | All tests pass; any deselected tests are expected and explained by pytest config. |
| Runtime config and diagnostics | `pytest tests/test_runtime_config.py tests/test_runtime_diagnostics_route.py tests/test_driver_manager.py tests/test_healthz.py -v` | App-data paths, diagnostics route, driver resolution, and health endpoint pass. |
| Extraction route safety | `pytest tests/test_extract_route.py -v` | Invalid URL and driver startup failures return actionable errors without raw tracebacks. |
| Copy planner/routes/copier/UI | `pytest tests/test_form_copy_planner.py tests/test_form_copy_routes.py tests/test_form_copier.py tests/test_form_copy_ui.py -v` | Planner capability matrix, routes, copier result handling, and Copy Form UI safety checks pass. |
| Form filling core | `pytest tests/test_form_processor.py tests/test_form_submitter.py tests/test_prefill_link_generator.py tests/test_prefill_submission.py -v` | Response generation, submitter behavior, prefill generation, and prefill submission tests pass. |
| Storage and history | `pytest tests/test_storage_service.py tests/test_submission_history_route.py tests/test_submission_persistence.py -v` | TinyDB storage, history route, and submission persistence tests pass. |
| Frontend/static safety | `pytest tests/test_js_prefill_validator.py tests/test_frontend_popup_global.py tests/test_i18n_render.py -v` | JS validator, global popup behavior, and translated page render checks pass. |
| Landing build | `npm --prefix landing run build` | Static landing build exits successfully. |
| Windows packaging script parse | `powershell -NoProfile -Command "$null = [scriptblock]::Create((Get-Content -Raw scripts/package-windows.ps1))"` | Packaging script parses without PowerShell syntax errors. |

## Electron smoke checklist

Use this checklist for Electron dev smoke. Record whether each item passed, failed, or was not run.

1. Open PowerShell in the project root.
   - Expected: current directory contains `package.json`, `electron/`, and `wsgi.py`.
2. Run `npm run electron:dev`.
   - Expected: Electron window opens and shows a loading state until the local backend is ready.
3. Confirm the Flask UI loads inside the Electron window.
   - Expected: the app home page renders inside Electron, not in the default external browser.
4. Open `http://localhost:5000/healthz` in a browser or call it with a local HTTP client.
   - Expected: response is successful and reports the backend is healthy.
5. Click an external link from the app if one is visible in the current UI.
   - Expected: external link opens in the default browser, not inside the Electron app shell.
6. Go to the form filling flow and submit an invalid non-Google-Form URL.
   - Expected: the UI shows an actionable validation error and does not start Selenium.
7. Close the Electron window.
   - Expected: the backend process exits shortly after Electron quits; no orphan backend process remains.

## Windows installer smoke checklist

Use a clean Windows user profile or VM when possible. Record artifact name, version, OS version, and Chrome/Chromium availability.

1. Build or download the NSIS `.exe` installer from the intended release artifact.
   - Expected: installer exists in `release/` locally or in GitHub Releases.
2. If MSI is included for the release, build or download the `.msi` artifact too.
   - Expected: MSI exists only when enabled for that release.
3. Confirm `SHA256SUMS.txt` includes every `.exe` and `.msi` artifact shipped.
   - Expected: checksum file names match the artifacts exactly.
4. Install the NSIS `.exe` on a clean Windows user profile.
   - Expected: installation finishes without requiring Python to be installed globally.
5. Launch from the Start Menu shortcut.
   - Expected: Electron app opens and local backend starts.
6. Launch from the Desktop shortcut if created.
   - Expected: Electron app opens consistently from the shortcut.
7. Confirm no external browser opens automatically during startup.
   - Expected: app UI stays in Electron unless the user clicks an external link.
8. Check backend health after startup.
   - Expected: `/healthz` returns healthy status.
9. Open Settings > Diagnostics.
   - Expected: runtime mode, app data path, DB path, log path, bundled driver path, cached driver path, Chrome path, and ChromeDriver path or fallback message are visible.
10. Extract a disposable public Google Form URL.
    - Expected: extraction succeeds if Chrome/ChromeDriver are available; if not, the error explains how to fix Chrome/driver setup.
11. Confirm runtime files are written under app data.
    - Expected: DB/log/driver cache are not written into the install directory.
12. Uninstall the app.
    - Expected: installed binaries and shortcuts are removed.
13. Check app-data user files after uninstall.
    - Expected: user data under app data is preserved by default unless the installer explicitly offers and the tester selects data removal.

## Copy Form manual smoke checklist

Copy Form is best-effort for public/no-login workflows. Do not describe the result as an exact clone. Live Google Forms editor mutation may currently report `partial` or `skipped` for operations that do not have a stable live mutation adapter.

1. Create or choose a disposable source Google Form respondent URL.
   - Expected: the source form is safe to inspect and contains no sensitive data.
2. Create or choose a disposable target Google Form editable link that the tester owns or controls.
   - Expected: the target can be modified without affecting real users.
3. Open the app and go to Copy Form.
   - Expected: Copy Form page renders with safety wording and ownership confirmation disabled by default.
4. Enter an invalid source URL and start extraction.
   - Expected: validation error appears and no copy plan is created.
5. Enter the disposable source respondent URL and extract it.
   - Expected: source summary appears; unsupported or partial capabilities are not hidden.
6. Preview the copy plan.
   - Expected: plan keeps title/description first, preserves question order, and shows supported/partial/unsupported warnings.
7. Enter an invalid target edit link.
   - Expected: apply is rejected with a target-link validation error.
8. Enter the disposable target edit link but leave ownership confirmation unchecked.
   - Expected: apply remains disabled or the backend rejects the request.
9. Check the ownership confirmation and apply the plan.
   - Expected: report shows per-operation success, warning, skipped, partial, or failure status. Current live editor mutation may be partial/skipped rather than fully applied.
10. Open the target form manually.
    - Expected: any mutations that were reported as succeeded are visible; unsupported or skipped operations are clearly explained in the copy report.
11. Verify the UI wording.
    - Expected: the app says best-effort copy and public-link/no-login limitations; it does not claim exact cloning.

## Release handoff

Before publishing a release candidate:

1. Run the full automated regression suite.
2. Run the landing build check.
3. Run the packaging script parse check at minimum; run the full Windows packaging script when the release environment is ready.
4. Execute Electron smoke on the build mode being shipped.
5. Execute Windows installer smoke on a clean profile or VM.
6. Execute Copy Form manual smoke with disposable forms if Copy Form is part of the release notes.
7. Keep the GitHub Release as draft until install smoke has passed on downloaded artifacts.

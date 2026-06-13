# Testing

## Automated Checks

Run the full test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Current expected result: `215 passed, 1 deselected`.

The JS prefill validator is covered through pytest by shelling out to Node.js. If Node.js is missing, `tests/test_js_prefill_validator.py` skips with a manual verification note.

## Manual Smoke Checks

- Start the backend with `scripts/run_local.ps1` or run the Electron shell with `npm run electron:dev`.
- Open the app, extract a public Google Form URL, and confirm the preview shows title, pages, questions, and supported types.
- Configure a small submission plan with 1 thread and a safe delay range.
- Run a tiny submission or prefill-only flow and confirm status updates, warnings, and history persistence.
- Open Settings > Diagnostics and confirm runtime paths, Chrome, ChromeDriver, and log locations are actionable.

## Release Smoke Checks

- Run `scripts/package-windows.ps1`.
- Confirm `dist/GoogleFormTool/GoogleFormTool.exe` exists before Electron packaging.
- Confirm installers are created under `release/` and `release/SHA256SUMS.txt` includes each artifact.
- Install on a clean Windows profile, launch from Start Menu and Desktop shortcut, and confirm `/healthz` returns ok.
- Uninstall and confirm app binaries are removed while user data under app data is preserved by default.

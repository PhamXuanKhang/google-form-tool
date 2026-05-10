# Windows Release Checklist

## Build artifacts
- [ ] Run `scripts/package-windows.ps1` from PowerShell.
- [ ] Confirm backend sidecar exists at `dist/GoogleFormTool/GoogleFormTool.exe`.
- [ ] Confirm NSIS `.exe` installer exists in `release/`.
- [ ] Confirm MSI installer exists in `release/`.
- [ ] Confirm artifact version matches `package.json`.

## Install smoke
- [ ] Install NSIS `.exe` on a clean Windows user profile.
- [ ] Install MSI on a clean Windows user profile.
- [ ] Launch from Start Menu shortcut.
- [ ] Launch from Desktop shortcut.
- [ ] Confirm Electron window loads without opening the external browser.
- [ ] Confirm local backend starts and `/healthz` returns ok.

## Runtime diagnostics
- [ ] Open Settings > Diagnostics.
- [ ] Confirm runtime mode is `electron` in packaged app.
- [ ] Confirm app data, DB, log, bundled drivers, and cached drivers paths are shown.
- [ ] Confirm Chrome and ChromeDriver paths are shown or Selenium fallback text is clear.
- [ ] Confirm bundled Chromium is not claimed as included.

## Core workflow smoke
- [ ] Extract a public Google Form URL.
- [ ] Confirm driver startup errors show actionable diagnostics if Chrome/ChromeDriver cannot start.
- [ ] Confirm runtime data is written under app data, not install directory.

## Uninstall smoke
- [ ] Uninstall NSIS install and confirm app binaries are removed.
- [ ] Uninstall MSI install and confirm app binaries are removed.
- [ ] Confirm uninstall does not delete user data under app data by default.

## Release notes
- [ ] Note that Windows SmartScreen may warn until the app is code signed or has reputation.
- [ ] Note that bundled Chromium is deferred; users need installed Chrome/Chromium or Selenium fallback support.
- [ ] Upload NSIS `.exe`, MSI, and checksums to GitHub Releases.
- [ ] Include version, date, major changes, known limitations, and install/uninstall instructions in the GitHub Release body.

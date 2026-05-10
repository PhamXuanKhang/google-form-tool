# Windows Release Checklist

## Build artifacts
- [ ] For local builds, run `uv sync` first so `.venv` exists.
- [ ] Run `scripts/package-windows.ps1` from PowerShell or trigger `.github/workflows/release.yml` manually.
- [ ] Confirm GitHub Actions installs uv and runs `uv sync` before packaging.
- [ ] Confirm backend sidecar exists at `dist/GoogleFormTool/GoogleFormTool.exe`.
- [ ] Confirm NSIS `.exe` installer exists in `release/`.
- [ ] Confirm MSI installer exists in `release/` if MSI is enabled for this release.
- [ ] Confirm `release/SHA256SUMS.txt` exists and includes every `.exe`/`.msi` artifact.
- [ ] Confirm artifact version matches `package.json`.

## Landing and download smoke
- [ ] Run `cd landing && npm run build`.
- [ ] Run `cd landing && npm run dev` and open the local preview.
- [ ] Confirm landing CTA links to `https://github.com/PhamXuanKhang/google-form-tool/releases/latest`.
- [ ] Confirm landing does not hardcode direct release asset URLs.
- [ ] Replace README placeholder `https://<your-vercel-app>.vercel.app` with the real Vercel URL before public release.
- [ ] Confirm README links to the landing page and GitHub Releases latest.

## Install smoke
- [ ] Install NSIS `.exe` on a clean Windows user profile.
- [ ] Install MSI on a clean Windows user profile if MSI is included.
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
- [ ] Uninstall MSI install and confirm app binaries are removed if MSI is included.
- [ ] Confirm uninstall does not delete user data under app data by default.

## GitHub Release
- [ ] Create or push a `v*` tag only after local smoke checks pass.
- [ ] Confirm GitHub Actions uploaded `.exe`, optional `.msi`, and `SHA256SUMS.txt`.
- [ ] Keep release as draft until install smoke is completed on downloaded artifacts.
- [ ] Include version, date, major changes, known limitations, and install/uninstall instructions in the GitHub Release body.
- [ ] Note that Windows SmartScreen may warn until the app is code signed or has reputation.
- [ ] Note that bundled Chromium is deferred; users need installed Chrome/Chromium, while ChromeDriver may be resolved automatically when available.
- [ ] Confirm the landing download CTA resolves to GitHub Releases latest after publishing.

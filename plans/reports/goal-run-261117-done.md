# Goal run — Release 2.0

Status: all seven feature groups are done, the version is 2.0.0, and PR #11 is open into
`master`. The one unmet signal is "CI green". GitHub Actions does not start any job on this
repository because the account is locked over billing, so the PR stays a draft. Only the
owner can clear that.

PR: https://github.com/PhamXuanKhang/google-form-tool/pull/11 (draft, title `feat: release 2.0`)

## Baseline (phase 0, 2026-11-16, `master` 85d14b6)

- pytest: `272 passed, 1 deselected`
- ruff: `All checks passed!`
- Node v26.3.0, uv 0.9.8; ports 5056 and 5123 free; no `GoogleFormTool.exe` running.

## Branches

| # | Phase | Branch | Status | Tests |
|---|-------|--------|--------|-------|
| 0 | Prepare | `release/v2` | done | 272 |
| 1 | UI foundation | `feat/v2-ui-foundation` | done | 284 |
| 2 | Run engine | `feat/v2-run-engine` | done | 325 |
| 3 | Simulation + report | `feat/v2-simulation-report` | done | 354 |
| 4 | MCP core + skill | `feat/v2-mcp-core` | done | 381 |
| 5 | Presets + templates | `feat/v2-presets-templates` | done | 456 |
| 6 | Personas + AI Autopilot | `feat/v2-personas-autopilot` | done | 503 |
| 7 | Scheduled runs | `feat/v2-drip-mode` | done | 527 |
| 8 | Release | `release/v2` | done except CI | 531 |

All branches are pushed. `release/v2` holds phase 7 plus the release commits.

## Final checks

- pytest: `531 passed, 1 deselected` on Python 3.12, and the same on an isolated Python 3.11
  environment (CI's version). The acceptance test files alone: `290 passed`.
- ruff: clean through both `uv run` and `uvx` (CI's form).
- Route snapshot: changed only by additions. Every new UI string has a Vietnamese translation,
  and the `.mo` files are current.
- Templates contain no external asset URL. No debug `console.log` or TODO was added.

## Smoke

- Free RAM stayed at 1.2 to 1.3 GB over two waits, under the 2 GB threshold. As in phases 1,
  2 and 4, only the PyInstaller backend bundle was built (`build_exe.bat release`). The
  Electron installer was not built.
- Before that build would run, two empty folders left from earlier builds
  (`build\google_form_tool\localpycs` and `dist\GoogleFormTool`) had to have their ReadOnly
  attribute cleared.
- Packaged backend on port 5056: `/healthz` returned 200 `{"status":"ok"}`, a
  `static/vendor` file returned 200, and `/diagnostics/runtime` reported version 2.0.0.
- `scripts/smoke-mcp.py --port 5056` against `GoogleFormToolMcp.exe`: 20 tools, every
  stdout line JSON-RPC 2.0, and `app_status` reported 2.0.0.
- The processes were stopped, and the build left no tracked change.

## Advice and review this session

- Kongming's phase 7 check was a no-go until one bug was fixed. A scheduled run whose batch
  recorded nothing (Chrome failing to start, for example) retried forever. That is fixed
  (230e325), along with a runner left marked "running" after a setup error. The go
  condition is met.
- The code review of `master...release/v2` found four correctness bugs, all fixed with tests:
  - A new scheduled run ignored its thread count per tick (cd44694).
  - Pausing a finished run returned success (cd44694).
  - Run headers were read without the database lock (d233b7b).
  - A failed persona save lost the overrides (6f425b1).

  A stray BOM in `wsgi.py` was also removed (da27991).
- A fake test key that matched a Google API key pattern was replaced (38f77a8). It remains in
  earlier commits.
- Kongming's whole-release verdict: **ready for the owner, not yet ready to merge or tag.**
  - It found no code defect that breaks a contract constraint.
  - It confirmed these hold: existing routes changed only by added keys, 1.x forms still load,
    the 500/10 limits apply on UI and MCP paths, the Gemini key never reaches server-side
    logs or responses, no test uses the network, and the code runs on Python 3.11.
  - Main risk, which I confirmed in the code: a row whose Submit was clicked but whose
    confirmation timed out is recorded as `failed`, so "retry failed" can send it twice
    (`app/adapters/browser/form_submitter.py:733-750`, `:384`). It is documented under Known
    Issues in the README rather than fixed, because the fix touches the real-browser path and
    needs a check on a real form.
  - Other points:
    - `/save_edit` now rejects values that `master` used to store. This is deliberate.
    - An inline `responses_list` on `/start_submission` skips the 500 cap, as it does on
      `master`. Neither the UI nor MCP can send one. Adding a guard would add a new 400 to an
      existing route, so that is the owner's call.
    - The MCP exe path inside an installed app is unverified.
    - Electron has no single-instance lock.
  - It was posted as a comment on PR #11.

## Not fixed (listed for the owner)

These came from the review. They do not break a contract signal.

- A second app instance runs startup recovery before failing on the busy port. It can mark the
  first instance's live scheduled runs interrupted, though nothing is sent twice.
- The drip runner writes the store before memory. If disk writes keep failing, a row can be
  resent.
- MCP `run_status` does not show `interrupted` after a restart; `list_runs` and `get_report`
  do.
- The Electron close-confirmation `fetch` has no timeout.
- A scheduled run starts a new Chrome for every tick.
- Prefill URLs are built twice when a run starts.
- Some code is duplicated: the percent-rounding helper and the `_questions` helper.
- The `MIN/MAX_WINDOW_SECONDS` constants are unused.
- `GET /forms` does one extra lookup per form (N+1).
- The MCP server reports the `mcp` library's version (1.30.0) as its own server version.
- 74 Vietnamese translations were already missing before this release (About page, Form
  Filling tour, Diagnostics labels).
- Dependency advisories predate this release: `npm audit` reports 7 high and 1 critical
  (npm dependencies unchanged since `master`), and `pip-audit` reports issues in packages
  pinned on `master`.

## What the owner must check before publishing

- Fix the GitHub billing lock and let CI run on PR #11. If gitleaks flags the old fake test
  key, add its fingerprint to `.gitleaksignore`.
- Decide what to do about the npm and pip advisories.
- Build the full installer on a machine with more free RAM, install it, and check that a
  scheduled run continues after the app is closed and opened again.
- Look at every page in light and dark mode, in English and Vietnamese.
- Run a real batch on your own form, in both submission modes. Force a failure, use "retry
  failed", and count the responses in Google to check for duplicates.
- Decide whether to make "clicked but unconfirmed" rows `unknown` instead of `failed`, and
  whether to cap inline `responses_list` (both suggested for 2.0.x).
- Try AI Autopilot with a real Gemini key.
- Add the MCP server to Claude and call each tool.
- Mark the PR ready, merge, tag `v2.0.0` and publish the release. The goal run did none of
  these.

## Unresolved questions

- Should the PR be marked ready before CI can run? This run left it a draft.

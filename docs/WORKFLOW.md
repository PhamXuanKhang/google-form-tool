# Workflow

How work gets classified, built, and proven in this repo. Product behavior lives in
`docs/product/user-stories.md`; proof status lives in `docs/TEST_MATRIX.md`.

## Before changing code

1. Read `README.md`, `docs/ARCHITECTURE.md`, and the user story the change touches.
2. Restate the request as one work item and pick a lane.

## Lanes

| Lane | Use for | What to do |
| --- | --- | --- |
| tiny | Docs, copy, names, narrow edits, initial setup that adds no domain behavior | Patch directly. Run the quick checks. |
| normal | Story-sized behavior with limited blast radius | Update the user story's acceptance criteria and `docs/TEST_MATRIX.md`. Implement the smallest slice. Add or update tests. |
| high-risk | Anything with a hard gate, or four or more risk flags | Write the plan first. Add a decision record. Ask for confirmation if the direction is ambiguous. |

Move from tiny/normal to high-risk when a hard gate applies.

## Risk checklist

Count one flag for each item the work touches:

- Auth: login, sessions, secrets.
- Authorization: roles, permissions.
- Data model: schema, deletion, retention, migration of stored data.
- Audit/security: privacy, sensitive data, access logs.
- External systems: Google Forms behavior, Gemini API, Chrome/ChromeDriver, updates.
- Public contracts: route shape, JSON keys, client-visible behavior.
- Cross-platform: Electron shell, packaged backend, installer.
- Existing behavior: already implemented or test-covered behavior changes.
- Weak proof: unclear or missing tests around the affected area.
- Multi-domain: more than one product area changes at once.

Zero or one flag: tiny or normal. Two or three: normal with stronger tests. Four or more: high-risk.

## Hard gates

These are always high-risk unless the owner explicitly narrows the scope:

- Auth or authorization changes.
- Data loss or stored-data migration.
- Audit or security behavior.
- External provider behavior.
- Removing or weakening a test or validation requirement.

## Where things go

- Stories and acceptance criteria: `docs/product/user-stories.md`.
- Proof status per story: `docs/TEST_MATRIX.md`.
- Decisions that change architecture, scope, contracts, or validation: `docs/decisions/NNNN-title.md`, from `docs/templates/decision.md`.
- Story detail for high-risk work: copy `docs/templates/story.md` next to the plan.
- Plans and reports: `plans/` and `plans/reports/`.

## Checks

Run from the repository root:

```powershell
uv run python -m pytest -q
uv run ruff check app/ tests/ wsgi.py
```

`uv run python -m pytest -q -m domain` runs only the fast domain tests.
`tests/test_route_snapshot.py` pins every route; it must stay green when routes move.

## Packaging smoke

Run this after changes that touch packaged modules (`google_form_tool.spec`, dependencies, imports):

1. Make sure no `GoogleFormTool.exe` process is running and port 5056 is free.
2. Set `$env:CI='true'` and run `.\scripts\package-windows.ps1`. Without `CI=true`, `build_exe.bat` stops at a `pause`.
3. Start `dist\GoogleFormTool\GoogleFormTool.exe` with `PORT=5056` and `GOOGLE_FORM_TOOL_NO_BROWSER=1`.
4. `GET /healthz` must return 200 with `{"status":"ok"}`. Then stop the process.
5. Revert build side effects in `git status` (for example `package-lock.json`) and do not commit `build/`, `dist/`, or `release/`.

With `CI=true`, electron-builder tries to publish and fails without `GH_TOKEN` after the
installers are built. The backend check in step 4 is the gate.

## Commits

Use conventional commits. Keep each logical change in its own commit.
Do not put plan or phase numbers in code comments, test names, or commit messages.

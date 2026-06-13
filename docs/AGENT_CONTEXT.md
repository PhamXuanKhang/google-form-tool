# Agent Context

Use this file as the short operational map before making changes.

## Success Criteria

- Keep runtime code minimal and focused on the desktop/local app use case.
- Preserve the extract → configure → submit → monitor workflow.
- Prefer deleting ignored artifacts over archiving them in the repo.
- Run GitNexus impact analysis before editing functions, classes, or route handlers.
- Run `mcp__gitnexus.detect_changes` before committing.

## Validate

```powershell
.\.venv\Scripts\python.exe -m pytest
npx gitnexus analyze
```

Tests may need unsandboxed permission because logging writes under the app data directory.

## Keep

- `README.md` for user/developer onboarding.
- `AGENTS.md` for agent instructions and GitNexus requirements.
- `docs/ARCHITECTURE.md` for runtime map.
- `docs/TESTING.md` for validation and release smoke checks.
- `docs/AGENT_CONTEXT.md` for concise agent handoff.

## Avoid Reintroducing

- Generated repo dumps such as `repomix-output.xml`.
- One-off review reports such as `report.html`.
- Large beta planning packs or obsolete scratch plans.
- Unreferenced sample JSON in the repository root.

---
title: Phase 1 Test Isolation
date: 2026-08-15
summary: "Isolated pytest from user data, added storage seam, migrated 31 test patches to fixture"
---

# Phase 1 Test Isolation

## What happened

Completed Phase 1 of the 4-phase repo restructure plan — test isolation from user data.

**Problem:** `pytest` was writing to `%APPDATA%\GoogleFormTool` (db.json, app.log) and required elevation. Tests patched `app.main_routes.get_storage_service` by module name (36 places), which would break when Phase 3 splits routes.

**Solution:**
1. **Env isolation** — `tests/conftest.py` sets `LOG_DIR`, `DB_PATH`, `SECRET_KEY` before any app import
2. **Storage seam** — `app/services.set_storage_provider()` allows test injection without module-name coupling
3. **Fixture migration** — Replaced 31 monkeypatch calls with `storage_stub()` fixture across 11 test files

## Outcome

- 215 passed, 1 deselected (unchanged baseline)
- `db.json` and `app.log` mtime unchanged after test run
- 0 remaining `main_routes, "get_storage_service"` patches
- Coupling map documents 23 remaining `main_routes.*` references for Phase 3

## Commits

- `55442c4` — env isolation + storage seam
- `d8fd33d` — fixture migration (12 files, +99/-118)

## Next steps

Phase 3 of master plan (route split) can proceed. Coupling map in `phase-04-verification-and-coupling-map.md` identifies which test files need updates when `active_submitters`, `_run_submission`, `_upload_cache` move to `app/services/submission_manager.py`.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.

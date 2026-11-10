---
title: "Phase 2: Storage Provider Seam"
date: 2026-08-15
summary: Added overridable storage provider seam in app/services/__init__.py so tests can inject fake storage without patching app.main_routes by name
---

# Phase 2: Storage Provider Seam

## What happened

Implemented Phase 2 of the Phase 1 Test Isolation plan
(`plans/260815-1127-phase-1-test-isolation/phase-02-storage-provider-seam.md`).

`app/services/__init__.py` gained a module-global `_storage_provider`, a
`set_storage_provider(provider)` setter, and `get_storage_service()` now checks
the provider first before falling back to the original
`Config.DB_PATH` + `StorageService(db_path)` path. Change is purely additive
(13 lines), default behavior byte-identical to before.

Rationale documented in the plan (DD-2): `app/main_routes.py` binds
`get_storage_service` at import time, and one call site
(`_run_submission`, spawned as a daemon thread) runs with no Flask app
context, so a `current_app`/app-extension-based seam would break there. A
module-global provider works in threads and doesn't couple to the
`app.main_routes` module name, so it survives the later route-module split
planned in Phase 3 of the parent restructure.

## Decision

Implemented exactly the plan's prescribed snippet, no deviation. Deferred
`ruff check` locally — this `.venv` has no `pip` installed, so `ruff` can't be
installed here; deferred to CI per the plan's own documented fallback, and
recorded that explicitly in the phase file's success criteria instead of
silently marking it PASS.

Committed Phase 1 (`tests/conftest.py`, pre-existing uncommitted env-bootstrap
work) together with Phase 2 in one commit (`55442c4`), since Phase 1 had never
been committed separately.

## Verification

- Full suite: `pytest -q` → 215 passed, 1 deselected (matches baseline).
- Manual probe: installed a stub provider, called `get_storage_service()`
  inside a thread with no Flask app context, confirmed it returned the stub.
- Confirmed all 15 `with get_storage_service() as storage:` call sites in
  `app/main_routes.py` unmodified.
- `code-reviewer` subagent pass: PASS, no blocking issues. Noted two
  non-blocking items for Phase 3: the "test-only" warning lives in a module
  comment rather than the setter's docstring, and existing
  `monkeypatch.setattr(main_routes, "get_storage_service", ...)` call sites
  still silently outrank an installed provider until migrated.

## Next steps

Phase 3 (`phase-03-migrate-test-stubs.md`) migrates the 36
`monkeypatch.setattr(main_routes, "get_storage_service", ...)` call sites
across 11 test files to the new `storage_stub` fixture, and adds an autouse
fixture to reset the provider after every test.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.

---
title: "Phase 2 Root Cleanup & Deps"
date: 2026-08-15
summary: "Migrated deps to pyproject.toml + uv, removed Docker, consolidated configs"
---

# Phase 2 Root Cleanup & Deps

## What happened

Executed Phase 2 of the 4-phase repo restructure plan. Migrated dependency management from requirements.txt to pyproject.toml + uv.lock:

- Created pyproject.toml with dynamic version from app/__init__.py (hatchling)
- Generated uv.lock (86 packages)
- Migrated CI workflows (ci.yml, release.yml) to astral-sh/setup-uv
- Simplified build_exe.bat to uv sync only
- Removed Docker files (Dockerfile, docker-compose.yml, .dockerignore)
- Removed obsolete configs (requirements.txt, pytest.ini, ruff.toml)
- Consolidated pytest/ruff config into pyproject.toml [tool.*] sections
- Simplified CLAUDE.md to thin loader pointing to AGENTS.md
- Updated README onboarding to uv-first

## Verification

- uv sync from clean env: SUCCESS
- Tests: 215 passed, 1 deselected (baseline maintained)
- Ruff lint: All checks passed
- pip-audit via uv export: runs successfully
- Dynamic version: 1.1.0

## Files changed

- New: pyproject.toml, uv.lock
- Modified: .github/workflows/ci.yml, release.yml, build_exe.bat, README.md, CLAUDE.md, app/main_routes.py, app/static/js/form_filling/main.js
- Deleted: Dockerfile, docker-compose.yml, .dockerignore, requirements.txt, pytest.ini, ruff.toml, tests/test_resource.md

## Decision

No new architectural decisions. Followed plan DD-1 through DD-4 as specified.

## Next steps

- Proceed to Phase 3 of master restructure plan (route splitting) when ready
- Monitor CI on review branch for any edge cases

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.

# 0002 Split main routes into route modules and services

Date: 2026-11-10

## Status

Accepted

## Context

`app/main_routes.py` held every route, the upload cache, the submission registry,
the background submission worker, and CSV/JSON export building in about 1,100
lines. That broke the boundary in `docs/ARCHITECTURE.md` that route handlers only
validate input and delegate. Templates and JS use `url_for('main.*')` endpoint
names, and the packaged backend only imports modules listed in
`google_form_tool.spec`.

## Decision

- Routes live in `app/routes/` as seven modules: `health`, `pages`, `forms`,
  `data`, `ai`, `submissions`, `history`. No module exceeds 250 lines.
- All modules share one blueprint created in `app/routes/__init__.py`, so
  endpoint names stay `main.*` and templates are unchanged.
- Process-wide state and logic move to `app/services/`: `upload_cache`,
  `submission_manager` (active submitters and the worker), and `history_export`.
- Route modules read mutable service state through the module
  (`submission_manager.active_submitters`) so tests can replace it.
- `google_form_tool.spec` hiddenimports list every new module.
- `tests/test_route_snapshot.py` pins rule, methods, endpoint, status, and JSON
  keys for the 22 routes and must stay green across route moves.

## Alternatives Considered

1. One blueprint per module. Rejected: endpoint names would change to
   `pages.index` and similar, breaking every `url_for('main.*')`.
2. Feature folders (`app/features/*`). Rejected: form copy, submit, and AI share
   the Form/Question models, Selenium extraction, and storage.

## Consequences

Positive:

- Handlers are short and each module has one concern.
- Submission state has a single owner that tests and routes both import.

Tradeoffs:

- Every new module must be added to the `.spec` hiddenimports, or only the
  installer breaks while tests stay green.

## Follow-Up

- `/about` raises today because `about.html` passes a literal `%` through
  gettext. The snapshot pins this as a strict xfail; fix the template separately.

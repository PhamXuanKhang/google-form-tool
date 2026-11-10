# Architecture

This project is a local desktop app for extracting, configuring, and submitting Google Forms in bulk. The packaged product runs an Electron shell and a local Flask backend; source development can run the Flask backend directly.

## Runtime Entry Points

- `wsgi.py` starts the Flask backend with Waitress outside debug mode.
- `app/__init__.py` creates the Flask app, registers routes, and initializes logging.
- `electron/main.js` owns the desktop window lifecycle.
- `electron/backendProcess.js` starts and stops the packaged backend sidecar.

## Main Flows

- Extract: `app/routes/forms.py` receives a Google Form URL and delegates browser extraction to `app/adapters/browser/form_extractor.py`.
- Configure: templates and JS under `app/templates/` and `app/static/js/form_filling/` render question configs and validate client-side input.
- Submit: `app/routes/submissions.py` validates requests and starts `app/services/submission_manager.py`, which tracks active submitters and runs `app/adapters/browser/form_submitter.py` workers for direct or prefilled URL submission.
- Prefill: `app/domain/prefill_link_generator.py` builds Google Forms prefill URLs from configured answers.
- Storage: `app/services/storage_service.py` persists forms and submission history for the local user.
- Diagnostics: the `/healthz` and diagnostics routes expose runtime health for desktop support.
- Landing: `landing/` is a separate static site deployed on its own (for example to Vercel). It is not part of the packaged app; its release link points to GitHub Releases latest.

## Boundaries

- UI code should call Flask routes, not storage or Selenium directly.
- Route handlers live in `app/routes/` (one shared `main` blueprint), validate input, and delegate business logic to `app/domain/`, `app/adapters/`, or `app/services/`. See `docs/decisions/0002-route-split.md`.
- `app/domain/` holds form processing, prefill link generation, and form copy planning, and does not import Selenium or adapters. Browser automation lives in `app/adapters/browser/` and the Gemini client in `app/adapters/ai/`. Runtime configuration is `app/config.py`.
- Selenium lifecycle belongs in extractor/submitter/copy modules; each path must clean up drivers.
- Generated artifacts, local reports, and AI planning scratch files should stay ignored and out of the repo.

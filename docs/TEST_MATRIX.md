# Test Matrix

This file maps product behavior to proof for Google Form Automation Tool.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Extract form | Parse Google Form structure into local form model | yes | yes | manual | desktop/browser | implemented | `tests/test_form_extractor.py`, `tests/test_extract_route.py` |
| Configure answers | Validate answer probability/configuration in UI and backend | yes | yes | manual | browser | implemented | `tests/test_form_processor.py`, `tests/test_js_prefill_validator.py` |
| Bulk direct submit | Submit configured responses with worker threads and status tracking | yes | yes | manual | desktop/browser | implemented | `tests/test_form_submitter.py`, `tests/test_submission_status_retention.py` |
| Prefill submit | Generate and submit prefilled Google Forms URLs | yes | yes | manual | desktop/browser | implemented | `tests/test_prefill_link_generator.py`, `tests/test_prefill_submission.py` |
| AI answer generation | Generate bounded AI responses and handle model/API validation | yes | yes | manual | backend | implemented | `tests/test_ai_text_route.py`, `tests/test_ai_model_resolution.py`, `tests/test_ai_generator_gating.py` |
| Persistence/history | Store forms, submissions, history, and exports locally | yes | yes | manual | backend | implemented | `tests/test_storage_service.py`, `tests/test_submission_persistence.py`, `tests/test_submission_history_route.py` |
| Runtime diagnostics | Report health, runtime paths, drivers, and monitoring status | yes | yes | manual | desktop/backend | implemented | `tests/test_healthz.py`, `tests/test_runtime_diagnostics_route.py`, `tests/test_monitoring_routes.py` |
| Form copy MVP | Best-effort copy preview and apply flow | yes | yes | manual | desktop/browser | implemented | `tests/test_form_copier.py`, `tests/test_form_copy_planner.py`, `tests/test_form_copy_routes.py`, `tests/test_form_copy_ui.py` |
| Windows packaging | Build backend sidecar and Electron installer | no | no | manual | Windows | implemented | `scripts/package-windows.ps1`, `google_form_tool.spec`, `electron-builder.yml` |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.

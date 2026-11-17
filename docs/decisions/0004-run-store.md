# 0004 Plan runs up front and log rows outside db.json

Date: 2026-11-17

## Status

Accepted

## Context

Release 2.0 needs to preview answers before sending, report actual against
target after sending, retry failed responses, and resume scheduled runs. All
of these need a record of each response, and a preview that matches what is
sent.

Before this change:

- Direct mode drew one random answer set and sent it for every submission in
  the batch, while prefill mode spread each question's percentages across rows
  as exact quotas. Neither had a seed.
- Worker threads shared one `self.responses` attribute, so with more than one
  thread a form could be filled with another row's answers.
- History stored one aggregate `Submission` per batch.
- TinyDB rewrites all of `db.json` on every write and only locks within the
  process (`app/services/storage_service.py`).

## Decision

1. `app/domain/response_plan.py` builds a `ResponsePlan` before any browser
   opens: a seed, a mode, and one row per response with the exact answers
   that will be sent. Branch-to-submit stops and per-mode filtering happen
   here, and each skipped answer is listed with its reason. The same form,
   count, seed and mode always give the same plan. With no seed given, one
   is generated and returned.
   - Prefill keeps exact per-question quotas (`_allocate_counts`) and
     shuffles each question's values across rows with the seed.
   - Direct mode draws every row independently from a per-row seed. This
     replaces the earlier single replayed draw.
2. The submitter works through the plan rows and reports every state change
   of a row (`in_flight`, then `success` or `failed`). Each worker thread
   keeps its own answers.
3. `app/services/run_store.py` stores a small header per run in a new `runs`
   table of `db.json`, written only when the run is created and when its
   status changes. Rows go to `<APP_DATA>/runs/<run_id>.jsonl` (`RUNS_DIR`):
   one `plan` line per row at creation, then one `result` line per change.
   Reads merge by index, and the latest line wins. Lines that are not valid
   JSON are skipped, and a write that follows a torn line starts on a new
   line.
4. The backend writes `<APP_DATA>/runtime.json` (port, pid) at startup for
   local clients.

## Alternatives Considered

1. Rows inside `db.json`. Rejected: every row write would rewrite the whole
   file, and a hard kill mid-write can truncate the saved forms.
2. SQLite. Rejected for now: a new storage engine for one feature, plus a
   migration path, when append-only JSONL covers the access pattern (append
   by many threads, read whole run).
3. Generate answers inside the workers, as before. Rejected: a preview could
   not match what is sent, and a retry could not resend the same answers.

## Consequences

Positive:

- Preview, report, retry and scheduling all read one source of truth.
- Row logging cannot damage saved forms. Deleting `runs/` loses only run
  detail.
- Direct mode now spreads answers according to the configured percentages.

Tradeoffs:

- Direct-mode batches send different answers per submission where they used
  to repeat one set. This is intended, but it is visible behavior.
- Prefill rows are no longer ordered by option. Per-question totals are
  unchanged.
- In prefill mode the browser step may still choose a first option for a
  required choice question the plan left empty. That fallback is not in the
  plan.
- Each JSONL append opens and closes the file, which costs a few
  milliseconds per row.

## Follow-Up

- The simulation and report routes read plans and runs.
- Scheduled runs mark rows left `in_flight` by a restart as `unknown`, and
  never resend them automatically.

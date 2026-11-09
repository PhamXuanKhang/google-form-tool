# 0003 Collapse the harness into one workflow guide

Date: 2026-11-10

## Status

Accepted

## Context

The harness adopted in `0001-brownfield-harness-adoption.md` grew to about 1,800
lines of process docs (harness guide, maturity levels, component taxonomy, trace
spec, context rules, SQL schema, CLI reference) while `docs/product/` was empty.
The CLI binary and its database are git-ignored, so a clean clone could not run
the commands `CLAUDE.md` and `AGENTS.md` required.

## Decision

- Keep the three intake lanes, risk checklist, and hard gates in one short
  document, `docs/WORKFLOW.md`.
- Remove the CLI, trace, maturity, component, backlog, and SQL schema layers, and
  the instruction to run `harness-cli`.
- Track product behavior in `docs/product/user-stories.md` and proof in
  `docs/TEST_MATRIX.md`.
- Keep `docs/decisions/` and the decision template.
- Move the refactor audit to `plans/reports/` because it is a dated record, not
  evergreen guidance.

## Alternatives Considered

1. Keep the harness and commit the CLI. Rejected: it adds a binary and a
   database for a single-maintainer project with no repeated use of them.
2. Delete all process docs. Rejected: the lanes and hard gates still help decide
   how much proof a change needs.

## Consequences

Positive:

- One document to read; a clean clone has every command the docs mention.

Tradeoffs:

- Durable decision and proof rows are no longer queryable; they are files only.
- `.gitignore` still lists the old `harness.db` and CLI paths so local copies stay ignored.

## Follow-Up

- None.

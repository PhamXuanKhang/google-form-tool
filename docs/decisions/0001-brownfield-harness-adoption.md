# 0001 Brownfield Harness Adoption

Date: 2026-06-13

## Status

Accepted

## Context

This repository already has an implemented desktop/local Flask application, a passing pytest suite, GitNexus indexing, and concise project docs. The goal is to adopt Repository Harness without reintroducing large planning packs or generic placeholder docs that make the codebase harder for agents to navigate.

## Decision

Adopt Repository Harness in merge mode and customize it for this brownfield app:

- Keep existing `AGENTS.md`, `CLAUDE.md`, `README.md`, and `docs/ARCHITECTURE.md` as project-specific sources of truth.
- Add Harness intake, context, matrix, templates, durable schema, and CLI support.
- Keep the downloaded `scripts/bin/harness-cli.exe` and generated `harness.db` ignored; they can be restored by rerunning the Harness installer.
- Use Harness for intake/risk/validation framing and GitNexus for code impact/execution-flow analysis.
- Avoid story packets for tiny docs or narrow maintenance edits.

## Alternatives Considered

1. Copy the full upstream harness unchanged. Rejected because generic placeholder decisions and product docs would conflict with the existing app.
2. Keep only the earlier three local docs. Rejected because the Harness CLI, templates, and context rules provide useful agent-native workflows.

## Consequences

Positive:

- Agents get clearer intake, validation, and trace rules.
- The repo keeps a smaller project-specific documentation surface.
- Harness can be refreshed from upstream without replacing product-specific docs.

Tradeoffs:

- The local Harness CLI binary is not tracked, so fresh clones must rerun the installer or download the CLI before using `scripts/bin/harness-cli.exe`.
- Some Harness docs remain process-oriented and should be pruned if they stop helping actual work.

## Follow-Up

- Keep `docs/TEST_MATRIX.md` aligned with real test evidence.
- Add story packets only for normal/high-risk changes that span multiple steps.

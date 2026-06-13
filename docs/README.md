# Documentation Map

This directory holds the project harness and the compact product/validation
context for the existing Google Form Automation Tool app.

## Main Files

- `HARNESS.md`: how humans and agents collaborate.
- `FEATURE_INTAKE.md`: how prompts become tiny, normal, or high-risk work.
- `ARCHITECTURE.md`: architecture discovery and boundary rules.
- `TEST_MATRIX.md`: behavior-to-proof map; current proof status is queried with
  `scripts/bin/harness-cli query matrix`.
- `HARNESS_BACKLOG.md`: harness improvement list; current improvement records
  are stored with `scripts/bin/harness-cli backlog`.
- `GLOSSARY.md`: shared terms.

## Folders

- `product/`: dedicated product contracts when an area outgrows README/architecture docs.
- `stories/`: feature packets and backlog.
- `decisions/`: durable decisions and tradeoffs.
- `templates/`: reusable spec-intake, story, plan, decision, and validation
  formats.

## Current State

Harness is installed into a brownfield app. Use it to classify work, keep
validation proof visible, and leave durable decisions only when they help future
agents avoid repeating context discovery.

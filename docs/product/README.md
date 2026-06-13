# Product Docs

The current product contract lives primarily in `README.md`,
`docs/ARCHITECTURE.md`, and `docs/TEST_MATRIX.md`.

Add files here only when a product area becomes complex enough to need a
dedicated durable contract. Good future candidates are `form-filling.md`,
`prefill-submission.md`, `desktop-runtime.md`, and `form-copy.md`.

Do not create domain files just to fill the folder. A small documentation
surface is healthier than fake product truth.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet for normal/high-risk work.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.

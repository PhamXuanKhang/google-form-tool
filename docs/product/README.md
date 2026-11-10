# Product Docs

User stories with acceptance criteria live in [user-stories.md](./user-stories.md).
The rest of the product contract lives in `README.md`,
`docs/ARCHITECTURE.md`, and `docs/TEST_MATRIX.md`.

Add files here only when a product area becomes complex enough to need a
dedicated durable contract. Good future candidates are `form-filling.md`,
`prefill-submission.md`, `desktop-runtime.md`, and `form-copy.md`.

Do not create domain files just to fill the folder. A small documentation
surface is healthier than fake product truth.

## Update Rule

When behavior changes:

1. Update the affected story in `user-stories.md`.
2. Update `docs/TEST_MATRIX.md`.
3. Record a decision in `docs/decisions/` if the change affects architecture, scope, risk, or a previously settled product rule.

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## Harness

Claude Code loads this file into every session. Keep Harness context focused and agent-native:

@AGENTS.md

@docs/FEATURE_INTAKE.md

Before normal or high-risk work, also read `docs/CONTEXT_RULES.md` and run `scripts/bin/harness-cli.exe query matrix` when the local CLI exists.

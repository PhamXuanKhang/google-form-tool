"""Lightweight static check that AI Generate is only offered for text-like
questions (TIP-006.1).

This project has no JS/jsdom harness, but the gating logic lives in a single
template literal inside question_config.js and is straightforward to verify
by inspecting the source. The test asserts that:

  * the AI Generate <option> is wrapped in a conditional that admits
    input_text and textarea only, and
  * the option is NOT emitted unconditionally inside the
    input_text/textarea/date/time render branch.

If question_config.js is restructured later, update this test to match the
new shape rather than relaxing the assertions.
"""
from pathlib import Path

QUESTION_CONFIG_JS = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "static"
    / "js"
    / "form_filling"
    / "question_config.js"
)


def _load_source() -> str:
    return QUESTION_CONFIG_JS.read_text(encoding="utf-8")


def test_ai_generate_is_gated_by_text_types():
    src = _load_source()
    # Both type checks must be present in the gating expression.
    assert 'type === "input_text"' in src
    assert 'type === "textarea"' in src
    # The gated variable feeds into the dropdown template.
    assert "${aiOption}" in src
    # Sanity: the literal AI Generate option must only appear inside the
    # gating expression (one occurrence — assignment to aiOption), not
    # hard-coded in the template literal.
    occurrences = src.count("AI Generate</option>")
    assert occurrences == 1, (
        f"Expected exactly one literal '<option>AI Generate</option>' "
        f"(inside the type gate), found {occurrences}"
    )


def test_date_and_time_branch_does_not_emit_ai_option_unconditionally():
    src = _load_source()
    # Locate the input_text/textarea/date/time render branch.
    needle = '["input_text", "textarea", "date", "time"].includes(type)'
    start = src.find(needle)
    assert start != -1, "Could not locate the text/date/time render branch"
    # Slice forward to the next else-if branch boundary.
    end = src.find("else if", start + len(needle))
    assert end != -1
    branch = src[start:end]

    # Inside this branch, the option string must appear inside an aiOption
    # ternary, not as a bare option literal in the template.
    assert "aiOption" in branch
    assert 'type === "input_text" || type === "textarea"' in branch
    # The literal option still appears once (as the truthy ternary value),
    # so a count == 1 here is correct.
    assert branch.count("<option>AI Generate</option>") == 1

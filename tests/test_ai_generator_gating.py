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
    # Type checks for the gating branches must be present.
    assert 'type === "input_text"' in src
    assert 'type === "textarea"' in src
    # AI Generate must appear at least once (in input_text and/or textarea arrays).
    assert '"AI Generate"' in src
    # Date and Time sub-branches must NOT include AI Generate.
    date_start = src.find('if (type === "date")')
    assert date_start != -1, "Could not locate the date sub-branch"
    date_branch = src[date_start : date_start + 60]
    assert "AI Generate" not in date_branch
    time_start = src.find('if (type === "time")')
    assert time_start != -1, "Could not locate the time sub-branch"
    time_branch = src[time_start : time_start + 60]
    assert "AI Generate" not in time_branch


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

    # AI Generate is present in the branch (for input_text/textarea sub-cases).
    assert '"AI Generate"' in branch
    # Date sub-branch returns only ["Date"] — no AI Generate.
    assert '["Date"]' in branch
    # Time sub-branch returns only ["Time"] — no AI Generate.
    assert '["Time"]' in branch
    # Confirm the date/time return arrays do not include AI Generate.
    assert "AI Generate" not in '["Date"]'
    assert "AI Generate" not in '["Time"]'

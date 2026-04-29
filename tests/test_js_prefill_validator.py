"""Run the Node.js test suite for the prefill validator under pytest.

The frontend gate that protects /start_submission lives in
``app/static/js/form_filling/prefill_validator.js``. There is no JS test
harness in this project, but Node.js (>=18) is the standard local
prerequisite for running the dev server, so we shell out to it for
unit-level coverage of the validator module.

If Node is not available the test is skipped with a clear message,
documenting the manual verification path in docs/beta-test-runbook.md.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
JS_TEST = REPO_ROOT / "tests" / "js" / "test_prefill_validator.mjs"


@pytest.mark.skipif(
    shutil.which("node") is None,
    reason="Node.js not on PATH; see docs/beta-test-runbook.md §7 for manual verification.",
)
def test_prefill_validator_js_suite():
    assert JS_TEST.exists(), f"Missing JS test file: {JS_TEST}"
    result = subprocess.run(
        ["node", str(JS_TEST)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        f"Node JS validator tests failed (exit {result.returncode}):\n{output}"
    )
    # Sanity: at least the announced count is present so a silent no-op test
    # script can't pass.
    assert "JS tests passed" in result.stdout, (
        f"Unexpected JS test output:\n{output}"
    )

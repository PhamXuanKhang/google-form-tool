"""The packaged backend imports app modules lazily in places, so PyInstaller
only bundles what the spec lists. Every module under app/ must be listed."""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "google_form_tool.spec"


def _app_modules():
    modules = set()
    for path in (REPO_ROOT / "app").rglob("*.py"):
        parts = path.relative_to(REPO_ROOT).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        modules.add(".".join(parts))
    return modules


def test_every_app_module_is_a_hidden_import():
    listed = set(re.findall(r'"(app(?:\.[\w]+)*)"', SPEC.read_text(encoding="utf-8")))

    missing = sorted(_app_modules() - listed)

    assert missing == []

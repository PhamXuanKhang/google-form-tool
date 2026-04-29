"""Static guard for frontend popup wiring.

Several ES modules call ``window.showPopup`` directly. The implementation lives
in ``form_extract.js``, so it must be exposed globally or client-side gates can
silently abort without showing any message.
"""
from pathlib import Path


FORM_EXTRACT_JS = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "static"
    / "js"
    / "form_filling"
    / "form_extract.js"
)


def test_show_popup_is_exposed_on_window():
    source = FORM_EXTRACT_JS.read_text(encoding="utf-8")

    assert "function showPopup" in source
    assert "window.showPopup = showPopup" in source

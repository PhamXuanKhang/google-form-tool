"""Static guard for frontend popup wiring.

Several ES modules call ``window.showPopup`` directly. The implementation lives
in ``form_extract.js``, so it must be exposed globally or client-side gates can
silently abort without showing any message.
"""
from pathlib import Path


FORM_FILLING_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "js" / "form_filling"
FORM_EXTRACT_JS = FORM_FILLING_DIR / "form_extract.js"
FORM_FILLING_MAIN_JS = FORM_FILLING_DIR / "main.js"


def test_show_popup_is_exposed_on_window():
    source = FORM_EXTRACT_JS.read_text(encoding="utf-8")

    assert "function showPopup" in source
    assert "window.showPopup = showPopup" in source


def test_form_preview_escapes_extracted_form_text():
    source = FORM_EXTRACT_JS.read_text(encoding="utf-8")

    assert "function escapeHtml" in source
    assert "escapeHtml(form.title)" in source
    assert "escapeHtml(form.description)" in source
    assert "escapeHtml(q.text)" in source
    assert "escapeHtml(q.type)" in source
    assert "escapeHtml(opt.text)" in source


def test_upload_preview_uses_text_content_for_uploaded_data():
    source = FORM_FILLING_MAIN_JS.read_text(encoding="utf-8")

    assert 'id="upload-preview"' in source
    assert 'document.getElementById("upload-preview").textContent' in source
    assert '${JSON.stringify(result.responses.slice(0, 3), null, 2)}' not in source

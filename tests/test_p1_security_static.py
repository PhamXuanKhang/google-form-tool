from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORM_EXTRACT_JS = REPO_ROOT / "app" / "static" / "js" / "form_filling" / "form_extract.js"
HOME_JS = REPO_ROOT / "app" / "static" / "js" / "home.js"
ELECTRON_MAIN_JS = REPO_ROOT / "electron" / "main.js"


def test_form_preview_escapes_external_google_form_text():
    source = FORM_EXTRACT_JS.read_text(encoding="utf-8")

    assert "function escapeHtml" in source
    assert "${escapeHtml(form.title)}" in source
    assert "${escapeHtml(form.description)}" in source
    assert "${escapeHtml(q.text)}" in source
    assert "${escapeHtml(q.type)}" in source
    assert "${escapeHtml(opt.text)}" in source
    assert "${form.title}" not in source
    assert "${q.text}" not in source
    assert "${opt.text}" not in source


def test_home_delete_uses_json_post_instead_of_destructive_get():
    source = HOME_JS.read_text(encoding="utf-8")

    assert "fetch('/forms/delete'" in source
    assert "method: 'POST'" in source
    assert "JSON.stringify({ form_url: formUrl })" in source
    assert "deleteFormBtn').href = `/?form_url=" not in source


def test_electron_external_links_are_allowlisted():
    source = ELECTRON_MAIN_JS.read_text(encoding="utf-8")

    assert "ALLOWED_EXTERNAL_HOSTS" in source
    assert "'github.com'" in source
    assert "'www.linkedin.com'" in source
    assert "'www.google.com'" in source
    assert "'docs.google.com'" in source
    assert "parsed.protocol === 'mailto:'" in source
    assert "parsed.protocol !== 'https:'" in source
    assert "ALLOWED_EXTERNAL_HOSTS.has(parsed.hostname)" in source

def test_form_copy_renders_navbar_and_safety_ui(client):
    response = client.get("/form_copy?lang=en")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/form_copy"' in text
    assert "fa-copy" in text
    assert "Copy Form" in text
    assert "does not claim an exact clone" in text
    assert 'id="ownership-confirmation"' in text
    assert 'id="apply-copy-btn"' in text
    assert "js/form_copy/main.js" in text


def test_form_copy_static_js_contains_expected_endpoints(client):
    response = client.get("/static/js/form_copy/main.js")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "/form_copy/extract_source" in text
    assert "/form_copy/preview_plan" in text
    assert "/form_copy/apply_to_target" in text
    assert "ownershipConfirmation.checked" in text
    assert "renderCapabilityMatrix" in text


def test_form_copy_static_js_escapes_external_text(client):
    response = client.get("/static/js/form_copy/main.js")
    text = response.get_data(as_text=True)

    assert "function escapeHtml" in text
    assert "escapeHtml(message)" in text
    assert "Source loaded: ${data.form.title}" in text
    assert "escapeHtml(warning.message)" in text
    assert "escapeHtml(result.status)" in text
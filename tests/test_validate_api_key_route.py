def test_validate_api_key_rejects_invalid_without_leaking_key(client, monkeypatch, caplog):
    secret = "super-secret-key"

    class FakeResponder:
        def __init__(self, api_key):
            self.api_key = api_key

        def validate_api_key(self):
            return False

    import app.core.ai_responder as ai_module

    monkeypatch.setattr(ai_module, "AIResponder", FakeResponder)
    monkeypatch.setattr(ai_module, "is_ai_available", lambda: True)

    response = client.post("/validate_api_key", json={"api_key": secret})

    assert response.status_code == 400
    body = response.get_json()
    assert body["valid"] is False
    assert secret not in response.get_data(as_text=True)
    assert secret not in caplog.text


def test_validate_api_key_returns_model_unavailable(client, monkeypatch):
    import app.core.ai_responder as ai_module

    class FakeResponder:
        def __init__(self, _api_key):
            raise ai_module.ModelResolutionError("No Gemini model supports generateContent.")

    monkeypatch.setattr(ai_module, "AIResponder", FakeResponder)
    monkeypatch.setattr(ai_module, "is_ai_available", lambda: True)

    response = client.post("/validate_api_key", json={"api_key": "k"})

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == "model_unavailable"

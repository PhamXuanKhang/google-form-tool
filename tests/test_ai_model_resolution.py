import app.core.ai_responder as ai_module


class FakeModelInfo:
    def __init__(self, name, methods):
        self.name = name
        self.supported_generation_methods = methods


class FakeModelsService:
    def __init__(self, models):
        self._models = models

    def list(self):
        return self._models

    def generate_content(self, model, contents):
        class Resp:
            text = "OK"

        return Resp()


class FakeClient:
    def __init__(self, models):
        self.models = FakeModelsService(models)


class FakeGenAI:
    def __init__(self, models):
        self._models = models

    def Client(self, api_key):
        return FakeClient(self._models)


def test_configured_model_used_when_available(monkeypatch):
    models = [
        FakeModelInfo("models/gemini-fast", ["generateContent"]),
        FakeModelInfo("models/gemini-pro", ["generateContent"]),
    ]
    fake_genai = FakeGenAI(models)
    monkeypatch.setattr(ai_module, "genai", fake_genai)
    monkeypatch.setattr(ai_module, "GENAI_AVAILABLE", True)
    monkeypatch.setattr(ai_module.Config, "GEMINI_MODEL", "models/gemini-fast")

    responder = ai_module.AIResponder("k")
    assert responder.model_name == "models/gemini-fast"


def test_fallback_when_configured_model_missing(monkeypatch):
    models = [
        FakeModelInfo("models/gemini-1.5-flash", ["generateContent"]),
        FakeModelInfo("models/gemini-pro", ["generateContent"]),
    ]
    fake_genai = FakeGenAI(models)
    monkeypatch.setattr(ai_module, "genai", fake_genai)
    monkeypatch.setattr(ai_module, "GENAI_AVAILABLE", True)
    monkeypatch.setattr(ai_module.Config, "GEMINI_MODEL", "models/stale-model")

    responder = ai_module.AIResponder("k")
    assert responder.model_name == "models/gemini-1.5-flash"


def test_no_generate_content_models_raise(monkeypatch):
    models = [FakeModelInfo("models/legacy", ["embedContent"])]
    fake_genai = FakeGenAI(models)
    monkeypatch.setattr(ai_module, "genai", fake_genai)
    monkeypatch.setattr(ai_module, "GENAI_AVAILABLE", True)
    monkeypatch.setattr(ai_module.Config, "GEMINI_MODEL", "models/legacy")

    try:
        ai_module.AIResponder("k")
    except ai_module.ModelResolutionError as e:
        assert "generateContent" in str(e)
    else:
        raise AssertionError("ModelResolutionError expected")

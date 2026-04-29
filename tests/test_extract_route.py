import app.main_routes as main_routes
from app.core.form_extractor import DriverStartupError, FormLoadError


class EmptyStorage:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get_form_by_url(self, url):
        return None

    def save_form(self, form):
        return True


def test_extract_route_rejects_invalid_google_form_url(client):
    response = client.post(
        "/form_filling/extract",
        json={"form_url": "https://example.com/not-a-google-form"},
    )

    assert response.status_code == 400
    assert "valid Google Form URL" in response.get_json()["error"]


def test_extract_route_reports_chrome_driver_startup_error(client, monkeypatch):
    class FailingExtractor:
        def __init__(self, **kwargs):
            pass

        def extract_form_data(self, form_url):
            raise DriverStartupError("bad driver path")

    monkeypatch.setattr(main_routes, "get_storage_service", lambda: EmptyStorage())
    monkeypatch.setattr(main_routes, "FormExtractor", FailingExtractor)

    response = client.post(
        "/form_filling/extract",
        json={"form_url": "https://docs.google.com/forms/d/example/viewform"},
    )

    assert response.status_code == 500
    assert "Chrome or ChromeDriver" in response.get_json()["error"]


def test_extract_route_reports_form_load_error(client, monkeypatch):
    class FailingExtractor:
        def __init__(self, **kwargs):
            pass

        def extract_form_data(self, form_url):
            raise FormLoadError("parse failed")

    monkeypatch.setattr(main_routes, "get_storage_service", lambda: EmptyStorage())
    monkeypatch.setattr(main_routes, "FormExtractor", FailingExtractor)

    response = client.post(
        "/form_filling/extract",
        json={"form_url": "https://docs.google.com/forms/d/example/viewform"},
    )

    assert response.status_code == 500
    assert "could not be loaded or parsed" in response.get_json()["error"]

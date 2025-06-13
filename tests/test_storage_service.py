from tests.conftest import temp_db
from app import StorageService, Form
from config import Config

def test_create_form_success():
    data = {
        "title": "Test form",
        "description": "For testing",
        "url": "https://example.com/form",
        "created_at": "2023-01-01T00:00:00Z",
        "last_used": "2023-01-01T00:00:00Z",
        "response_config": None,
        "submissions": []
    }
    form = Form().from_url(url=data["url"], **{k: v for k, v in data.items() if k != "url"})
    save_result = StorageService(Config.DB_PATH).save_form(form)
    assert isinstance(form, Form)
    assert save_result

def test_connect_db_success():
    storage_service = StorageService(Config.DB_PATH)
    assert storage_service.connect_db()
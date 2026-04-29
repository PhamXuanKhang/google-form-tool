import app.main_routes as main_routes


class EmptyStorage:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get_all_forms_summary(self):
        return []


def test_home_renders_in_english(client, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: EmptyStorage())

    response = client.get("/?lang=en")

    assert response.status_code == 200
    assert b"Recent Forms" in response.data
    assert b"New Form" in response.data


def test_home_renders_in_vietnamese(client, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: EmptyStorage())

    response = client.get("/?lang=vi")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Biểu mẫu gần đây" in text
    assert "Biểu mẫu mới" in text


def test_form_filling_renders_in_english(client):
    response = client.get("/form_filling?lang=en")

    assert response.status_code == 200
    assert b"Step 1: Enter Google Form URL" in response.data
    assert b"Upload a CSV, JSON, or XLSX file with answer data." in response.data


def test_form_filling_renders_in_vietnamese(client):
    response = client.get("/form_filling?lang=vi")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Bước 1: Nhập URL Google Form" in text
    assert "Tải lên tệp CSV, JSON hoặc XLSX chứa dữ liệu trả lời." in text
    assert 'pleaseExtractFormFirst: "Vui l\\u00f2ng tr\\u00edch xu\\u1ea5t' in text

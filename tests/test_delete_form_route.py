import app.main_routes as main_routes


class DeleteStorage:
    def __init__(self, form=None):
        self.form = form
        self.deleted_ids = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get_all_forms_summary(self):
        return [
            {
                "id": self.form.id,
                "url": str(self.form.url),
                "title": self.form.title,
                "description": self.form.description,
                "created_at": self.form.created_at.isoformat(),
                "total_fill": 0,
                "last_used": None,
            }
        ] if self.form else []

    def get_form_by_url(self, url):
        if self.form and str(self.form.url).rstrip('/') == str(url).rstrip('/'):
            return self.form
        return None

    def delete_form(self, form_id):
        self.deleted_ids.append(form_id)


def test_get_home_with_form_url_query_does_not_delete(client, sample_form, monkeypatch):
    storage = DeleteStorage(sample_form)
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    response = client.get(f"/?form_url={sample_form.url}")

    assert response.status_code == 200
    assert storage.deleted_ids == []


def test_delete_form_requires_form_url(client):
    response = client.post("/forms/delete", json={})

    assert response.status_code == 400
    assert "No form URL" in response.get_json()["error"]


def test_delete_form_returns_404_for_unknown_form(client, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: DeleteStorage(None))

    response = client.post("/forms/delete", json={"form_url": "https://docs.google.com/forms/d/missing/viewform"})

    assert response.status_code == 404
    assert "Form not found" in response.get_json()["error"]


def test_delete_form_deletes_matching_form(client, sample_form, monkeypatch):
    storage = DeleteStorage(sample_form)
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: storage)

    response = client.post("/forms/delete", json={"form_url": str(sample_form.url)})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert storage.deleted_ids == [sample_form.id]

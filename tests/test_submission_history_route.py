import app.main_routes as main_routes


class HistoryStorage:
    def __init__(self, form):
        self.form = form

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get_form_by_id(self, form_id):
        if self.form and self.form.id == form_id:
            return self.form
        return None


def test_submission_history_returns_submissions(client, sample_form, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: HistoryStorage(sample_form))

    response = client.get(f"/submission_history/{sample_form.id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["form_id"] == sample_form.id
    assert data["title"] == sample_form.title
    assert data["submissions"] == [
        {
            "submission_id": "sub_001",
            "num_submission": 1,
            "concurrent_thread": 2,
            "time_used": 1345,
            "success_rate": 95.0,
            "network_status": "10ms",
        }
    ]


def test_submission_history_returns_empty_list(client, sample_form, monkeypatch):
    form_without_submissions = sample_form.model_copy(deep=True)
    form_without_submissions.submissions = None
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: HistoryStorage(form_without_submissions))

    response = client.get(f"/submission_history/{sample_form.id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["submissions"] == []


def test_submission_history_returns_404_for_missing_form(client, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: HistoryStorage(None))

    response = client.get("/submission_history/missing_form")

    assert response.status_code == 404
    assert "Form not found" in response.get_json()["error"]


def test_export_history_csv_still_works(client, sample_form, monkeypatch):
    monkeypatch.setattr(main_routes, "get_storage_service", lambda: HistoryStorage(sample_form))

    response = client.get(f"/export_history/{sample_form.id}")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    body = response.get_data(as_text=True)
    assert "submission_id,num_submission,concurrent_thread,time_used,success_rate,network_status" in body
    assert "sub_001,1,2,1345,95.0,10ms" in body

"""
Test suite for the StorageService class which handles all form-related database operations.

This module includes comprehensive tests for:
- Saving forms, including error scenarios.
- Retrieving summaries of all forms.
- Loading individual form data and validating deserialization.
- Getting, updating, and validating response configurations.
- Adding and retrieving submission data.
- Deleting forms and submissions, including edge cases.
- Logging output for all operations at appropriate levels (INFO, WARNING, ERROR).

Each test ensures correct behavior, data integrity, and proper logging under normal and exceptional conditions.
"""
from app import Submission, ResponseConfig, Page, Form
from app.services.storage_service import StorageService
from datetime import datetime
import threading
import pytest
import logging


def test_get_all_forms_summary_empty(temp_db, caplog):
    caplog.set_level(logging.INFO)
    summaries = temp_db.get_all_forms_summary()
    assert summaries == []
    assert "Retrieved 0 forms summary" in caplog.text


def test_get_all_forms_summary_with_data(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    summaries = temp_db.get_all_forms_summary()
    assert len(summaries) == 1
    assert summaries[0]["id"] == "form_001"
    assert summaries[0]["title"] == "Test Form"
    assert summaries[0]["response_config"] is True
    assert summaries[0]["total_fill"] == 1
    assert "Retrieved 1 forms summary" in caplog.text


def test_get_all_forms_summary_error(temp_db, monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    # Simulate database error
    def mock_db_all():
        raise Exception("Database error")
    monkeypatch.setattr(temp_db.db, "all", mock_db_all)
    with pytest.raises(Exception, match="Database error"):
       (temp_db.get_all_forms_summary())
    assert "Error retrieving forms summary: Database error" in caplog.text


def test_load_form_not_found(temp_db, caplog):
    caplog.set_level(logging.WARNING)
    form = temp_db._load_form("form_nonexistent")
    assert form is None
    assert "Form not found: form_nonexistent" in caplog.text


def test_load_form_validation_error(temp_db, caplog, monkeypatch):
    caplog.set_level(logging.ERROR)
    # Simulate invalid form data
    temp_db.db.insert({"id": "form_002", "title": 123})  # Invalid: title should be str
    form = temp_db._load_form("form_002")
    assert form is None
    assert "Validation error for form_id form_002" in caplog.text


def test_get_form_response_config(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    response_config = temp_db.get_form_response_config("form_001")
    assert response_config is not None
    assert len(response_config.pages) == 2
    assert response_config.pages[0].page_id == "page_001"
    assert "Retrieved response config for form: form_001" in caplog.text


def test_get_form_response_config_not_found(temp_db, caplog):
    caplog.set_level(logging.INFO)
    response_config = temp_db.get_form_response_config("form_nonexistent")
    assert response_config is None
    assert "Form not found: form_nonexistent" in caplog.text


def test_get_submission(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    submissions = temp_db.get_submission("form_001")
    assert len(submissions) == 1
    assert submissions[0].submission_id == "sub_001"
    assert "Retrieved submission for form: form_001" in caplog.text


def test_get_submission_not_found(temp_db, caplog):
    caplog.set_level(logging.INFO)
    submissions = temp_db.get_submission("form_nonexistent")
    assert submissions is None
    assert "Form not found: form_nonexistent" in caplog.text



def test_save_form(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    result = temp_db.save_form(sample_form)
    assert result is True
    form = temp_db._load_form("form_001")
    assert form is not None
    assert form.title == "Test Form"
    assert "Saved form: form_001" in caplog.text


def test_save_form_with_no_response_config(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    sample_form.response_config = None
    result = temp_db.save_form(sample_form)
    assert result is True
    form = temp_db._load_form("form_001")
    assert form is not None
    assert form.title == "Test Form"
    assert "Saved form: form_001" in caplog.text
    assert form.response_config is None


def test_save_form_error(temp_db, sample_form, caplog, monkeypatch):
    caplog.set_level(logging.ERROR)
    # Simulate database error
    def mock_db_upsert(*args, **kwargs):
        raise Exception("Database error")
    monkeypatch.setattr(temp_db.db, "upsert", mock_db_upsert)
    result = temp_db.save_form(sample_form)
    assert result is False
    assert "Error saving form form_001: Database error" in caplog.text


def test_update_response_config(temp_db, sample_form, sample_config, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    new_config = ResponseConfig(pages=[Page(page_id="page_new", questions=[])])
    result = temp_db.update_response_config("form_001", new_config)
    assert result is True
    form = temp_db._load_form("form_001")
    assert len(form.response_config.pages) == 1
    assert form.response_config.pages[0].page_id == "page_new"
    assert "Updated response config for form: form_001" in caplog.text


def test_update_response_config_not_found(temp_db, sample_config, caplog):
    caplog.set_level(logging.INFO)
    result = temp_db.update_response_config("form_nonexistent", sample_config)
    assert result is False
    assert "Form not found: form_nonexistent" in caplog.text


def test_add_submission(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    new_submission = Submission(
        submission_id="sub_002",
        num_submission=2,
        concurrent_thread=3,
        time_used=6,
        success_rate=90.0,
        network_status="20ms"
    )
    result = temp_db.add_submission("form_001", new_submission)
    assert result is True
    form = temp_db._load_form("form_001")
    assert len(form.submissions) == 2
    assert form.submissions[1].submission_id == "sub_002"
    assert "Added submission to form: form_001" in caplog.text


def test_add_submission_not_found(temp_db, sample_submission, caplog):
    caplog.set_level(logging.INFO)
    result = temp_db.add_submission("form_nonexistent", sample_submission)
    assert result is False
    assert "Form not found: form_nonexistent" in caplog.text



def test_delete_form(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    result = temp_db.delete_form("form_001")
    assert result is True
    form = temp_db._load_form("form_001")
    assert form is None
    assert "Deleted form: form_001" in caplog.text


def test_delete_form_not_found(temp_db, caplog):
    caplog.set_level(logging.INFO)
    result = temp_db.delete_form("form_nonexistent")
    assert result is True  # TinyDB returns True for remove even if no match
    assert "Deleted form: form_nonexistent" in caplog.text


def test_delete_submission(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    result = temp_db.delete_submission("form_001", "sub_001")
    assert result is True
    form = temp_db._load_form("form_001")
    assert len(form.submissions) == 0
    assert "Deleted submission from form: form_001" in caplog.text


def test_delete_submission_not_found(temp_db, sample_form, caplog):
    caplog.set_level(logging.INFO)
    temp_db.save_form(sample_form)
    result = temp_db.delete_submission("form_001", "sub_nonexistent")
    assert result is True
    form = temp_db._load_form("form_001")
    assert len(form.submissions) == 1  # No change
    assert "Deleted submission from form: form_001" in caplog.text


def test_delete_submission_form_not_found(temp_db, caplog):
    caplog.set_level(logging.INFO)
    result = temp_db.delete_submission("form_nonexistent", "sub_001")
    assert result is False
    assert "Form not found: form_nonexistent" in caplog.text



def test_concurrent_add_submission_keeps_all_rows(temp_db, sample_form):
    temp_db.save_form(sample_form)
    db_path = temp_db.db_path
    errors = []

    def add_submission(index):
        submission = Submission(
            submission_id=f"thread_sub_{index}",
            form_id="form_001",
            num_submission=1,
            concurrent_thread=1,
            time_used=1,
            success_rate=100.0,
            network_status="ok",
            created_at=datetime.now(),
        )
        try:
            with StorageService(db_path) as storage:
                assert storage.add_submission("form_001", submission) is True
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=add_submission, args=(index,)) for index in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    form = temp_db._load_form("form_001")
    submission_ids = {submission.submission_id for submission in form.submissions}
    assert {f"thread_sub_{index}" for index in range(10)}.issubset(submission_ids)


def test_form_id_generation_consistency():
    """Test that both ID generation methods produce identical results for the same URL."""
    test_url = "https://example.com/test-form"
    
    # Test with minimal required fields
    test_kwargs = {
        "title": "Test Form",
        "description": "Test Description",
        "created_at": datetime.now(),
        "last_used": datetime.now(),
        "response_config": None,
        "submissions": None,
    }
    
    # Generate IDs using both methods
    direct_id = Form.get_id_from_url(test_url)
    from_url_id = Form.from_url(test_url, **test_kwargs).id
    
    # Verify consistency
    assert direct_id == from_url_id, (
        f"ID generation mismatch:\n"
        f"get_id_from_url(): {direct_id}\n"
        f"from_url(): {from_url_id}"
    )
    
    # Verify the prefix
    assert direct_id.startswith("f_"), "ID should start with 'f_' prefix"
    
    # Verify same URL produces same ID
    same_url_id = Form.get_id_from_url(test_url)
    assert direct_id == same_url_id, "Same URL should produce same ID"
    
    # Verify different URLs produce different IDs
    different_url_id = Form.get_id_from_url("https://example.com/different-form")
    assert direct_id != different_url_id, "Different URLs should produce different IDs"
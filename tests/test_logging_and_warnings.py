import logging

from app import create_app
from app.core.form_submitter import FormSubmitter, HIGH_FAILURE_WARNING_MESSAGE
from app.logging_config import (
    CONSOLE_HANDLER_NAME,
    FILE_HANDLER_NAME,
    configure_logging,
    logger,
)


def test_logging_configuration_adds_file_handler_without_duplicates(tmp_path):
    configure_logging(tmp_path)
    configure_logging(tmp_path)

    console_handlers = [
        handler for handler in logger.handlers
        if handler.name == CONSOLE_HANDLER_NAME
    ]
    file_handlers = [
        handler for handler in logger.handlers
        if handler.name == FILE_HANDLER_NAME
    ]

    assert len(console_handlers) == 1
    assert len(file_handlers) == 1

    logger.info("file logging smoke test")
    for handler in logger.handlers:
        handler.flush()

    log_file = tmp_path / "app.log"
    assert log_file.exists()
    assert "file logging smoke test" in log_file.read_text(encoding="utf-8")


def test_app_logging_init_does_not_duplicate_handlers():
    create_app(testing=True)
    create_app(testing=True)

    console_handlers = [
        handler for handler in logger.handlers
        if handler.name == CONSOLE_HANDLER_NAME
    ]
    file_handlers = [
        handler for handler in logger.handlers
        if handler.name == FILE_HANDLER_NAME
    ]

    assert len(console_handlers) == 1
    assert len(file_handlers) == 1


def test_low_success_rate_sets_and_logs_warning(sample_form, monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    submitter = FormSubmitter(sample_form)

    def fake_worker(self, num_submissions, min_delay, max_delay, callback=None):
        self.status["success"] += 7
        self.status["failed"] += 3

    monkeypatch.setattr(FormSubmitter, "_submission_worker", fake_worker)

    submission = submitter.submit_form(
        num_submissions=10,
        concurrent_threads=1,
        min_delay=0,
        max_delay=0,
    )

    assert submission.success_rate == 70
    assert submitter.get_status()["warning"] == HIGH_FAILURE_WARNING_MESSAGE
    assert HIGH_FAILURE_WARNING_MESSAGE in caplog.text


def test_normal_success_rate_does_not_set_warning(sample_form, monkeypatch):
    submitter = FormSubmitter(sample_form)

    def fake_worker(self, num_submissions, min_delay, max_delay, callback=None):
        self.status["success"] += 8
        self.status["failed"] += 2

    monkeypatch.setattr(FormSubmitter, "_submission_worker", fake_worker)

    submission = submitter.submit_form(
        num_submissions=10,
        concurrent_threads=1,
        min_delay=0,
        max_delay=0,
    )

    assert submission.success_rate == 80
    assert submitter.get_status()["warning"] is None

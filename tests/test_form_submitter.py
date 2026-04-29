from datetime import datetime

from app.core import form_submitter as form_submitter_module
from app.core.form_submitter import FormSubmitter
from app.models import Form, ResponseConfig


class FakeDriver:
    def __init__(self):
        self.get_url = None

    def get(self, url):
        self.get_url = url


class FakeWebDriverWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, condition):
        return True


def test_submit_single_form_passes_plain_string_url_to_driver(monkeypatch):
    form = Form(
        id="form_001",
        title="Test Form",
        description="Test description",
        url="https://example.com/test-form",
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(pages=[]),
        submissions=None,
    )
    submitter = FormSubmitter(form)
    driver = FakeDriver()

    monkeypatch.setattr(form_submitter_module, "WebDriverWait", FakeWebDriverWait)
    monkeypatch.setattr(submitter, "_fill_page", lambda driver, page_num: False)

    result = submitter._submit_single_form(driver)

    assert result is False
    assert isinstance(driver.get_url, str)
    assert driver.get_url == "https://example.com/test-form"

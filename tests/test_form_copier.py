from app.core.form_copier import FormCopier, is_google_form_edit_url
from app.models import CopyOperation, CopyPlan


class FakeDriver:
    def __init__(self, current_url="https://docs.google.com/forms/d/target/edit", fail_action=None):
        self.current_url = current_url
        self.fail_action = fail_action
        self.actions = []
        self.loaded_url = None
        self.quit_called = False

    def get(self, url):
        self.loaded_url = url

    def quit(self):
        self.quit_called = True

    def record_action(self, action, payload):
        if self.fail_action == action:
            raise RuntimeError(f"{action} failed")
        self.actions.append((action, payload))


class LiveLikeDriver:
    current_url = "https://docs.google.com/forms/d/target/edit"

    def __init__(self):
        self.quit_called = False

    def get(self, url):
        self.loaded_url = url

    def quit(self):
        self.quit_called = True


def make_plan(question_operation=None):
    operations = [
        CopyOperation(
            kind="set_title_description",
            capability="supported",
            payload={"title": "Copied title", "description": "Copied description"},
        )
    ]
    if question_operation:
        operations.append(question_operation)
    return CopyPlan(source_form_id="form_1", source_title="Copied title", operations=operations)


def test_edit_url_validation_accepts_google_forms_edit_urls_only():
    assert is_google_form_edit_url("https://docs.google.com/forms/d/example/edit") is True
    assert is_google_form_edit_url("https://docs.google.com/forms/d/example/edit?usp=sharing") is True
    assert is_google_form_edit_url("https://docs.google.com/forms/d/example/not-edit/edit") is False
    assert is_google_form_edit_url("https://docs.google.com/forms/d/example/viewform") is False
    assert is_google_form_edit_url("https://example.com/forms/d/example/edit") is False


def test_copier_rejects_invalid_target_without_driver():
    result = FormCopier(driver_factory=lambda: FakeDriver()).apply_plan(make_plan(), "https://example.com/edit")

    assert result.status == "failure"
    assert result.warnings[0].code == "invalid_target_url"


def test_copier_quits_driver_when_target_not_editable():
    driver = FakeDriver(current_url="https://example.com/not-google")

    result = FormCopier(driver_factory=lambda: driver).apply_plan(make_plan(), "https://docs.google.com/forms/d/example/edit")

    assert result.status == "failure"
    assert driver.quit_called is True
    assert result.warnings[-1].code == "target_not_editable"


def test_copier_applies_title_description_in_order_and_quits_driver():
    driver = FakeDriver()

    result = FormCopier(driver_factory=lambda: driver).apply_plan(make_plan(), "https://docs.google.com/forms/d/example/edit")

    assert result.status == "success"
    assert driver.loaded_url == "https://docs.google.com/forms/d/example/edit"
    assert driver.actions == [("set_title", "Copied title"), ("set_description", "Copied description")]
    assert driver.quit_called is True


def test_copier_records_warning_when_operation_fails():
    driver = FakeDriver(fail_action="set_title")

    result = FormCopier(driver_factory=lambda: driver).apply_plan(make_plan(), "https://docs.google.com/forms/d/example/edit")

    assert result.status == "partial"
    assert result.operations_failed == 1
    assert result.warnings[-1].code == "operation_failed"


def test_copier_reports_not_implemented_for_live_driver_instead_of_success():
    driver = LiveLikeDriver()

    result = FormCopier(driver_factory=lambda: driver).apply_plan(make_plan(), "https://docs.google.com/forms/d/example/edit")

    assert result.status == "partial"
    assert result.operations_succeeded == 0
    assert result.operation_results[0]["status"] == "skipped"
    assert result.warnings[-1].code == "operation_not_implemented"
    assert driver.quit_called is True


def test_copier_attempts_supported_question_operations():
    driver = FakeDriver()
    question_operation = CopyOperation(
        kind="create_question",
        capability="supported",
        source_question_id="q1",
        source_question_text="Pick one",
        question_type="multiple_choice",
        payload={"text": "Pick one", "type": "multiple_choice", "options": ["A", "B"]},
    )

    result = FormCopier(driver_factory=lambda: driver).apply_plan(make_plan(question_operation), "https://docs.google.com/forms/d/example/edit")

    assert result.status == "success"
    assert driver.actions[-1] == ("create_question", {"type": "multiple_choice", "text": "Pick one", "options": ["A", "B"]})


def test_copier_skips_partial_question_operations():
    driver = FakeDriver()
    question_operation = CopyOperation(
        kind="create_question",
        capability="partial",
        source_question_id="q1",
        source_question_text="Rate",
        question_type="linear_scale",
        payload={"text": "Rate", "type": "linear_scale", "options": []},
    )

    result = FormCopier(driver_factory=lambda: driver).apply_plan(make_plan(question_operation), "https://docs.google.com/forms/d/example/edit")

    assert result.status == "partial"
    assert result.operation_results[-1]["status"] == "skipped"
    assert result.warnings[-1].code == "operation_skipped"
    assert "skipped" in result.warnings[-1].message
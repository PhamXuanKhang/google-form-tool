import pytest
from app.models import Form, Page, Question
from app.core.form_extractor import DriverStartupError, FormExtractor


@pytest.mark.integration
def test_extract_form_data_structure(extractor, sample_form_url):
    form_data: Form = extractor.extract_form_data(sample_form_url)

    # Kiểm tra tiêu đề
    assert form_data.title == "Khảo sát trải nghiệm khách hàng"
    assert form_data.description == "Cảm ơn bạn đã dành chút thời gian để hoàn thành khảo sát ngắn này! Những câu trả lời của bạn giúp chúng tôi cải thiện."

    # Có ít nhất 1 page
    assert len(form_data.response_config.pages) == 4

    # Mỗi page có ít nhất 1 câu hỏi
    for page in form_data.response_config.pages:
        assert isinstance(page, Page)

        for question in page.questions:
            assert isinstance(question, Question)
            assert question.text is not None
            assert question.type in [
                "input_text", "input_email", "multiple_choice",
                "dropdown", "checkbox", "linear_scale", "rank",
                "textarea", "date", "time", "unknown"
            ]
            # TIP-002: real extracted questions (except the q_email pseudo
            # question, which Google does not assign an entry to) must carry
            # an entry_id of the form "entry.<number>" for prefill-link mode.
            if question.question_id != "q_email":
                assert question.entry_id is not None
                assert question.entry_id.startswith("entry.")


def test_extract_form_data_cleanup_when_driver_startup_fails(monkeypatch):
    extractor = FormExtractor(headless=True)

    def fail_to_start():
        raise DriverStartupError("Chrome or ChromeDriver could not start")

    monkeypatch.setattr(extractor, "initialize_driver", fail_to_start)

    with pytest.raises(DriverStartupError):
        extractor.extract_form_data("https://docs.google.com/forms/d/example/viewform")

    assert extractor.driver is None

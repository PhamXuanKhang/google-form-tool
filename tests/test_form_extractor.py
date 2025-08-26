import pytest
from app.models import Form, Page, Question


def test_extract_form_data_structure(extractor, sample_form_url):
    form_data: Form = extractor.extract_form_data(sample_form_url)

    # Kiểm tra tiêu đề
    assert form_data.title == "Khảo sát trải nghiệm khách hàng"
    assert form_data.description == "Cảm ơn bạn đã dành chút thời gian để hoàn thành khảo sát ngắn này! Những câu trả lời của bạn giúp chúng tôi cải thiện."

    # Có ít nhất 1 page
    assert len(form_data.response_config.pages) >= 1

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

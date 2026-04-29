"""
Test suite for FormProcessor class.

Tests for:
- Random response generation
- File data loading (CSV, JSON)
- User edit application
"""
import pytest
import json
import tempfile
import os
from app.core.form_processor import FormProcessor
from app.models import Form, ResponseConfig, Page, Question, AnswerConfig, AnswerOption
from datetime import datetime


@pytest.fixture
def sample_form():
    """Create a sample form with various question types."""
    return Form(
        id="test_form_001",
        title="Test Form",
        description="Test description",
        url="https://example.com/form",
        created_at=datetime.now(),
        last_used=None,
        response_config=ResponseConfig(pages=[
            Page(
                page_id="page_1",
                questions=[
                    Question(
                        question_id="q1",
                        type="input_text",
                        text="Your name?",
                        answer_config=AnswerConfig(fill_percentage=100, answers=[], options=None)
                    ),
                    Question(
                        question_id="q2",
                        type="multiple_choice",
                        text="Favorite color?",
                        answer_config=AnswerConfig(
                            fill_percentage=100,
                            answers=None,
                            options=[
                                AnswerOption(text="Red", percentage=50.0),
                                AnswerOption(text="Blue", percentage=30.0),
                                AnswerOption(text="Green", percentage=20.0),
                            ]
                        )
                    ),
                    Question(
                        question_id="q3",
                        type="checkbox",
                        text="Select hobbies",
                        answer_config=AnswerConfig(
                            fill_percentage=100,
                            answers=None,
                            options=[
                                AnswerOption(text="Reading", percentage=50.0),
                                AnswerOption(text="Sports", percentage=50.0),
                            ]
                        )
                    ),
                ]
            )
        ]),
        submissions=None
    )


@pytest.fixture
def processor(sample_form):
    """Create a FormProcessor instance."""
    return FormProcessor(sample_form)


class TestRandomResponses:
    """Tests for random response generation."""

    def test_generate_random_responses_returns_dict(self, processor):
        responses = processor.generate_random_responses()
        assert isinstance(responses, dict)

    def test_generate_random_responses_has_all_questions(self, processor):
        responses = processor.generate_random_responses(fill_percentage=100)
        assert "q1" in responses
        assert "q2" in responses
        assert "q3" in responses

    def test_text_response_is_string(self, processor):
        responses = processor.generate_random_responses()
        assert isinstance(responses.get("q1"), str)

    def test_multiple_choice_response_is_string(self, processor):
        responses = processor.generate_random_responses()
        q2_response = responses.get("q2")
        assert q2_response in ["Red", "Blue", "Green"]

    def test_checkbox_response_is_list(self, processor):
        responses = processor.generate_random_responses()
        q3_response = responses.get("q3")
        assert isinstance(q3_response, list)
        for item in q3_response:
            assert item in ["Reading", "Sports"]


class TestLoadDataFromFile:
    """Tests for file loading functionality."""

    def test_load_csv_file(self, processor):
        csv_content = "q1,q2,q3\nJohn,Red,Reading\nJane,Blue,\"Reading,Sports\""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            responses_list = processor.load_data_from_file(csv_path)
            assert len(responses_list) == 2
            assert responses_list[0]["q1"] == "John"
            assert responses_list[0]["q2"] == "Red"
            assert responses_list[1]["q1"] == "Jane"
        finally:
            os.unlink(csv_path)

    def test_load_json_file(self, processor):
        json_content = [
            {"q1": "Alice", "q2": "Green", "q3": ["Sports"]},
            {"q1": "Bob", "q2": "Red", "q3": ["Reading", "Sports"]}
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(json_content, f)
            json_path = f.name

        try:
            responses_list = processor.load_data_from_file(json_path)
            assert len(responses_list) == 2
            assert responses_list[0]["q1"] == "Alice"
            assert responses_list[1]["q3"] == ["Reading", "Sports"]
        finally:
            os.unlink(json_path)

    def test_load_with_mapping(self, processor):
        csv_content = "name,color,hobbies\nJohn,Red,Reading"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            mapping = {"name": "q1", "color": "q2", "hobbies": "q3"}
            responses_list = processor.load_data_from_file(csv_path, mapping)
            assert len(responses_list) == 1
            assert responses_list[0]["q1"] == "John"
            assert responses_list[0]["q2"] == "Red"
        finally:
            os.unlink(csv_path)

    def test_load_nonexistent_file_raises(self, processor):
        with pytest.raises(FileNotFoundError):
            processor.load_data_from_file("/nonexistent/path/file.csv")

    def test_load_unsupported_format_raises(self, processor):
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            xlsx_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                processor.load_data_from_file(xlsx_path)
        finally:
            os.unlink(xlsx_path)


class TestApplyUserEdits:
    """Tests for applying user edits to form configuration."""

    def test_apply_fill_percentage_edit(self, processor):
        edits = {
            "q1": {"fill_percentage": 50}
        }
        processor.apply_user_edits(edits)

        q1 = processor.form.response_config.pages[0].questions[0]
        assert q1.answer_config.fill_percentage == 50

    def test_apply_answers_edit(self, processor):
        edits = {
            "q1": {"answers": ["Custom Answer 1", "Custom Answer 2"]}
        }
        processor.apply_user_edits(edits)

        q1 = processor.form.response_config.pages[0].questions[0]
        assert q1.answer_config.answers == ["Custom Answer 1", "Custom Answer 2"]

    def test_apply_options_percentage_edit(self, processor):
        edits = {
            "q2": {
                "options": [
                    {"text": "Red", "percentage": 80},
                    {"text": "Blue", "percentage": 10},
                    {"text": "Green", "percentage": 10},
                ]
            }
        }
        processor.apply_user_edits(edits)

        q2 = processor.form.response_config.pages[0].questions[1]
        options = {opt.text: opt.percentage for opt in q2.answer_config.options}
        assert options["Red"] == 80
        assert options["Blue"] == 10

    def test_apply_edit_to_nonexistent_question_is_ignored(self, processor):
        edits = {
            "nonexistent_q": {"fill_percentage": 50}
        }
        processor.apply_user_edits(edits)

"""
Create fixtures for unit testing
"""
import pytest
import os
from datetime import datetime
from app import create_app, StorageService, Form, Submission, ResponseConfig, Page, Question, AnswerConfig, AnswerOption
from tempfile import NamedTemporaryFile


@pytest.fixture
def client():
    """
    Creates a Flask test client for HTTP route testing.
    """
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_db():
    """
    Provides a temporary TinyDB database instance for testing.
    The file is created with a .json suffix and deleted after tests.
    """
    with NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        db_path = temp_file.name
    with StorageService(db_path) as db:
        yield db
    os.remove(db_path)


@pytest.fixture
def sample_submission():
    """
    Returns a sample Submission object for use in tests.
    """
    return Submission(
        submission_id="sub_001",
        num_submission=1,
        concurrent_thread=2,
        time_used=1345,
        success_rate=95.0,
        network_status="10ms"
    )


@pytest.fixture
def sample_config():
    """
    Returns a sample ResponseConfig with a sample page and question.
    """
    return ResponseConfig(
        pages=[
            Page(
                page_id="page_001",
                questions=[
                    Question(
                        question_id="q_001",
                        type="multiple_choice",
                        text="How satisfied are you?",
                        answer_config=AnswerConfig(
                            options=[
                                AnswerOption(text="Very Satisfied", percentage=50.0, next_page_id="page_002"),
                                AnswerOption(text="Neutral", percentage=30.0)
                            ]
                        )
                    )
                ]
            ),
            Page(page_id="page_002", questions=[])
        ]
    )


@pytest.fixture
def sample_form(sample_config, sample_submission):
    """
    Returns a sample Form object populated with config and one submission.
    """
    return Form(
        id="form_001",
        title="Test Form",
        description="A test form for unit testing",
        url="https://example.com/test",
        created_at=datetime.now(),
        last_used=datetime.now(),
        priority_tags=["test", "unit"],
        response_config=sample_config,
        submissions=[sample_submission]
    )

"""
Define data models for form data and response configuration.
"""
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import List, Optional
from app.utils import generate_uuid_from_url
from uuid import uuid4


class AnswerOption(BaseModel):
    """
    Represents a single option in a multiple-choice question.

    Attributes:
        text (str): The label or content of the answer option.
        percentage (float): The selection probability percentage (0-100) for auto-filling.
        next_page_id (Optional[str]): The ID of the next page if this option is selected (for branching logic).
    """
    text: str
    percentage: float = Field(ge=0, le=100)
    next_page_id: Optional[str] = None


class AnswerConfig(BaseModel):
    """
    Configuration for how a question should be automatically answered.

    Attributes:
        fill_percentage (Optional[float]): Probability that this question will be answered (0-100).
        answers (Optional[List[str]]): List of possible answers (used for text-based questions).
        options (Optional[List[AnswerOption]]): List of multiple-choice options with selection probabilities.
    """
    fill_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    answers: Optional[List[str]] = None
    options: Optional[List[AnswerOption]] = None


class Question(BaseModel):
    """
    Represents a single question within a form page.

    Attributes:
        question_id (str): Unique identifier for the question.
        type (str): Type of the question.
        text (str): The question content.
        answer_config (AnswerConfig): Configuration for how the question should be answered.
    """
    question_id: str
    type: str = Field(pattern=r"^(text|multiple_choice)$")
    text: str
    answer_config: AnswerConfig


class Page(BaseModel):
    """
    Represents a page in a form, which contains a list of questions.

    Attributes:
        page_id (str): Unique identifier for the page (auto-generated).
        questions (List[Question]): List of questions on this page.
    """
    page_id: str = Field(default_factory=lambda: f"page_{uuid4().hex[:8]}")
    questions: List[Question]


class ResponseConfig(BaseModel):
    """
    Defines the structure of the form's response flow.

    Attributes:
        pages (List[Page]): List of all pages that make up the form.
    """
    pages: List[Page]


class Submission(BaseModel):
    """
    Represents a single submission attempt of a form.

    Attributes:
        submission_id (str): Unique identifier for the submission (auto-generated).
        num_submission (int): Number of form submissions executed in this batch.
        concurrent_thread (int): Number of concurrent threads used in submission.
        time_used (int): Times spend for the submission.
        success_rate (float): Percentage of successful submissions (0-100).
        network_status (str): Network condition or response status at the time of submission.
    """
    submission_id: str = Field(default_factory=lambda: f"sub_{uuid4().hex[:8]}")
    num_submission: int = Field(ge=1)
    concurrent_thread: int = Field(ge=1)
    time_used: int
    success_rate: float = Field(ge=0, le=100)
    network_status: str


class Form(BaseModel):
    """
    Represents a complete form including metadata, structure, and submission history.

    Attributes:
        id (str): Unique identifier for the form.
        title (str): Title of the form.
        description (str): Brief description of the form.
        url (HttpUrl): Direct URL to the form.
        created_at (datetime): Date and time the form was created.
        last_used (datetime): Most recent usage timestamp of the form.
        response_config (ResponseConfig): The structure and content of the form.
        submissions (List[Submission]): History of all submission attempts.
    """
    id: str
    title: str
    description: str
    url: HttpUrl
    created_at: datetime
    last_used: datetime
    response_config: ResponseConfig
    submissions: List[Submission]

    @classmethod
    def from_url(cls, url: str, **kwargs):
        """
        Create a Form instance from a given URL, automatically generating a deterministic ID.

        Args:
            url (str): The form's URL to generate the ID from.
            **kwargs: Other keyword arguments for initializing the Form (e.g., title, description).

        Returns:
            Form: A new Form instance with ID generated from the URL.
        """
        return cls(id=f"f_{generate_uuid_from_url(url)}", url=url, **kwargs)


class FormData(BaseModel):
    """
    Represents the in-memory or on-disk database structure that stores multiple forms.

    Attributes:
        forms (List[Form]): List of all forms in the database.
    """
    forms: List[Form]

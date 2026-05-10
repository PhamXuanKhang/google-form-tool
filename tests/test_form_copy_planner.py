from datetime import datetime

from app.core.form_copy_planner import CAPABILITY_MATRIX, FormCopyPlanner, get_capability, normalize_question_type
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig


def make_form(questions):
    return Form(
        id="form_copy_source",
        title="Source title",
        description="Source description",
        url="https://docs.google.com/forms/d/example/viewform",
        created_at=datetime.now(),
        last_used=datetime.now(),
        response_config=ResponseConfig(pages=[Page(page_id="page_1", questions=questions)]),
        submissions=[],
    )


def test_capability_matrix_classifies_supported_partial_and_unsupported_types():
    assert "multiple_choice" in CAPABILITY_MATRIX["supported"]
    assert get_capability("date") == "partial"
    assert get_capability("file_upload") == "unsupported"
    assert normalize_question_type("Multiple Choice") == "multiple_choice"


def test_planner_preserves_title_description_first_and_question_order():
    form = make_form([
        Question(question_id="q1", type="short_answer", text="Name", answer_config=AnswerConfig()),
        Question(
            question_id="q2",
            type="multiple_choice",
            text="Pick one",
            answer_config=AnswerConfig(options=[AnswerOption(text="A", percentage=50), AnswerOption(text="B", percentage=50)]),
        ),
    ])

    plan = FormCopyPlanner().build_plan(form)

    assert plan.operations[0].kind == "set_title_description"
    assert plan.operations[0].payload["title"] == "Source title"
    assert [operation.source_question_id for operation in plan.operations[1:]] == ["q1", "q2"]
    assert plan.operations[2].payload["options"] == ["A", "B"]
    assert plan.warnings == []


def test_planner_generates_warnings_for_partial_and_unsupported_questions():
    form = make_form([
        Question(question_id="q1", type="linear_scale", text="Rate", answer_config=AnswerConfig()),
        Question(question_id="q2", type="file_upload", text="Upload", answer_config=AnswerConfig()),
    ])

    plan = FormCopyPlanner().build_plan(form)

    assert [operation.capability for operation in plan.operations[1:]] == ["partial", "unsupported"]
    assert [warning.capability for warning in plan.warnings] == ["partial", "unsupported"]
    assert "exact" not in " ".join(warning.message.lower() for warning in plan.warnings)

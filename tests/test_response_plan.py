from collections import Counter
from datetime import datetime

import pytest

from app.domain.form_processor import FormProcessor
from app.domain.response_plan import (
    PLAN_MODE_DOM_FILL,
    PLAN_MODE_PREFILL,
    SKIP_REASON_DOM_FILL,
    SKIP_REASON_PREFILL,
    build_plan,
)
from app.models import AnswerConfig, AnswerOption, Form, Page, Question, ResponseConfig

pytestmark = pytest.mark.domain


def _form():
    return Form(
        id="form_plan",
        title="Plan form",
        description="",
        url="https://docs.google.com/forms/d/e/PLAN/viewform",
        created_at=datetime(2026, 1, 1),
        last_used=None,
        response_config=ResponseConfig(pages=[
            Page(page_id="p1", questions=[
                Question(question_id="name", entry_id="entry.1", type="input_text", text="Name",
                         answer_config=AnswerConfig(fill_percentage=100, answers=None, options=None)),
                Question(question_id="color", entry_id="entry.2", type="multiple_choice", text="Color",
                         answer_config=AnswerConfig(fill_percentage=100, options=[
                             AnswerOption(text="Red", percentage=60.0),
                             AnswerOption(text="Blue", percentage=30.0),
                             AnswerOption(text="Green", percentage=10.0),
                         ])),
                Question(question_id="size", entry_id="entry.3", type="dropdown", text="Size",
                         answer_config=AnswerConfig(fill_percentage=100, options=[
                             AnswerOption(text="S", percentage=50.0),
                             AnswerOption(text="L", percentage=50.0),
                         ])),
                Question(question_id="cv", entry_id="entry.4", type="file_upload", text="CV",
                         answer_config=None),
                Question(question_id="order", entry_id="entry.5", type="rank", text="Order",
                         answer_config=AnswerConfig(options=[AnswerOption(text="a", percentage=50.0), AnswerOption(text="b", percentage=50.0)])),
            ]),
        ]),
        submissions=None,
    )


@pytest.mark.parametrize("mode", [PLAN_MODE_PREFILL, PLAN_MODE_DOM_FILL])
def test_same_seed_gives_identical_plans(mode):
    first = build_plan(_form(), 30, seed=1234, mode=mode)
    second = build_plan(_form(), 30, seed=1234, mode=mode)

    assert first.to_dict() == second.to_dict()


@pytest.mark.parametrize("mode", [PLAN_MODE_PREFILL, PLAN_MODE_DOM_FILL])
def test_different_seeds_give_different_plans(mode):
    first = build_plan(_form(), 30, seed=1, mode=mode)
    second = build_plan(_form(), 30, seed=2, mode=mode)

    assert first.answers() != second.answers()


def test_missing_seed_is_generated_and_reproduces_the_plan():
    plan = build_plan(_form(), 10, mode=PLAN_MODE_DOM_FILL)

    assert isinstance(plan.seed, int)
    assert build_plan(_form(), 10, seed=plan.seed, mode=PLAN_MODE_DOM_FILL).answers() == plan.answers()


def test_prefill_plan_keeps_exact_quota_per_question():
    plan = build_plan(_form(), 37, seed=99, mode=PLAN_MODE_PREFILL)

    colors = Counter(row.answers["color"] for row in plan.rows)
    sizes = Counter(row.answers["size"] for row in plan.rows)
    expected_colors = FormProcessor._allocate_counts([60.0, 30.0, 10.0], 37)
    expected_sizes = FormProcessor._allocate_counts([50.0, 50.0], 37)

    assert [colors["Red"], colors["Blue"], colors["Green"]] == expected_colors
    assert [sizes["S"], sizes["L"]] == expected_sizes


def test_prefill_plan_skips_types_prefill_cannot_send():
    plan = build_plan(_form(), 3, seed=5, mode=PLAN_MODE_PREFILL)

    for row in plan.rows:
        assert "cv" not in row.answers
        assert "order" in row.answers
    assert plan.skipped_summary() == {}

    uploaded = build_plan(_form(), 0, seed=5, mode=PLAN_MODE_PREFILL,
                          responses_list=[{"name": "Ann", "cv": "x.pdf"}])
    assert uploaded.rows[0].answers == {"name": "Ann"}
    assert uploaded.rows[0].skipped == [
        {"question_id": "cv", "type": "file_upload", "reason": SKIP_REASON_PREFILL}
    ]
    assert uploaded.skipped_summary() == {"file_upload": 1}


def test_direct_plan_skips_types_the_browser_filler_does_not_answer():
    plan = build_plan(_form(), 4, seed=7, mode=PLAN_MODE_DOM_FILL)

    for row in plan.rows:
        assert "order" not in row.answers
        assert {"question_id": "order", "type": "rank", "reason": SKIP_REASON_DOM_FILL} in row.skipped
        assert set(row.answers) == {"name", "color", "size"}


def test_direct_plan_draws_rows_independently():
    plan = build_plan(_form(), 40, seed=11, mode=PLAN_MODE_DOM_FILL)

    assert len({row.answers["name"] for row in plan.rows}) > 1
    assert len({row.answers["color"] for row in plan.rows}) > 1


def test_uploaded_rows_override_count_and_keep_order():
    rows = [{"name": "A"}, {"name": "B"}, {"name": "C"}]

    plan = build_plan(_form(), 99, seed=3, mode=PLAN_MODE_DOM_FILL, responses_list=rows)

    assert [row.index for row in plan.rows] == [0, 1, 2]
    assert [row.answers["name"] for row in plan.rows] == ["A", "B", "C"]
    assert rows[0] == {"name": "A"}


def test_fixed_responses_are_repeated():
    plan = build_plan(_form(), 3, seed=3, mode=PLAN_MODE_PREFILL, responses={"name": "Same"})

    assert plan.answers() == [{"name": "Same"}] * 3


def test_branch_to_submit_drops_later_page_answers():
    form = _form()
    form.response_config.pages[0].questions[1].answer_config.options[0].next_page_id = "__submit__"
    form.response_config.pages.append(Page(page_id="p2", questions=[
        Question(question_id="later", entry_id="entry.9", type="input_text", text="Later",
                 answer_config=AnswerConfig(fill_percentage=100, answers=["x"])),
    ]))

    for mode in (PLAN_MODE_PREFILL, PLAN_MODE_DOM_FILL):
        plan = build_plan(form, 20, seed=8, mode=mode)
        for row in plan.rows:
            if row.answers.get("color") == "Red":
                assert "later" not in row.answers
            else:
                assert row.answers.get("later") == "x"


def test_form_saved_by_version_one_still_builds_a_plan():
    stored = {
        "id": "legacy",
        "title": "Legacy",
        "description": "",
        "url": "https://docs.google.com/forms/d/e/LEGACY/viewform",
        "created_at": "2025-05-01T10:00:00",
        "last_used": None,
        "response_config": {"pages": [{"page_id": "p1", "questions": [
            {"question_id": "q1", "type": "multiple_choice", "text": "Pick",
             "answer_config": {"fill_percentage": 100, "answers": None,
                               "options": [{"text": "Yes", "percentage": 100.0, "next_page_id": None}]}},
        ]}]},
        "submissions": [],
    }
    form = Form.model_validate(stored)

    for mode in (PLAN_MODE_PREFILL, PLAN_MODE_DOM_FILL):
        plan = build_plan(form, 2, seed=1, mode=mode)
        assert plan.answers() == [{"q1": "Yes"}, {"q1": "Yes"}]


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown submission_mode"):
        build_plan(_form(), 1, seed=1, mode="bogus")

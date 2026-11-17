import pytest

from app.domain.run_report import distribution, retry_candidates

pytestmark = pytest.mark.domain

SNAPSHOT = {
    "color": {"text": "Color", "type": "multiple_choice", "entry_param": "entry.1", "fill_percentage": 100,
              "options": {"Red": 3.0, "Blue": 1.0}},
    "tags": {"text": "Tags", "type": "checkbox", "entry_param": "entry.2", "fill_percentage": 100,
             "options": {"A": 50.0, "B": 80.0}},
    "name": {"text": "Name", "type": "input_text", "entry_param": "entry.3", "fill_percentage": 50,
             "options": None},
}


def _by_id(questions):
    return {question["question_id"]: question for question in questions}


def test_single_choice_targets_are_normalized_and_other_values_listed():
    rows = [{"color": "Red"}, {"entry.1": "Blue"}, {"color": "Green"}, {}]

    color = _by_id(distribution(SNAPSHOT, rows))["color"]

    assert color["kind"] == "choice"
    assert color["options"] == [
        {"text": "Red", "count": 1, "target": 75.0, "rate": 25.0},
        {"text": "Blue", "count": 1, "target": 25.0, "rate": 25.0},
        {"text": "Green", "count": 1, "target": None, "rate": 25.0},
    ]
    assert (color["answered"], color["blank"], color["blank_rate"]) == (3, 1, 25.0)


def test_checkbox_counts_each_selected_option():
    rows = [{"tags": ["A", "B"]}, {"tags": ["B"]}]

    tags = _by_id(distribution(SNAPSHOT, rows))["tags"]

    assert {o["text"]: (o["count"], o["rate"], o["target"]) for o in tags["options"]} == {
        "A": (1, 50.0, 50.0), "B": (2, 100.0, 80.0),
    }


def test_text_questions_report_distinct_values_and_samples():
    rows = [{"name": "Ann"}, {"name": "Bob"}, {"name": "Ann"}, {"name": ""}]

    name = _by_id(distribution(SNAPSHOT, rows))["name"]

    assert name["kind"] == "text"
    assert name["distinct"] == 2
    assert name["samples"] == ["Ann", "Bob"]
    assert name["target_fill"] == 50
    assert name["blank"] == 1


def test_empty_rows_give_zero_rates():
    color = _by_id(distribution(SNAPSHOT, []))["color"]

    assert all(option["rate"] == 0.0 for option in color["options"])


def _rows(*statuses):
    return [{"index": i, "status": status, "answers": {"i": i}} for i, status in enumerate(statuses)]


def test_retry_candidates_take_failed_rows_and_unknown_only_on_request():
    original = _rows("success", "failed", "unknown", "planned")

    assert [row["index"] for row in retry_candidates([original])] == [1]
    assert [row["index"] for row in retry_candidates([original], include_unknown=True)] == [1, 2]


def test_retry_candidates_follow_the_latest_attempt_of_each_row():
    original = _rows("failed", "failed", "failed")
    first_retry = [
        {"index": 0, "status": "success"},
        {"index": 1, "status": "failed"},
        {"index": 2, "status": "planned"},
    ]

    remaining = retry_candidates([original, first_retry])

    assert [row["index"] for row in remaining] == [1, 2]
    assert remaining[0]["answers"] == {"i": 1}
    assert retry_candidates([]) == []

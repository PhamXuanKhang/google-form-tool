"""Unit tests for PrefillLinkGenerator (TIP-003)."""
from datetime import date, datetime
from urllib.parse import parse_qsl, urlsplit

import pytest

from app.core.prefill_link_generator import PrefillLinkGenerator
from app.models import (
    AnswerConfig,
    AnswerOption,
    Form,
    Page,
    Question,
    ResponseConfig,
)


def _make_form(*questions: Question, url: str = None) -> Form:
    return Form(
        id="form_test",
        title="t",
        description="",
        url=url or "https://docs.google.com/forms/d/e/FAKEID/viewform",
        created_at=datetime(2026, 1, 1),
        last_used=None,
        response_config=ResponseConfig(
            pages=[Page(page_id="page_1", questions=list(questions))]
        ),
        submissions=None,
    )


def _text_q(qid: str, entry: str = None) -> Question:
    return Question(
        question_id=qid,
        entry_id=entry,
        type="input_text",
        text=qid,
        answer_config=AnswerConfig(fill_percentage=100, answers=[], options=None),
    )


def _mc_q(qid: str, entry: str, options: list) -> Question:
    return Question(
        question_id=qid,
        entry_id=entry,
        type="multiple_choice",
        text=qid,
        answer_config=AnswerConfig(
            fill_percentage=100,
            answers=None,
            options=[AnswerOption(text=o, percentage=0) for o in options],
        ),
    )


def _checkbox_q(qid: str, entry: str, options: list) -> Question:
    return Question(
        question_id=qid,
        entry_id=entry,
        type="checkbox",
        text=qid,
        answer_config=AnswerConfig(
            fill_percentage=100,
            answers=None,
            options=[AnswerOption(text=o, percentage=0) for o in options],
        ),
    )


def _params(url: str):
    return parse_qsl(urlsplit(url).query, keep_blank_values=True)


# ---------------------------------------------------------------- single field

def test_single_text_field():
    form = _make_form(_text_q("111", "entry.111"))
    url = PrefillLinkGenerator(form).build_prefill_url({"111": "Alice"})
    pairs = _params(url)
    assert pairs[0] == ("usp", "pp_url")
    assert ("entry.111", "Alice") in pairs
    assert urlsplit(url).path.endswith("/viewform")


def test_multiple_choice_emits_one_param():
    form = _make_form(_mc_q("111", "entry.111", ["A", "B"]))
    url = PrefillLinkGenerator(form).build_prefill_url({"111": "A"})
    pairs = _params(url)
    assert pairs.count(("entry.111", "A")) == 1


# -------------------------------------------------------------------- checkbox

def test_checkbox_emits_repeated_params():
    form = _make_form(_checkbox_q("111", "entry.111", ["A", "B", "C"]))
    url = PrefillLinkGenerator(form).build_prefill_url({"111": ["A", "B"]})
    pairs = _params(url)
    assert ("entry.111", "A") in pairs
    assert ("entry.111", "B") in pairs
    # Two answer params for entry.111
    assert sum(1 for k, _ in pairs if k == "entry.111") == 2


# -------------------------------------------------------------------- key forms

def test_response_keyed_by_raw_question_id():
    form = _make_form(_text_q("123", "entry.123"))
    url = PrefillLinkGenerator(form).build_prefill_url({"123": "v"})
    assert ("entry.123", "v") in _params(url)


def test_response_keyed_by_full_entry_id():
    form = _make_form(_text_q("123", "entry.123"))
    url = PrefillLinkGenerator(form).build_prefill_url({"entry.123": "v"})
    assert ("entry.123", "v") in _params(url)


def test_falls_back_to_numeric_question_id_when_entry_id_missing():
    # Question stored before TIP-002: no entry_id, but question_id is numeric.
    form = _make_form(_text_q("777", entry=None))
    url = PrefillLinkGenerator(form).build_prefill_url({"777": "v"})
    assert ("entry.777", "v") in _params(url)


# ----------------------------------------------------------------- skip values

@pytest.mark.parametrize("value", [None, "", []])
def test_empty_values_are_skipped(value):
    form = _make_form(_text_q("111", "entry.111"))
    url = PrefillLinkGenerator(form).build_prefill_url({"111": value})
    pairs = _params(url)
    assert all(k != "entry.111" for k, _ in pairs)


def test_checkbox_skips_empty_items():
    form = _make_form(_checkbox_q("111", "entry.111", ["A"]))
    url = PrefillLinkGenerator(form).build_prefill_url({"111": ["A", "", None]})
    pairs = _params(url)
    assert sum(1 for k, _ in pairs if k == "entry.111") == 1


# ------------------------------------------------------------------ error path

def test_missing_entry_mapping_raises():
    # Non-numeric question_id and no entry_id -> get_entry_param() -> None.
    q = Question(
        question_id="q_email",
        type="input_email",
        text="email",
        answer_config=AnswerConfig(fill_percentage=0, answers=[], options=None),
    )
    form = _make_form(q)
    with pytest.raises(ValueError, match="No entry mapping"):
        PrefillLinkGenerator(form).build_prefill_url({"q_email": "x@y.com"})


def test_nested_object_value_raises():
    form = _make_form(_text_q("111", "entry.111"))
    with pytest.raises(ValueError, match="not supported"):
        PrefillLinkGenerator(form).build_prefill_url({"111": {"nested": 1}})


# --------------------------------------------------------- url normalization

def test_normalizes_form_response_url():
    form = _make_form(
        _text_q("111", "entry.111"),
        url="https://docs.google.com/forms/d/e/FAKEID/formResponse",
    )
    url = PrefillLinkGenerator(form).build_prefill_url({"111": "v"})
    parts = urlsplit(url)
    assert parts.path.endswith("/viewform")
    assert "formResponse" not in parts.path


def test_existing_query_params_are_preserved_but_entry_overwritten():
    # Match the old prefill-link script: generated links start from usp=pp_url
    # and discard stale/custom query params from the source URL.
    form = _make_form(
        _text_q("111", "entry.111"),
        url="https://docs.google.com/forms/d/e/FAKEID/viewform?entry.111=stale&track=keep&usp=foo",
    )
    url = PrefillLinkGenerator(form).build_prefill_url({"111": "fresh"})
    pairs = _params(url)
    assert ("track", "keep") not in pairs
    assert ("entry.111", "fresh") in pairs
    assert ("entry.111", "stale") not in pairs
    assert ("usp", "pp_url") in pairs
    # Only one usp value.
    assert sum(1 for k, _ in pairs if k == "usp") == 1


# ------------------------------------------------------------------------ batch

def test_build_prefill_urls_batch():
    form = _make_form(_text_q("111", "entry.111"))
    urls = PrefillLinkGenerator(form).build_prefill_urls(
        [{"111": "a"}, {"111": "b"}]
    )
    assert len(urls) == 2
    assert ("entry.111", "a") in _params(urls[0])
    assert ("entry.111", "b") in _params(urls[1])


# ---------------------------------------------------------------- date / time

def test_date_object_is_iso_formatted():
    form = _make_form(_text_q("111", "entry.111"))
    url = PrefillLinkGenerator(form).build_prefill_url({"111": date(2026, 4, 29)})
    assert ("entry.111", "2026-04-29") in _params(url)

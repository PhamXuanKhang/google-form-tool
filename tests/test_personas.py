import json
import random
from collections import Counter
from datetime import datetime

import pytest

from app.domain.form_processor import FormProcessor
from app.domain.personas import merged_form
from app.domain.response_plan import PLAN_MODE_DOM_FILL, PLAN_MODE_PREFILL, build_plan, target_snapshot
from app.domain.run_report import summarize_run
from app.models import AnswerConfig, AnswerOption, Form, Page, Persona, Question, ResponseConfig

X = {"X1", "X2"}
Y = {"Y1", "Y2"}


def _options(percentages):
    return [AnswerOption(text=text, percentage=pct) for text, pct in percentages.items()]


def _form(personas=None):
    shared = {"X1": 25.0, "X2": 25.0, "Y1": 25.0, "Y2": 25.0}
    return Form(
        id="f_per", title="Personas", description="", url="https://docs.google.com/forms/d/e/PER/viewform",
        created_at=datetime(2026, 1, 1), last_used=None, submissions=None,
        response_config=ResponseConfig(pages=[Page(page_id="p1", questions=[
            Question(question_id="q1", entry_id="entry.1", type="multiple_choice", text="First",
                     answer_config=AnswerConfig(fill_percentage=100, options=_options(shared))),
            Question(question_id="q2", entry_id="entry.2", type="dropdown", text="Second",
                     answer_config=AnswerConfig(fill_percentage=100, options=_options(shared))),
        ])]),
        personas=personas,
    )


def _split_personas():
    only_x = AnswerConfig(fill_percentage=100, options=_options({"X1": 50.0, "X2": 50.0, "Y1": 0.0, "Y2": 0.0}))
    only_y = AnswerConfig(fill_percentage=100, options=_options({"X1": 0.0, "X2": 0.0, "Y1": 50.0, "Y2": 50.0}))
    return [
        Persona(persona_id="a", name="Group X", weight=60, overrides={"q1": only_x, "q2": only_x}),
        Persona(persona_id="b", name="Group Y", weight=40, overrides={"q1": only_y, "q2": only_y}),
    ]


# ------------------------------------------------------------------ plans


@pytest.mark.domain
@pytest.mark.parametrize("mode", [PLAN_MODE_PREFILL, PLAN_MODE_DOM_FILL])
def test_personas_get_their_weighted_share_and_never_mix_answers(mode):
    plan = build_plan(_form(_split_personas()), 100, seed=21, mode=mode)

    assert Counter(row.persona_id for row in plan.rows) == {"a": 60, "b": 40}
    for row in plan.rows:
        values = {row.answers["q1"], row.answers["q2"]}
        expected = X if row.persona_id == "a" else Y
        assert values <= expected, (row.persona_id, values)
    assert plan.to_dict() == build_plan(_form(_split_personas()), 100, seed=21, mode=mode).to_dict()
    # Rows of the two personas are interleaved, not in two blocks.
    first_forty = [row.persona_id for row in plan.rows[:40]]
    assert set(first_forty) == {"a", "b"}


@pytest.mark.domain
def test_without_personas_the_plan_is_unchanged():
    form = _form()
    seed, count = 5, 30

    plan = build_plan(form, count, seed=seed, mode=PLAN_MODE_PREFILL)

    processor = FormProcessor(form, rng=random.Random(seed))
    expected = processor.apply_prefill_branch_stops(processor.generate_prefill_responses(count, shuffle=True))
    assert plan.answers() == expected
    assert all(row.persona_id is None and "persona_id" not in row.to_dict() for row in plan.rows)

    direct = build_plan(form, 5, seed=seed, mode=PLAN_MODE_DOM_FILL)
    assert direct.answers() == [
        FormProcessor(form, rng=random.Random(f"{seed}:{i}")).generate_random_responses() for i in range(5)
    ]


@pytest.mark.domain
def test_forms_saved_before_personas_still_load():
    data = _form().model_dump(mode="json")
    data.pop("personas")

    form = Form.model_validate(data)

    assert form.personas is None
    assert build_plan(form, 3, seed=1).rows


@pytest.mark.domain
def test_blended_targets_and_shared_branching():
    form = _form(_split_personas())
    form.response_config.pages[0].questions[0].answer_config.options[0].next_page_id = "__submit__"

    snapshot = target_snapshot(form)
    merged = merged_form(form, form.personas[0])

    assert snapshot["q1"]["options"] == {"X1": 30.0, "X2": 30.0, "Y1": 20.0, "Y2": 20.0}
    assert merged.response_config.pages[0].questions[0].answer_config.options[0].next_page_id == "__submit__"
    assert merged.personas is None


@pytest.mark.domain
@pytest.mark.parametrize("mode", [PLAN_MODE_PREFILL, PLAN_MODE_DOM_FILL])
def test_partial_overrides_keep_the_shared_fields(mode):
    fill_only = Persona(persona_id="f", name="Fill only", weight=50,
                        overrides={"q1": AnswerConfig(fill_percentage=50)})
    options_only = Persona(persona_id="o", name="Options only", weight=50,
                           overrides={"q2": AnswerConfig(options=_options({"X1": 100.0, "X2": 0.0, "Y1": 0.0, "Y2": 0.0}))})
    form = _form([fill_only, options_only])

    merged_fill = merged_form(form, fill_only).response_config.pages[0].questions[0].answer_config
    merged_options = merged_form(form, options_only).response_config.pages[0].questions[1].answer_config
    plan = build_plan(form, 40, seed=2, mode=mode)

    assert merged_fill.fill_percentage == 50 and [o.text for o in merged_fill.options] == ["X1", "X2", "Y1", "Y2"]
    assert merged_options.fill_percentage == 100
    known = X | Y
    for row in plan.rows:
        assert set(row.answers.values()) <= known, row.answers
        if row.persona_id == "o":
            assert row.answers["q2"] == "X1"


@pytest.mark.domain
def test_run_report_breaks_results_down_by_persona():
    form = _form(_split_personas())
    from app.domain.personas import persona_targets

    header = {"target_snapshot": target_snapshot(form), "personas": persona_targets(form)}
    rows = [
        {"index": 0, "status": "success", "persona_id": "a", "answers": {"q1": "X1", "q2": "X2"}},
        {"index": 1, "status": "success", "persona_id": "b", "answers": {"q1": "Y1", "q2": "Y2"}},
        {"index": 2, "status": "failed", "persona_id": "a", "answers": {"q1": "X2", "q2": "X1"}},
    ]

    summary = summarize_run(form, header, rows)

    by_id = {persona["persona_id"]: persona for persona in summary["personas"]}
    assert (by_id["a"]["count"], by_id["b"]["count"]) == (1, 1)
    q1 = by_id["b"]["questions"][0]
    assert {o["text"]: o["target"] for o in q1["options"]} == {"X1": 0.0, "X2": 0.0, "Y1": 50.0, "Y2": 50.0}


# ----------------------------------------------------------------- routes


class MemoryStorage:
    def __init__(self, form):
        self.data = form.model_dump(mode="json")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def get_form_by_id(self, form_id):
        return Form.model_validate(self.data) if form_id == self.data["id"] else None

    def save_form(self, form):
        self.data = form.model_dump(mode="json")
        return True

    def update_personas(self, form_id, personas):
        form = Form.model_validate(self.data)
        form.personas = list(personas) or None
        self.data = form.model_dump(mode="json")
        return True


def _persona_payload():
    return [persona.model_dump(mode="json") for persona in _split_personas()]


@pytest.fixture
def storage(storage_stub):
    return storage_stub(MemoryStorage(_form()))


def test_set_and_get_personas(client, storage):
    saved = client.post("/forms/f_per/personas", json={"personas": _persona_payload()})
    listed = client.get("/forms/f_per/personas").get_json()["personas"]

    assert saved.status_code == 200
    assert [p["name"] for p in listed] == ["Group X", "Group Y"]
    assert client.post("/forms/f_per/personas", json={"personas": []}).status_code == 200
    assert client.get("/forms/f_per/personas").get_json()["personas"] == []


@pytest.mark.parametrize("mutate", [
    lambda personas: personas[0].update(weight=59),
    lambda personas: personas.extend([dict(personas[0], persona_id=f"x{i}", weight=0) for i in range(7)]),
    lambda personas: personas[0]["overrides"].update({"nope": {"fill_percentage": 100}}),
    lambda personas: personas[0]["overrides"]["q1"]["options"].append({"text": "Z", "percentage": 0}),
    lambda personas: personas[0]["overrides"]["q1"]["options"][0].update(percentage=90),
    lambda personas: personas[1].update(persona_id="a"),
    lambda personas: personas[0].update(weight=-5),
])
def test_invalid_personas_are_rejected_and_nothing_is_saved(client, storage, mutate):
    personas = _persona_payload()
    mutate(personas)
    before = json.loads(json.dumps(storage.data))

    response = client.post("/forms/f_per/personas", json={"personas": personas})

    assert response.status_code == 400
    assert storage.data == before


def test_simulation_shows_the_persona_split(client, storage):
    client.post("/forms/f_per/personas", json={"personas": _persona_payload()})

    data = client.post("/simulate", json={"form_id": "f_per", "num_submissions": 50, "seed": 3}).get_json()

    assert {p["persona_id"]: p["count"] for p in data["personas"]} == {"a": 30, "b": 20}


def test_templates_carry_personas(client, storage):
    client.post("/forms/f_per/personas", json={"personas": _persona_payload()})
    template = client.get("/forms/f_per/config/export").get_json()
    client.post("/forms/f_per/personas", json={"personas": []})

    preview = client.post("/forms/f_per/config/import", json={"template": template}).get_json()
    applied = client.post("/forms/f_per/config/import", json={"template": template, "apply": True}).get_json()

    assert len(template["personas"]) == 2
    assert preview["preview"]["personas"] == {"status": "included", "count": 2}
    assert applied["applied"] is True
    assert len(client.get("/forms/f_per/personas").get_json()["personas"]) == 2

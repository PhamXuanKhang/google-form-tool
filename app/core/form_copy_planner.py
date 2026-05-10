from app.models import CopyOperation, CopyPlan, CopyWarning, Form

CAPABILITY_MATRIX = {
    "supported": ["short_answer", "paragraph", "multiple_choice", "checkbox", "dropdown"],
    "partial": ["linear_scale", "date", "time"],
    "unsupported": ["multiple_choice_grid", "checkbox_grid", "file_upload", "rating", "quiz", "theme", "branching", "validation"],
}

_TYPE_ALIASES = {
    "short answer": "short_answer",
    "short_answer": "short_answer",
    "text": "short_answer",
    "paragraph": "paragraph",
    "multiple choice": "multiple_choice",
    "multiple_choice": "multiple_choice",
    "radio": "multiple_choice",
    "checkbox": "checkbox",
    "checkboxes": "checkbox",
    "dropdown": "dropdown",
    "linear scale": "linear_scale",
    "linear_scale": "linear_scale",
    "scale": "linear_scale",
    "date": "date",
    "time": "time",
    "multiple choice grid": "multiple_choice_grid",
    "multiple_choice_grid": "multiple_choice_grid",
    "checkbox grid": "checkbox_grid",
    "checkbox_grid": "checkbox_grid",
    "file upload": "file_upload",
    "file_upload": "file_upload",
    "rating": "rating",
}


def normalize_question_type(question_type: str) -> str:
    return _TYPE_ALIASES.get((question_type or "").strip().lower(), (question_type or "unknown").strip().lower())


def get_capability(question_type: str) -> str:
    normalized_type = normalize_question_type(question_type)
    for capability, question_types in CAPABILITY_MATRIX.items():
        if normalized_type in question_types:
            return capability
    return "unsupported"


class FormCopyPlanner:
    def build_plan(self, form: Form) -> CopyPlan:
        operations = [
            CopyOperation(
                kind="set_title_description",
                capability="supported",
                payload={"title": form.title, "description": form.description or ""},
            )
        ]
        warnings = []

        if form.response_config:
            for page in form.response_config.pages:
                for question in page.questions or []:
                    normalized_type = normalize_question_type(question.type)
                    capability = get_capability(normalized_type)
                    options = []
                    if question.answer_config and question.answer_config.options:
                        options = [option.text for option in question.answer_config.options]

                    operations.append(
                        CopyOperation(
                            kind="create_question",
                            capability=capability,
                            source_question_id=question.question_id,
                            source_question_text=question.text,
                            question_type=normalized_type,
                            payload={
                                "text": question.text,
                                "type": normalized_type,
                                "options": options,
                            },
                        )
                    )

                    if capability != "supported":
                        warnings.append(
                            CopyWarning(
                                code=f"{capability}_question_type",
                                message=f"Question type '{normalized_type}' is {capability} for no-login copy.",
                                question_id=question.question_id,
                                question_text=question.text,
                                capability=capability,
                            )
                        )

        return CopyPlan(
            source_form_id=form.id,
            source_title=form.title,
            source_description=form.description or "",
            operations=operations,
            warnings=warnings,
            capability_matrix=CAPABILITY_MATRIX,
        )

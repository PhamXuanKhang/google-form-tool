"""Gemini API key validation and AI text answer routes."""


from flask import jsonify, request

from app.logging_config import logger
from app.routes import bp, json_error
from app.services import get_storage_service, submission_manager


@bp.route('/validate_api_key', methods=['POST'])
def validate_api_key():
    """
    Validate Gemini API Key

    POST /validate_api_key
    - Tests if the provided API key is valid
    """
    data = request.get_json()
    api_key = data.get('api_key')

    if not api_key:
        return jsonify({"valid": False, "error": "No API key provided"}), 400

    try:
        from app.adapters.ai.ai_responder import AIResponder, is_ai_available, ModelResolutionError
        if not is_ai_available():
            return jsonify({
                "valid": False,
                "error": "AI dependency is not installed. Run uv sync (or uv pip install google-genai).",
                "code": "ai_dependency_missing",
            }), 400

        try:
            responder = AIResponder(api_key)
        except ModelResolutionError as e:
            logger.warning("API key validation failed: %s", str(e))
            return jsonify({
                "valid": False,
                "error": str(e),
                "code": "model_unavailable",
            }), 400

        is_valid = responder.validate_api_key()
        if not is_valid:
            return jsonify({
                "valid": False,
                "error": "API key validation failed.",
                "code": "invalid_api_key",
            }), 400

        return jsonify({
            "valid": True,
            "message": "API key is valid",
        })

    except Exception as e:
        logger.error("API key validation error: %s", type(e).__name__)
        return jsonify({"valid": False, "error": "API key validation failed."}), 400


MAX_AUDIENCE_CHARS = 2000


def _ai_error(message, code, status):
    return jsonify({"error": message, "code": code}), status


def _current_settings(question):
    config = question.answer_config
    if not config:
        return {}
    current = {"fill_percentage": config.fill_percentage}
    if config.options:
        current["options"] = [{"text": option.text, "percentage": option.percentage} for option in config.options]
    if config.answers:
        current["answers"] = list(config.answers[:20])
    return current


@bp.route('/ai/propose_config', methods=['POST'])
def ai_propose_config():
    """
    AI Autopilot: propose answer settings (and optionally personas) for a whole form.

    POST /ai/propose_config
    Body: form_id, api_key, audience (up to 2000 characters), want_personas
    Returns the checked proposal with before/after per question. Nothing is
    saved; applying goes through /save_edit and /forms/<id>/personas.
    """
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    api_key = data.get('api_key')
    audience = data.get('audience')
    want_personas = data.get('want_personas') is True

    if not form_id or not api_key:
        return _ai_error("form_id and api_key are required", "missing_fields", 400)
    if not isinstance(audience, str) or not audience.strip():
        return _ai_error("Describe who answers the form.", "missing_audience", 400)
    if len(audience) > MAX_AUDIENCE_CHARS:
        return _ai_error(f"The description is limited to {MAX_AUDIENCE_CHARS} characters.", "audience_too_long", 400)

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
    if not form:
        return _ai_error("Form not found", "form_not_found", 404)

    from app.adapters.ai.ai_responder import AIResponder, ModelResolutionError, is_ai_available
    from app.domain.autopilot_proposal import ProposalError, validate_proposal

    if not is_ai_available():
        return _ai_error("AI dependency is not installed. Run uv sync (or uv pip install google-genai).",
                         "ai_dependency_missing", 400)
    try:
        responder = AIResponder(api_key)
        raw = responder.propose_form_config(form, audience.strip(), want_personas)
        proposal = validate_proposal(form, raw, want_personas)
    except ModelResolutionError as e:
        return _ai_error(str(e), "model_unavailable", 400)
    except TimeoutError:
        return _ai_error("AI request timed out", "ai_timeout", 504)
    except ProposalError as e:
        return _ai_error(str(e), e.code, 422)
    except ValueError as e:
        if str(e) == "Input too large":
            return _ai_error("This form is too large to send to the AI in one request.", "prompt_too_large", 400)
        return _ai_error("The AI answer was not valid JSON.", "invalid_ai_response", 422)
    except Exception as e:
        # Never echo the API key into logs or the response.
        logger.error("AI Autopilot failed for form %s: %s", form_id, type(e).__name__)
        return _ai_error("Failed to get an AI proposal", "ai_failed", 500)

    questions = {
        question.question_id: question
        for page in (form.response_config.pages if form.response_config else [])
        for question in page.questions or []
    }
    return jsonify({
        "success": True,
        "questions": [
            {"question_id": question_id, "text": questions[question_id].text, "type": questions[question_id].type,
             "before": _current_settings(questions[question_id]), "after": edit}
            for question_id, edit in proposal["edits"].items()
        ],
        "edits": proposal["edits"],
        "personas": proposal["personas"],
        "warnings": proposal["warnings"],
    })


@bp.route('/generate_ai_text_answers', methods=['POST'])
def generate_ai_text_answers():
    """
    Inline AI text generation for one text-like question (TIP-006).

    POST /generate_ai_text_answers
    Body: form_id, question_id, api_key, count (1-500)
    Returns: { success: True, answers: [str, ...] }
    """
    data = request.get_json() or {}
    form_id = data.get('form_id')
    question_id = data.get('question_id')
    api_key = data.get('api_key')

    try:
        count = int(data.get('count', 1))
    except (TypeError, ValueError):
        return jsonify({"error": "count must be an integer"}), 400

    if not form_id or not question_id or not api_key:
        return jsonify({
            "error": "form_id, question_id and api_key are required"
        }), 400
    if count < 1 or count > submission_manager.MAX_SUBMISSIONS_PER_BATCH:
        return jsonify({
            "error": f"count must be between 1 and {submission_manager.MAX_SUBMISSIONS_PER_BATCH}"
        }), 400

    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404

            question = None
            for page in (form.response_config.pages or []):
                for q in (page.questions or []):
                    if q.question_id == question_id:
                        question = q
                        break
                if question:
                    break

            if not question:
                return jsonify({"error": f"Question '{question_id}' not found"}), 404

            if question.type not in ("input_text", "textarea"):
                return jsonify({
                    "error": (
                        f"AI generation is only supported for input_text or "
                        f"textarea questions; got '{question.type}'."
                    )
                }), 400

            from app.adapters.ai.ai_responder import AIResponder, is_ai_available
            if not is_ai_available():
                return jsonify({
                    "error": "AI not available. Install google-generativeai."
                }), 400

            responder = AIResponder(api_key)
            answers = responder.generate_text_variations(
                question, count, context=form.title
            )
            return jsonify({"success": True, "answers": answers})

    except ValueError as e:
        return json_error(str(e), 400)
    except TimeoutError:
        return json_error("AI request timed out", 504)
    except Exception as e:
        # Never echo api_key into logs/response.
        logger.error("Error generating AI text answers for question %s: %s", question_id, type(e).__name__)
        return jsonify({"error": "Failed to generate AI answers"}), 500

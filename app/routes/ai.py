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
        from app.core.ai_responder import AIResponder, is_ai_available, ModelResolutionError
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

            from app.core.ai_responder import AIResponder, is_ai_available
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

"""Persona routes: read and replace a form's personas."""

from flask import jsonify, request

from app.domain.personas import validate_personas
from app.logging_config import logger
from app.routes import bp, json_error
from app.services import get_storage_service


def _dump(personas):
    return [persona.model_dump(mode="json") for persona in personas or []]


@bp.route('/forms/<form_id>/personas', methods=['GET'])
def get_personas(form_id):
    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
    if not form:
        return json_error("Form not found", 404)
    return jsonify({"success": True, "personas": _dump(form.personas)})


@bp.route('/forms/<form_id>/personas', methods=['POST'])
def set_personas(form_id):
    """Replace the whole persona list. An empty list removes personas."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "personas" not in data:
        return json_error("Send {\"personas\": [...]}.")
    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
        if not form:
            return json_error("Form not found", 404)
        try:
            personas = validate_personas(form, data["personas"])
        except ValueError as e:
            return json_error(str(e))
        if not storage.update_personas(form_id, personas):
            logger.error("Failed to save personas for form_id=%s", form_id)
            return json_error("Could not save personas.", 500)
    return jsonify({"success": True, "personas": _dump(personas)})

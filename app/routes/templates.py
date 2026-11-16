"""Distribution presets and answer-configuration templates."""

import json
import re

from flask import Response, jsonify, request

from app.domain.config_template import build_template, match_template, parse_template
from app.domain.distribution_presets import PRESET_TYPES, preset_table
from app.domain.form_processor import FormProcessor
from app.logging_config import logger
from app.routes import bp, json_error
from app.services import get_storage_service, get_template_store

_TEMPLATE_ID = re.compile(r"^[0-9a-f]{32}$")
MAX_PRESET_OPTIONS = 100


@bp.route('/presets', methods=['GET'])
def presets():
    """Percentages of every preset available for a question type and option count."""
    question_type = request.args.get('type', '')
    raw_count = request.args.get('options', '')
    if not raw_count.isdigit() or not 1 <= int(raw_count) <= MAX_PRESET_OPTIONS:
        return json_error(f"options must be an integer from 1 to {MAX_PRESET_OPTIONS}.")
    if question_type not in PRESET_TYPES:
        return json_error(f"Presets apply to: {', '.join(sorted(PRESET_TYPES))}.")
    return jsonify({"success": True, "type": question_type, "presets": preset_table(int(raw_count), question_type)})


@bp.route('/forms/<form_id>/config/export', methods=['GET'])
def export_config(form_id):
    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
    if not form:
        return json_error("Form not found", 404)
    template = build_template(form, request.args.get('name'))
    response = Response(json.dumps(template, indent=2, ensure_ascii=False), mimetype='application/json')
    response.headers['Content-Disposition'] = f'attachment; filename=config_{form_id}.json'
    return response


def _template_from_request():
    """Read the template from an uploaded file, a JSON body, or a saved template id."""
    if 'file' in request.files:
        raw = request.files['file'].read()
        try:
            return json.loads(raw.decode('utf-8-sig')), request.form.get('apply') in ('true', '1')
        except (UnicodeDecodeError, ValueError):
            raise ValueError("The file is not valid JSON.")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Send a template file, a template object, or a template_id.")
    apply = data.get('apply') is True
    if data.get('template_id'):
        template_id = str(data['template_id'])
        record = get_template_store().get(template_id) if _TEMPLATE_ID.match(template_id) else None
        if not record:
            raise LookupError("Template not found")
        record.pop("template_id", None)
        return record, apply
    return data.get('template'), apply


@bp.route('/forms/<form_id>/config/import', methods=['POST'])
def import_config(form_id):
    """Preview a template against a form; apply the matching questions when apply is true."""
    try:
        raw, apply = _template_from_request()
        template = parse_template(raw)
    except LookupError as e:
        return json_error(str(e), 404)
    except ValueError as e:
        return json_error(str(e))

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
        if not form:
            return json_error("Form not found", 404)
        preview = match_template(form, template)
        edits = preview.pop("edits")
        if apply and edits:
            FormProcessor(form).apply_user_edits(edits)
            if not storage.save_form(form):
                logger.error("Failed to save imported configuration for form_id=%s", form_id)
                return json_error("Could not save form configuration.", 500)
    return jsonify({"success": True, "applied": bool(apply and edits), "preview": preview})


@bp.route('/templates', methods=['GET'])
def list_templates():
    templates = [
        {
            "template_id": record["template_id"],
            "name": record.get("name"),
            "created_at": record.get("created_at"),
            "question_count": len(record.get("questions") or []),
        }
        for record in get_template_store().list()
    ]
    return jsonify({"success": True, "templates": templates})


@bp.route('/templates', methods=['POST'])
def save_template():
    """Save a form's current answer configuration as a named template."""
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    name = data.get('name')
    if not form_id:
        return json_error("No form_id provided")
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        return json_error("Give the template a name of 1 to 200 characters.")
    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
    if not form:
        return json_error("Form not found", 404)
    record = get_template_store().save(build_template(form, name.strip()))
    return jsonify({"success": True, "template_id": record["template_id"], "name": record["name"]})


@bp.route('/templates/<template_id>/delete', methods=['POST'])
def delete_template(template_id):
    if not _TEMPLATE_ID.match(template_id) or not get_template_store().delete(template_id):
        return json_error("Template not found", 404)
    return jsonify({"success": True})

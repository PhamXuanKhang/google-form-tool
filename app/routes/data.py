"""Answer data upload and form edit routes."""


from flask import current_app, jsonify, request

from app.logging_config import logger
from app.routes import bp, json_error
from app.services import get_storage_service, upload_cache
from config import Config


@bp.route('/load_data', methods=['POST'])
def load_data():
    """
    Load Data File

    POST /load_data
    - Uploads CSV/JSON file and returns parsed response rows
    - Each row becomes one submission's responses
    """
    form_id = request.form.get('form_id')
    if not form_id:
        return json_error("No form_id provided", 400)

    max_upload_bytes = current_app.config.get('MAX_CONTENT_LENGTH') or Config.MAX_UPLOAD_BYTES
    if request.content_length and request.content_length > max_upload_bytes:
        return json_error(f"Uploaded file exceeds maximum size of {max_upload_bytes} bytes", 413)

    if 'answer_file' not in request.files:
        return json_error("No file uploaded", 400)

    file = request.files['answer_file']
    if file.filename == '':
        return json_error("No selected file", 400)

    import os
    import tempfile
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in ('.csv', '.json', '.xlsx'):
        return json_error("Unsupported file format. Use CSV, JSON, or XLSX", 400)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        file_path = tmp.name
        file.save(file_path)

    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return json_error("Form not found", 404)

            from app.core.form_processor import FormProcessor
            processor = FormProcessor(form)

            mapping = None
            mapping_json = request.form.get('mapping')
            if mapping_json:
                import json
                mapping = json.loads(mapping_json)

            responses_list = processor.load_data_from_file(file_path, mapping, max_rows=Config.MAX_UPLOAD_ROWS)
            upload_id = upload_cache.store_uploaded_responses(responses_list)
            if not upload_id:
                return json_error("Upload cache full", 503)

            return jsonify({
                "success": True,
                "upload_id": upload_id,
                "row_count": len(responses_list),
                "rows_loaded": len(responses_list),
                "preview": responses_list[:5],
                "message": f"Loaded {len(responses_list)} response sets"
            })

    except FileNotFoundError as e:
        return json_error(str(e), 404)
    except ValueError as e:
        return json_error(str(e), 400)
    except Exception:
        logger.exception("Unexpected error loading data")
        return json_error("An unexpected error occurred", 500)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@bp.route('/save_edit', methods=['POST'])
def save_edit():
    """
    Save Edited Form Configuration

    POST /save_edit
    - Applies user edits to a form and saves it
    """
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    edits = data.get('edits', {})
    
    if not form_id:
        return jsonify({"error": "No form ID provided."}), 400
    if not edits:
        return jsonify({"error": "No manual configuration changes were provided."}), 400
    
    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404
            
            from app.core.form_processor import FormProcessor
            processor = FormProcessor(form)
            processor.apply_user_edits(edits)
            
            if not storage.save_form(form):
                logger.error("Failed to save edited form configuration for form_id=%s", form_id)
                return jsonify({"error": "Could not save form configuration."}), 500
            
            return jsonify({
                "success": True,
                "message": "Form configuration saved successfully"
            })
    
    except Exception:
        logger.exception("Error saving form configuration for form_id=%s", form_id)
        return jsonify({"error": "Error saving form configuration."}), 500

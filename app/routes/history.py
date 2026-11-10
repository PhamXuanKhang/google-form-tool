"""Submission history and export routes."""

from flask import Response, jsonify, request

from app.logging_config import logger
from app.routes import bp
from app.services import get_storage_service, history_export


@bp.route('/submission_history/<form_id>', methods=['GET'])
def submission_history(form_id):
    """
    Submission History

    GET /submission_history/<form_id>
    - Returns saved submission history for one form as JSON
    """
    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return jsonify({"error": "Form not found. Please refresh the page and try again."}), 404

            submissions = [
                {
                    "submission_id": sub.submission_id,
                    "num_submission": sub.num_submission,
                    "concurrent_thread": sub.concurrent_thread,
                    "time_used": sub.time_used,
                    "success_rate": sub.success_rate,
                    "network_status": sub.network_status,
                }
                for sub in (form.submissions or [])
            ]

            return jsonify({
                "success": True,
                "form_id": form.id,
                "title": form.title,
                "submissions": submissions,
            })

    except Exception as e:
        logger.error(f"Error getting submission history for {form_id}: {e}")
        return jsonify({"error": "Could not load submission history. Please try again."}), 500


@bp.route('/export_history/<form_id>', methods=['GET'])
def export_history(form_id):
    """
    Export Submission History

    GET /export_history/<form_id>?format=csv|json
    - Exports submission history for a form
    - Default format: csv
    """
    export_format = request.args.get('format', 'csv').lower()

    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404

            submissions = form.submissions or []

            if export_format == 'json':
                body, mimetype, extension = history_export.submissions_to_json(submissions), 'application/json', 'json'
            else:
                body, mimetype, extension = history_export.submissions_to_csv(submissions), 'text/csv', 'csv'

            response = Response(response=body, status=200, mimetype=mimetype)
            response.headers['Content-Disposition'] = f'attachment; filename=submissions_{form_id}.{extension}'
            return response

    except Exception:
        logger.exception("Unexpected error exporting history")
        return jsonify({"error": "An unexpected error occurred"}), 500

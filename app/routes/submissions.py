"""Start, stop and status routes for form submissions."""


from flask import jsonify, request

from app.core.driver_manager import get_chrome_binary, get_chromedriver_path
from app.logging_config import logger
from app.routes import bp, json_error
from app.services import get_storage_service, submission_manager, upload_cache
from app.config import Config


@bp.route('/start_submission', methods=['POST'])
def start_submission():
    """
    Start Form Submission

    POST /start_submission
    - Begins automated form submissions in background threads
    - Supports concurrent submissions for different forms
    - Accepts optional responses_list for data-driven submission
    """
    from app.core.form_submitter import (
        SUBMISSION_MODE_PREFILL,
        VALID_SUBMISSION_MODES,
    )

    data = request.get_json(silent=True) or {}

    form_id = data.get('form_id')
    upload_id = data.get('upload_id')
    responses_list = data.get('responses_list')
    responses = data.get('responses')
    use_file_data = data.get('use_file_data', False)
    use_ai_responses = data.get('use_ai_responses', False)
    submission_mode = data.get('submission_mode') or SUBMISSION_MODE_PREFILL

    logger.info(
        "Received start_submission request: form_id=%s mode=%s requested_total=%s",
        form_id,
        submission_mode,
        data.get('num_submissions'),
    )

    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400

    if submission_mode not in VALID_SUBMISSION_MODES:
        return jsonify({
            "error": (
                f"Unknown submission_mode '{submission_mode}'. "
                f"Expected one of: {list(VALID_SUBMISSION_MODES)}"
            )
        }), 400

    if upload_id:
        responses_list = upload_cache.get_cached_upload(upload_id)
        if responses_list is None:
            return json_error("Upload expired or not found. Please re-upload.", 400)

    try:
        num_submissions, concurrent_threads, min_delay, max_delay = submission_manager.validate_submission_request(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    submission_manager.cleanup_finished_submitters()

    with submission_manager.active_submitters_lock:
        current_submitter = submission_manager.active_submitters.get(form_id)
        if current_submitter and current_submitter.get_status().get("running", False):
            return jsonify({"error": "A submission is already running for this form."}), 409

    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404

            from app.core.form_submitter import FormSubmitter

            submitter = FormSubmitter(
                form=form,
                chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
                chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
                headless=True
            )
            with submission_manager.active_submitters_lock:
                submission_manager.active_submitters[form_id] = submitter

            prepared_count = num_submissions
            skipped_summary = {}
            debug_prefill_sample = None
            if submission_mode == SUBMISSION_MODE_PREFILL:
                prepared_count, skipped_summary, debug_prefill_sample = submitter.prepare_prefill_queue(
                    num_submissions=num_submissions,
                    responses=responses,
                    responses_list=responses_list,
                    include_debug_sample=Config.PREFILL_DEBUG_SAMPLE,
                )

            warnings = submission_manager.format_skipped_type_warning(skipped_summary)

            logger.info(
                "Start submission: form_id=%s mode=%s total=%s skipped=%s",
                form_id,
                submission_mode,
                prepared_count,
                skipped_summary or "none",
            )

            import threading
            submission_thread = threading.Thread(
                target=submission_manager.run_submission,
                args=(submitter, form_id, num_submissions, concurrent_threads, min_delay, max_delay, responses_list, responses, submission_mode, upload_id)
            )
            submission_thread.daemon = True
            submission_thread.start()

            if use_file_data:
                mode = "data-driven"
            elif use_ai_responses:
                mode = "AI-generated"
            else:
                mode = "random"

            response_body = {
                "success": True,
                "message": f"Started {prepared_count} form submissions ({mode} mode) with {concurrent_threads} threads",
                "submission_mode": submission_mode,
                "prepared_count": prepared_count,
                "warnings": warnings,
            }
            if debug_prefill_sample:
                response_body["debug_prefill_sample"] = debug_prefill_sample

            return jsonify(response_body)

    except Exception:
        logger.exception("Unexpected error starting submission")
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route('/stop_submission', methods=['POST'])
def stop_submission():
    """
    Stop Form Submission

    POST /stop_submission
    - Stops submission for a specific form (pass form_id in body)
    - If no form_id provided, stops all active submissions
    """
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')

    if form_id:
        with submission_manager.active_submitters_lock:
            submitter = submission_manager.active_submitters.get(form_id)
        if not submitter:
            return jsonify({"success": False, "message": f"No active submission for form {form_id}"})
        try:
            submitter.stop()
            return jsonify({"success": True, "message": f"Submission for form {form_id} stopped"})
        except Exception as e:
            return jsonify({"error": f"Error stopping submission: {str(e)}"}), 500
    else:
        with submission_manager.active_submitters_lock:
            submitters = list(submission_manager.active_submitters.values())
        stopped = 0
        for sub in submitters:
            if sub.get_status().get("running", False):
                sub.stop()
                stopped += 1
        return jsonify({"success": True, "message": f"Stopped {stopped} active submission(s)"})


@bp.route('/submission_status', methods=['GET'])
def submission_status():
    """
    Submission Status

    GET /submission_status?form_id=xxx
    - Returns the current status of form submission for a specific form
    - If no form_id provided, returns status of all active submissions
    """
    form_id = request.args.get('form_id')

    if form_id:
        with submission_manager.active_submitters_lock:
            submitter = submission_manager.active_submitters.get(form_id)
        if not submitter:
            return jsonify({"running": False, "message": f"No submission for form {form_id}"})
        return jsonify(submitter.get_status())
    else:
        submission_manager.cleanup_finished_submitters()
        with submission_manager.active_submitters_lock:
            submitters = dict(submission_manager.active_submitters)
        all_status = {fid: sub.get_status() for fid, sub in submitters.items()}
        return jsonify({"active_submissions": all_status, "count": len(all_status)})

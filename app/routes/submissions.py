"""Start, stop and status routes for form submissions."""


from flask import jsonify, request

from app.adapters.browser.driver_manager import get_chrome_binary, get_chromedriver_path
import random

from app.domain.drip_schedule import build_schedule
from app.domain.personas import persona_targets
from app.domain.response_plan import build_plan, target_snapshot
from app.logging_config import logger
from app.routes import bp, json_error
from app.services import get_run_store, get_storage_service, submission_manager, upload_cache
from app.services.drip_runner import DripRunner, utc_now, window_end_for
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
    from app.adapters.browser.form_submitter import (
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
        seed = submission_manager.parse_seed(data.get('seed'))
        window_seconds = submission_manager.parse_schedule(data.get('schedule'))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    submission_manager.cleanup_finished_submitters()

    if submission_manager.form_has_running_submission(form_id):
        return jsonify({"error": "A submission is already running for this form."}), 409

    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404

            from app.adapters.browser.form_submitter import FormSubmitter

            plan = build_plan(
                form,
                num_submissions,
                seed=seed,
                mode=submission_mode,
                responses_list=responses_list,
                responses=responses,
            )
            submitter = FormSubmitter(
                form=form,
                chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
                chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
                headless=True
            )
            submitter.plan = plan

            # Build prefill links before recording the run, so a form that
            # cannot be prefilled fails here without leaving a pending run.
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

            rows = [row.to_dict() for row in plan.rows]
            # Uploaded or fixed answers ignore personas, so only planned persona rows get a breakdown.
            extra = {"personas": persona_targets(form)} if any(row.persona_id for row in plan.rows) else {}
            runner = None
            if window_seconds is not None:
                start = utc_now()
                times = build_schedule(len(rows), start, window_seconds, random.Random(f"{plan.seed}:schedule"))
                for row, when in zip(rows, times):
                    row["due_at"] = when.isoformat()
                extra["schedule"] = {
                    "window_seconds": window_seconds,
                    "window_end": window_end_for(start, window_seconds).isoformat(),
                }
            try:
                def create_run():
                    return get_run_store().create_run(
                        form_id=form_id,
                        mode=submission_mode,
                        seed=plan.seed,
                        threads=concurrent_threads,
                        min_delay=min_delay,
                        max_delay=max_delay,
                        rows=rows,
                        target_snapshot=target_snapshot(form),
                        extra=extra or None,
                    )
                if window_seconds is not None:
                    runner = DripRunner(store=get_run_store(), header={}, send_batch=lambda rows, cb: None)
                    run = submission_manager.register_run(form_id, runner, create_run)
                    try:
                        runner.header = run
                        runner.load()
                        runner.send_batch = submission_manager.send_batch_factory(form, run)
                    except Exception:
                        runner.abandon()
                        raise
                else:
                    run = submission_manager.register_run(form_id, submitter, create_run)
            except submission_manager.RunAlreadyActive:
                return jsonify({"error": "A submission is already running for this form."}), 409

            warnings = submission_manager.format_skipped_type_warning(skipped_summary)

            logger.info(
                "Start submission: form_id=%s mode=%s total=%s skipped=%s",
                form_id,
                submission_mode,
                prepared_count,
                skipped_summary or "none",
            )

            if runner is not None:
                upload_cache.delete_cached_upload(upload_id)
                submission_manager.start_drip_thread(form, runner)
            else:
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
                "run_id": run["run_id"],
                "seed": plan.seed,
            }
            if debug_prefill_sample:
                response_body["debug_prefill_sample"] = debug_prefill_sample
            if window_seconds is not None:
                response_body["schedule"] = run["schedule"]

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


def _status_with_run(submitter):
    status = submitter.get_status()
    run_id = getattr(submitter, "run_id", None)
    if run_id:
        status["run_id"] = run_id
    return status


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
        return jsonify(_status_with_run(submitter))
    else:
        submission_manager.cleanup_finished_submitters()
        with submission_manager.active_submitters_lock:
            submitters = dict(submission_manager.active_submitters)
        all_status = {fid: _status_with_run(sub) for fid, sub in submitters.items()}
        return jsonify({"active_submissions": all_status, "count": len(all_status)})

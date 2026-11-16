"""Simulation before a run, and reports, exports and retries after it.

``/simulate`` only plans: it never creates a browser driver and never writes
to the run store.
"""

from flask import Response, abort, jsonify, render_template, request

from app.domain.response_plan import PLAN_MODE_PREFILL, PlanRow, ResponsePlan, build_plan
from app.domain.run_report import retry_candidates, summarize_plan, summarize_run
from app.logging_config import logger
from app.routes import bp, json_error
from app.services import get_run_store, get_storage_service, history_export, submission_manager, upload_cache
from app.services.run_store import ROW_IN_FLIGHT, ROW_RESULT_STATUSES, ROW_PLANNED, ROW_UNKNOWN, is_valid_run_id

SIMULATION_SAMPLE_ROWS = 20
ROWS_PAGE_DEFAULT = 50
ROWS_PAGE_MAX = 100
ROW_FILTERS = (ROW_PLANNED,) + ROW_RESULT_STATUSES


@bp.route('/simulate', methods=['POST'])
def simulate():
    """Plan a batch and summarize it without sending anything."""
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    if not form_id:
        return json_error("No form_id provided")
    submission_mode = data.get('submission_mode') or PLAN_MODE_PREFILL

    try:
        num_submissions, _threads, _min_delay, _max_delay = submission_manager.validate_submission_request(data)
        seed = submission_manager.parse_seed(data.get('seed'))
    except ValueError as e:
        return json_error(str(e))

    responses_list = None
    if data.get('upload_id'):
        responses_list = upload_cache.get_cached_upload(data['upload_id'])
        if responses_list is None:
            return json_error("Upload expired or not found. Please re-upload.")

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
    if not form:
        return json_error("Form not found", 404)

    try:
        plan = build_plan(form, num_submissions, seed=seed, mode=submission_mode, responses_list=responses_list)
    except ValueError as e:
        return json_error(str(e))

    summary = summarize_plan(form, plan)
    return jsonify({
        "success": True,
        "seed": plan.seed,
        "submission_mode": plan.mode,
        "total": summary["total"],
        "questions": summary["questions"],
        "skipped": summary["skipped"],
        "warnings": submission_manager.format_skipped_type_warning(summary["skipped"]),
        "sample_rows": [
            {"index": row.index, "answers": row.answers}
            for row in plan.rows[:SIMULATION_SAMPLE_ROWS]
        ],
    })


# ------------------------------------------------------------------ runs


def _load_run(run_id):
    """Return (header, rows) as currently known, or an error response.

    A run whose submitter is no longer running in this process cannot still
    be sending, so its in-flight rows are reported as unknown and an
    unfinished header as interrupted.
    """
    if not is_valid_run_id(run_id):
        return None, None, json_error("Invalid run id")
    store = get_run_store()
    header = store.get_run(run_id)
    if not header:
        return None, None, json_error("Run not found", 404)
    rows = store.load_rows(run_id)
    if run_id not in submission_manager.live_run_ids():
        for row in rows:
            if row["status"] == ROW_IN_FLIGHT:
                row["status"] = ROW_UNKNOWN
        if header.get("status") in ("pending", "running"):
            header["status"] = "interrupted"
    return header, rows, None


def _header_summary(header):
    return {key: value for key, value in header.items() if key != "target_snapshot"}


@bp.route('/runs', methods=['GET'])
def list_runs():
    form_id = request.args.get('form_id')
    if not form_id:
        return json_error("No form_id provided")
    live = submission_manager.live_run_ids()
    runs = []
    for header in get_run_store().list_runs(form_id):
        if header["run_id"] not in live and header.get("status") in ("pending", "running"):
            header["status"] = "interrupted"
        runs.append(_header_summary(header))
    return jsonify({"success": True, "form_id": form_id, "runs": runs})


@bp.route('/runs/<run_id>', methods=['GET'])
def run_detail(run_id):
    header, rows, error = _load_run(run_id)
    if error:
        return error
    form = None
    with get_storage_service() as storage:
        form = storage.get_form_by_id(header.get("form_id"))
    return jsonify({
        "success": True,
        "run": _header_summary(header),
        "form_title": form.title if form else None,
        "summary": summarize_run(form, header, rows),
    })


def _int_arg(name, default, minimum, maximum):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    if not raw.isdigit():
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}.")
    value = int(raw)
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}.")
    return value


@bp.route('/runs/<run_id>/rows', methods=['GET'])
def run_rows(run_id):
    header, rows, error = _load_run(run_id)
    if error:
        return error
    status = request.args.get('status') or None
    if status and status not in ROW_FILTERS:
        return json_error(f"status must be one of: {', '.join(ROW_FILTERS)}")
    sort = request.args.get('sort') or "index"
    if sort not in ("index", "recent"):
        return json_error("sort must be index or recent")
    try:
        offset = _int_arg('offset', 0, 0, 10 ** 6)
        limit = _int_arg('limit', ROWS_PAGE_DEFAULT, 1, ROWS_PAGE_MAX)
    except ValueError as e:
        return json_error(str(e))

    if status:
        rows = [row for row in rows if row["status"] == status]
    if sort == "recent":
        rows = sorted(
            (row for row in rows if row.get("finished_at") or row.get("started_at")),
            key=lambda row: row.get("finished_at") or row.get("started_at"),
            reverse=True,
        )
    return jsonify({
        "success": True,
        "run_id": run_id,
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "rows": rows[offset:offset + limit],
    })


@bp.route('/runs/<run_id>/export', methods=['GET'])
def export_run(run_id):
    header, rows, error = _load_run(run_id)
    if error:
        return error
    export_format = (request.args.get('format') or 'csv').lower()
    if export_format not in ('csv', 'json'):
        return json_error("format must be csv or json")

    if export_format == 'json':
        body, mimetype = history_export.run_to_json(_header_summary(header), rows), 'application/json'
    else:
        body = history_export.run_rows_to_csv(header.get("target_snapshot") or {}, rows)
        mimetype = 'text/csv'
    response = Response(response=body, status=200, mimetype=mimetype)
    response.headers['Content-Disposition'] = f'attachment; filename=run_{run_id}.{export_format}'
    return response


@bp.route('/runs/<run_id>/retry', methods=['POST'])
def retry_run(run_id):
    """Start a new run that resends the failed rows of a run and its retries."""
    data = request.get_json(silent=True) or {}
    include_unknown = data.get('include_unknown') is True

    header, _rows, error = _load_run(run_id)
    if error:
        return error
    root_id = header.get("retry_of") or run_id
    root, root_rows, error = _load_run(root_id)
    if error:
        return error
    form_id = root["form_id"]
    if submission_manager.form_has_running_submission(form_id):
        return json_error("A submission is already running for this form.", 409)

    store = get_run_store()
    retries = sorted(
        (run for run in store.list_runs(form_id) if run.get("retry_of") == root_id),
        key=lambda run: run.get("created_at") or "",
    )
    family = [root_rows] + [_load_run(run["run_id"])[1] or [] for run in retries]
    candidates = retry_candidates(family, include_unknown=include_unknown)
    if not candidates:
        return json_error("No responses to send again.")

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)
    if not form:
        return json_error("Form not found", 404)

    plan = ResponsePlan(
        seed=root["seed"],
        mode=root["mode"],
        rows=[PlanRow(index=row["index"], answers=row["answers"], skipped=row["skipped"]) for row in candidates],
    )
    try:
        new_run = submission_manager.launch_planned_run(
            form, plan, root.get("threads") or 1, root.get("min_delay") or 0, root.get("max_delay") or 0,
            retry_of=root_id, snapshot=root.get("target_snapshot"),
        )
    except submission_manager.RunAlreadyActive:
        return json_error("A submission is already running for this form.", 409)
    except Exception:
        logger.exception("Unexpected error retrying run %s", run_id)
        return json_error("An unexpected error occurred", 500)

    return jsonify({
        "success": True,
        "run_id": new_run["run_id"],
        "retry_of": root_id,
        "total": len(plan.rows),
    })


@bp.route('/runs/<run_id>/view', methods=['GET'])
def run_view(run_id):
    if not is_valid_run_id(run_id) or not get_run_store().get_run(run_id):
        abort(404)
    return render_template('run_report.html', run_id=run_id, active_page="home")

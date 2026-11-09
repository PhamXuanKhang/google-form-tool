"""Registry of running form submitters and the background submission worker."""

import threading
import time

from app.logging_config import logger
from app.services import get_storage_service, upload_cache


active_submitters: dict = {}
active_submitters_lock = threading.RLock()
MAX_SUBMISSIONS_PER_BATCH = 500
MAX_CONCURRENT_THREADS = 10
FINISHED_STATUS_TTL = 60  # seconds to retain final status after submission ends


def _parse_integer_field(value, field_label, minimum, maximum):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field_label} must be an integer from {minimum} to {maximum}.")

    if isinstance(value, str):
        value = value.strip()
        if not value.isdigit():
            raise ValueError(f"{field_label} must be an integer from {minimum} to {maximum}.")
        value = int(value)
    elif isinstance(value, int):
        pass
    else:
        raise ValueError(f"{field_label} must be an integer from {minimum} to {maximum}.")

    if value < minimum or value > maximum:
        raise ValueError(f"{field_label} must be between {minimum} and {maximum}.")

    return value


def _parse_delay_field(value, field_label):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field_label} must be a non-negative number.")

    try:
        delay = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_label} must be a non-negative number.")

    if delay < 0:
        raise ValueError(f"{field_label} must be a non-negative number.")

    return delay


def validate_submission_request(data):
    num_submissions = _parse_integer_field(
        data.get('num_submissions', 1),
        "Number of submissions",
        1,
        MAX_SUBMISSIONS_PER_BATCH
    )
    concurrent_threads = _parse_integer_field(
        data.get('concurrent_threads', 1),
        "Concurrent threads",
        1,
        MAX_CONCURRENT_THREADS
    )

    if concurrent_threads > num_submissions:
        raise ValueError("Concurrent threads cannot be greater than the number of submissions.")

    min_delay = _parse_delay_field(data.get('min_delay', 1), "Minimum delay")
    max_delay = _parse_delay_field(data.get('max_delay', 5), "Maximum delay")

    if max_delay < min_delay:
        raise ValueError("Maximum delay must be greater than or equal to minimum delay.")

    return num_submissions, concurrent_threads, min_delay, max_delay


def cleanup_finished_submitters():
    """Remove finished submitters whose final-status TTL has expired."""
    now = time.monotonic()
    with active_submitters_lock:
        finished = [
            fid for fid, sub in active_submitters.items()
            if not sub.get_status().get("running", False)
            and (now - getattr(sub, "_finished_at", 0)) > FINISHED_STATUS_TTL
        ]
        for fid in finished:
            del active_submitters[fid]


def format_skipped_type_warning(skipped_summary):
    if not skipped_summary:
        return []
    parts = [f"{k} ({v})" for k, v in sorted(skipped_summary.items())]
    return [f"Skipping unsupported question types in prefill mode: {', '.join(parts)}."]


def run_submission(submitter, form_id, num_submissions, concurrent_threads, min_delay, max_delay, responses_list=None, responses=None, submission_mode=None, upload_id=None):
    """Internal helper: Runs submission in background thread"""
    try:
        submit_kwargs = dict(
            num_submissions=num_submissions,
            responses_list=responses_list,
            responses=responses,
            concurrent_threads=concurrent_threads,
            min_delay=min_delay,
            max_delay=max_delay,
        )
        if submission_mode is not None:
            submit_kwargs["submission_mode"] = submission_mode
        submission_result = submitter.submit_form(**submit_kwargs)

        try:
            with get_storage_service() as storage:
                saved = storage.add_submission(form_id, submission_result)
                if saved:
                    logger.info(f"Saved submission history for form {form_id}")
                else:
                    logger.warning(f"Submission history was not saved because form {form_id} was not found")
        except Exception as e:
            logger.error(f"Failed to save submission history for form {form_id}: {str(e)}")

        logger.info(f"Submission complete: {submission_result.success_rate}% success rate")

    except Exception as e:
        logger.error(f"Error in submission thread: {str(e)}")
    finally:
        upload_cache.delete_cached_upload(upload_id)
        submitter._finished_at = time.monotonic()

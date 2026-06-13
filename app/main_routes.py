"""
Main Routes Module

This module defines the main routes (API endpoints + UI pages) for the 
Google Form Automation Tool. Each section is grouped and separated 
for easier navigation and documentation.
"""

import os
import sys
import threading
import time
import uuid
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, session, jsonify, current_app, Response
from app.services import get_storage_service
from datetime import datetime
from app.core import FormExtractor
from app.core.form_copy_planner import FormCopyPlanner
from app.core.form_copier import FormCopier, is_google_form_edit_url
from app.core.form_extractor import DriverStartupError, FormExtractionError, FormLoadError
from app.core.driver_manager import get_chrome_binary, get_chromedriver_path, get_driver_diagnostics
from app.logging_config import logger
from config import Config

# Create blueprint
bp = Blueprint('main', __name__)

_upload_cache = {}
_upload_cache_lock = threading.RLock()


def _json_error(message: str, code: int = 400):
    return jsonify({"error": message}), code


def _same_origin_host(header_value: str) -> str:
    """Extract netloc (host:port) from an Origin or Referer header value."""
    try:
        return urlparse(header_value).netloc
    except Exception:
        return ""


@bp.before_request
def _check_same_origin():
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return None
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return None
    if _same_origin_host(origin) != request.host:
        return jsonify({"error": "Forbidden"}), 403
    return None


def _is_valid_google_forms_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    if url != url.strip():
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return (
        parsed.scheme == 'https'
        and parsed.hostname == 'docs.google.com'
        and parsed.path.startswith('/forms/d/')
    )


def _cleanup_expired_upload_cache(now: float = None) -> None:
    now = now or time.monotonic()
    ttl = Config.UPLOAD_CACHE_TTL_SECONDS
    with _upload_cache_lock:
        expired_ids = [
            upload_id
            for upload_id, entry in _upload_cache.items()
            if now - entry["created_at"] > ttl
        ]
        for upload_id in expired_ids:
            _upload_cache.pop(upload_id, None)


def _store_uploaded_responses(responses_list):
    _cleanup_expired_upload_cache()
    with _upload_cache_lock:
        if len(_upload_cache) >= Config.UPLOAD_CACHE_MAX_ENTRIES:
            return None
        upload_id = uuid.uuid4().hex[:12]
        while upload_id in _upload_cache:
            upload_id = uuid.uuid4().hex[:12]
        _upload_cache[upload_id] = {
            "responses": responses_list,
            "created_at": time.monotonic(),
        }
        return upload_id


def _get_cached_upload(upload_id: str):
    _cleanup_expired_upload_cache()
    with _upload_cache_lock:
        entry = _upload_cache.get(upload_id)
        if not entry:
            return None
        return entry["responses"]


def _delete_cached_upload(upload_id: str) -> None:
    if not upload_id:
        return
    with _upload_cache_lock:
        _upload_cache.pop(upload_id, None)


#############################
#      Home & Static UI     #
#############################

@bp.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"status": "ok"})


def _runtime_mode() -> str:
    if os.getenv("GOOGLE_FORM_TOOL_ELECTRON") == "1":
        return "electron"
    if getattr(sys, "frozen", False):
        return "frozen"
    return "dev"


def _runtime_diagnostics() -> dict:
    diagnostics = get_driver_diagnostics()
    return {
        "app_data_path": Config.APP_DATA_PATH,
        "db_path": Config.DB_PATH,
        "log_path": Config.LOG_DIR,
        "chrome_path": get_chrome_binary(Config.CHROME_BINARY_PATH),
        "chromedriver_path": get_chromedriver_path(Config.CHROME_DRIVER_PATH, allow_download=False),
        "mode": _runtime_mode(),
        **diagnostics,
    }


@bp.route('/diagnostics/runtime', methods=['GET'])
def runtime_diagnostics():
    return jsonify(_runtime_diagnostics())


@bp.route('/', methods=['GET'])
def index():
    """
    Home Page

    - Displays recent forms
    - Allows searching and deleting forms
    """
    query = request.args.get('search', '').lower().strip()

    with get_storage_service() as storage:
        recent_forms = storage.get_all_forms_summary()
    
    recent_forms = [
        {**form, 'created_at': datetime.fromisoformat(form['created_at']).strftime('%d/%m/%Y %H:%M')}
        for form in recent_forms
    ]
    
    if query:
        recent_forms = [
            form for form in recent_forms
            if query in form.get('title', '').lower() or query in form.get('description', '').lower()
        ]

    return render_template('index.html',
                           recent_forms=recent_forms,
                           active_page="home")


@bp.route('/forms/delete', methods=['POST'])
def delete_form():
    data = request.get_json(silent=True) or {}
    form_url = data.get('form_url', '')
    if not isinstance(form_url, str) or not form_url.strip():
        return jsonify({"error": "No form URL provided"}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url.strip())
        if not form:
            return jsonify({"error": "Form not found"}), 404
        storage.delete_form(form.id)

    return jsonify({"success": True})


@bp.route('/form_filling', methods=['GET', 'POST'])
def form_filling():
    """
    Form Filling Page

    - Renders UI for filling forms
    """
    return render_template(
        'form_filling.html',
        active_page="form_filling"
    )


@bp.route('/about', methods=['GET'])
def about():
    """
    About Page

    - Displays information about the tool
    """
    return render_template('about.html', active_page="about")


@bp.route('/settings/diagnostics', methods=['GET'])
def settings_diagnostics():
    return render_template(
        'settings_diagnostics.html',
        active_page="settings_diagnostics",
        diagnostics=_runtime_diagnostics(),
    )


@bp.route('/form_copy', methods=['GET'])
def form_copy():
    return render_template('form_copy.html', active_page="form_copy")


def _is_google_form_url(form_url: str) -> bool:
    return isinstance(form_url, str) and form_url.startswith('https://docs.google.com/forms/')


def _extract_or_load_form(form_url: str):
    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)
        if form:
            return form

        form_extractor = FormExtractor(
            chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
            chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
            headless=True,
        )
        form = form_extractor.extract_form_data(form_url)
        storage.save_form(form)
        return form


@bp.route('/form_copy/extract_source', methods=['POST'])
def form_copy_extract_source():
    data = request.get_json(silent=True) or {}
    form_url = data.get('form_url')
    if not form_url:
        return jsonify({"error": "No form URL provided"}), 400
    if not _is_google_form_url(form_url):
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400

    try:
        form = _extract_or_load_form(form_url)
    except ValueError as e:
        logger.warning(f"Invalid Google Form URL: {form_url}. Details: {str(e)}")
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400
    except DriverStartupError as e:
        logger.exception(f"Chrome/ChromeDriver startup failed while extracting source form: {e}")
        return jsonify({
            "error": (
                "Chrome or ChromeDriver could not start. Please check that Chrome is installed, "
                "ChromeDriver is available, and the runtime diagnostics paths are writable."
            ),
            "diagnostics": _runtime_diagnostics(),
        }), 500
    except FormLoadError as e:
        logger.exception(f"Google Form load/parse failed: {e}")
        return jsonify({"error": "The Google Form could not be loaded or parsed."}), 500
    except FormExtractionError as e:
        logger.exception(f"Unknown form extraction failure: {e}")
        return jsonify({"error": "The form could not be extracted because of an unexpected extraction error."}), 500
    except Exception as e:
        logger.exception(f"Unexpected source form extraction failure: {e}")
        return jsonify({"error": "The form could not be extracted because of an unknown error."}), 500

    return jsonify({
        "success": True,
        "form": {
            "id": form.id,
            "title": form.title,
            "description": form.description,
            "url": str(form.url),
        },
    })


@bp.route('/form_copy/preview_plan', methods=['POST'])
def form_copy_preview_plan():
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)

    if not form:
        return jsonify({"error": "Form not found"}), 404

    plan = FormCopyPlanner().build_plan(form)
    return jsonify({"success": True, "plan": plan.model_dump(mode="json")})


@bp.route('/form_copy/apply_to_target', methods=['POST'])
def form_copy_apply_to_target():
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    target_url = data.get('target_url')
    ownership_confirmed = data.get('ownership_confirmed') is True

    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400
    if not target_url:
        return jsonify({"error": "No target edit URL provided"}), 400
    if not is_google_form_edit_url(target_url):
        return jsonify({"error": "Please enter a valid Google Forms edit URL."}), 400
    if not ownership_confirmed:
        return jsonify({"error": "Please confirm you own or control the target form before applying changes."}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)

    if not form:
        return jsonify({"error": "Form not found"}), 404

    plan = FormCopyPlanner().build_plan(form)
    copier = FormCopier(
        chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
        chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
        headless=True,
    )
    result = copier.apply_plan(plan, target_url)
    status_code = 200 if result.status in ("success", "partial") else 500
    return jsonify({"success": result.status in ("success", "partial"), "result": result.model_dump(mode="json")}), status_code
#############################
##### Extract & Preview #####
#############################
@bp.route('/form_filling/extract', methods=['POST'])
def extract():
    """
    Extract Form Data

    POST /extract
    - Extracts form structure from a Google Form URL
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
        
    form_url = data.get('form_url')
    if not form_url:
        return jsonify({"error": "No form URL provided"}), 400
    if not isinstance(form_url, str):
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400
    form_url = form_url.strip()
    if not _is_valid_google_forms_url(form_url):
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400
        
    session['form_url'] = form_url

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)
        if not form:
            form_extractor = FormExtractor(
                chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
                chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
                headless=True
            )
            try:
                form = form_extractor.extract_form_data(form_url)
                storage.save_form(form)
            except ValueError as e:
                logger.warning(f"Invalid Google Form URL: {form_url}. Details: {str(e)}")
                return jsonify({"error": "Please enter a valid Google Form URL."}), 400
            except DriverStartupError as e:
                logger.exception(f"Chrome/ChromeDriver startup failed while extracting form: {e}")
                return jsonify({
                    "error": (
                        "Chrome or ChromeDriver could not start. Please check that Chrome is installed, "
                        "ChromeDriver is available, and the runtime diagnostics paths are writable."
                    ),
                    "diagnostics": _runtime_diagnostics(),
                }), 500
            except FormLoadError as e:
                logger.exception(f"Google Form load/parse failed: {e}")
                return jsonify({
                    "error": (
                        "The Google Form could not be loaded or parsed. Please check that the form URL "
                        "opens in a browser and the form is accessible."
                    )
                }), 500
            except FormExtractionError as e:
                logger.exception(f"Unknown form extraction failure: {e}")
                return jsonify({
                    "error": "The form could not be extracted because of an unexpected extraction error."
                }), 500
            except Exception as e:
                logger.exception(f"Unexpected form extraction failure: {e}")
                return jsonify({
                    "error": "The form could not be extracted because of an unknown error."
                }), 500
            
    return jsonify({"success": True, "message": "Form extracted successfully"})


@bp.route('/form_filling/preview', methods=['GET'])
def preview():
    """
    Preview Extracted Form

    GET /form_filling/preview
    - Returns the extracted form data stored in session
    """
    form_url = session.get('form_url')
    if not form_url:
        return jsonify({"error": "No form URL provided"}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)

    if not form:
        return jsonify({"error": "No data found for this form"}), 404

    return jsonify(form.model_dump(mode='json'))


#############################
###### Data Processing ######
#############################

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
        return _json_error("No form_id provided", 400)

    max_upload_bytes = current_app.config.get('MAX_CONTENT_LENGTH') or Config.MAX_UPLOAD_BYTES
    if request.content_length and request.content_length > max_upload_bytes:
        return _json_error(f"Uploaded file exceeds maximum size of {max_upload_bytes} bytes", 413)

    if 'answer_file' not in request.files:
        return _json_error("No file uploaded", 400)

    file = request.files['answer_file']
    if file.filename == '':
        return _json_error("No selected file", 400)

    import os
    import tempfile
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in ('.csv', '.json', '.xlsx'):
        return _json_error("Unsupported file format. Use CSV, JSON, or XLSX", 400)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        file_path = tmp.name
        file.save(file_path)

    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return _json_error("Form not found", 404)

            from app.core.form_processor import FormProcessor
            processor = FormProcessor(form)

            mapping = None
            mapping_json = request.form.get('mapping')
            if mapping_json:
                import json
                mapping = json.loads(mapping_json)

            responses_list = processor.load_data_from_file(file_path, mapping, max_rows=Config.MAX_UPLOAD_ROWS)
            upload_id = _store_uploaded_responses(responses_list)
            if not upload_id:
                return _json_error("Upload cache full", 503)

            return jsonify({
                "success": True,
                "upload_id": upload_id,
                "row_count": len(responses_list),
                "rows_loaded": len(responses_list),
                "preview": responses_list[:5],
                "message": f"Loaded {len(responses_list)} response sets"
            })

    except FileNotFoundError as e:
        return _json_error(str(e), 404)
    except ValueError as e:
        return _json_error(str(e), 400)
    except Exception as e:
        logger.exception("Unexpected error loading data")
        return _json_error("An unexpected error occurred", 500)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@bp.route('/generate_response', methods=['POST'])
def generate_response():
    """
    Generate Responses

    POST /generate_response
    - Generates random or AI-driven responses for a form
    - Set use_ai=true and provide api_key for AI mode
    """
    data = request.get_json()
    form_id = data.get('form_id')
    fill_percentage = data.get('fill_percentage', 100)
    use_ai = data.get('use_ai', False)
    api_key = data.get('api_key')

    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400

    try:
        with get_storage_service() as storage:
            form = storage.get_form_by_id(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404

            if use_ai and api_key:
                from app.core.ai_responder import AIResponder, is_ai_available
                if not is_ai_available():
                    return jsonify({"error": "AI not available. Install google-generativeai package."}), 400

                responder = AIResponder(api_key)
                questions = []
                for page in (form.response_config.pages or []):
                    questions.extend(page.questions or [])
                responses = responder.generate_responses_batch(questions, context=form.title)
                mode = "ai"
            else:
                from app.core.form_processor import FormProcessor
                processor = FormProcessor(form)
                responses = processor.generate_random_responses(fill_percentage)
                mode = "random"

            return jsonify({
                "success": True,
                "form_id": form_id,
                "mode": mode,
                "responses": responses
            })

    except Exception as e:
        logger.exception("Unexpected error generating responses")
        return jsonify({"error": "An unexpected error occurred"}), 500


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
                "error": "AI dependency is not installed. Run pip install -r requirements.txt.",
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
    if count < 1 or count > MAX_SUBMISSIONS_PER_BATCH:
        return jsonify({
            "error": f"count must be between 1 and {MAX_SUBMISSIONS_PER_BATCH}"
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
        return _json_error(str(e), 400)
    except TimeoutError:
        return _json_error("AI request timed out", 504)
    except Exception as e:
        # Never echo api_key into logs/response.
        logger.error("Error generating AI text answers for question %s: %s", question_id, type(e).__name__)
        return jsonify({"error": "Failed to generate AI answers"}), 500


@bp.route('/ai_status', methods=['GET'])
def ai_status():
    """
    Check AI Availability

    GET /ai_status
    - Returns whether AI functionality is available
    """
    from app.core.ai_responder import is_ai_available
    return jsonify({
        "available": is_ai_available(),
        "message": "AI available" if is_ai_available() else "Install google-generativeai package"
    })


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
    
    except Exception as e:
        logger.exception("Error saving form configuration for form_id=%s", form_id)
        return jsonify({"error": "Error saving form configuration."}), 500


#############################
###### Form Submission ######
#############################

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


def _validate_submission_request(data):
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


def _cleanup_finished_submitters():
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


def _format_skipped_type_warning(skipped_summary):
    if not skipped_summary:
        return []
    parts = [f"{k} ({v})" for k, v in sorted(skipped_summary.items())]
    return [f"Skipping unsupported question types in prefill mode: {', '.join(parts)}."]


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
        responses_list = _get_cached_upload(upload_id)
        if responses_list is None:
            return _json_error("Upload expired or not found. Please re-upload.", 400)

    try:
        num_submissions, concurrent_threads, min_delay, max_delay = _validate_submission_request(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    _cleanup_finished_submitters()

    with active_submitters_lock:
        current_submitter = active_submitters.get(form_id)
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
            with active_submitters_lock:
                active_submitters[form_id] = submitter

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

            warnings = _format_skipped_type_warning(skipped_summary)

            logger.info(
                "Start submission: form_id=%s mode=%s total=%s skipped=%s",
                form_id,
                submission_mode,
                prepared_count,
                skipped_summary or "none",
            )

            import threading
            submission_thread = threading.Thread(
                target=_run_submission,
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

    except Exception as e:
        logger.exception("Unexpected error starting submission")
        return jsonify({"error": "An unexpected error occurred"}), 500


def _run_submission(submitter, form_id, num_submissions, concurrent_threads, min_delay, max_delay, responses_list=None, responses=None, submission_mode=None, upload_id=None):
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
        _delete_cached_upload(upload_id)
        submitter._finished_at = time.monotonic()


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
        with active_submitters_lock:
            submitter = active_submitters.get(form_id)
        if not submitter:
            return jsonify({"success": False, "message": f"No active submission for form {form_id}"})
        try:
            submitter.stop()
            return jsonify({"success": True, "message": f"Submission for form {form_id} stopped"})
        except Exception as e:
            return jsonify({"error": f"Error stopping submission: {str(e)}"}), 500
    else:
        with active_submitters_lock:
            submitters = list(active_submitters.values())
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
        with active_submitters_lock:
            submitter = active_submitters.get(form_id)
        if not submitter:
            return jsonify({"running": False, "message": f"No submission for form {form_id}"})
        return jsonify(submitter.get_status())
    else:
        _cleanup_finished_submitters()
        with active_submitters_lock:
            submitters = dict(active_submitters)
        all_status = {fid: sub.get_status() for fid, sub in submitters.items()}
        return jsonify({"active_submissions": all_status, "count": len(all_status)})


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
                import json
                data = [s.model_dump() for s in submissions]
                response = Response(
                    response=json.dumps(data, indent=2, default=str),
                    status=200,
                    mimetype='application/json'
                )
                response.headers['Content-Disposition'] = f'attachment; filename=submissions_{form_id}.json'
                return response

            else:  # CSV
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)

                # Header
                writer.writerow(['submission_id', 'num_submission', 'concurrent_thread',
                               'time_used', 'success_rate', 'network_status'])

                # Data rows
                for sub in submissions:
                    writer.writerow([
                        sub.submission_id,
                        sub.num_submission,
                        sub.concurrent_thread,
                        sub.time_used,
                        sub.success_rate,
                        sub.network_status
                    ])

                response = Response(
                    response=output.getvalue(),
                    status=200,
                    mimetype='text/csv'
                )
                response.headers['Content-Disposition'] = f'attachment; filename=submissions_{form_id}.csv'
                return response

    except Exception as e:
        logger.exception("Unexpected error exporting history")
        return jsonify({"error": "An unexpected error occurred"}), 500


#############################
###### System Monitoring ####
#############################

@bp.route('/system_status', methods=['GET'])
def system_status():
    """
    System Status

    GET /system_status
    - Returns live system monitoring metrics
    """
    try:
        from app.monitoring.metrics_collector import MetricsCollector
        collector = MetricsCollector.get_instance()
        if not collector.is_running:
            collector.start()
        
        return jsonify(collector.get_system_status())
    
    except Exception as e:
        logger.exception("Unexpected error getting system status")
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route('/monitoring_history', methods=['GET'])
def monitoring_history():
    """
    Monitoring History

    GET /monitoring_history?duration=<seconds>
    - Returns historical monitoring data
    """
    try:
        from app.monitoring.metrics_collector import MetricsCollector
        duration = request.args.get('duration')
        if duration:
            duration = int(duration)
        
        collector = MetricsCollector.get_instance()
        history = collector.get_historical_metrics(duration)
        return jsonify(history)
    
    except Exception as e:
        logger.exception("Unexpected error getting monitoring history")
        return jsonify({"error": "An unexpected error occurred"}), 500


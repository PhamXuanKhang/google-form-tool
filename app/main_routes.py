"""
Main Routes Module

This module defines the main routes (API endpoints + UI pages) for the 
Google Form Automation Tool. Each section is grouped and separated 
for easier navigation and documentation.
"""

from flask import Blueprint, render_template, request, session, jsonify, current_app, Response
from app.services import get_storage_service
from datetime import datetime
from app.core import FormExtractor
from app.core.form_extractor import DriverStartupError, FormExtractionError, FormLoadError
from app.logging_config import logger
from config import Config

# Create blueprint
bp = Blueprint('main', __name__)


#############################
#      Home & Static UI     #
#############################

@bp.route('/', methods=['GET'])
def index():
    """
    Home Page

    - Displays recent forms
    - Allows searching and deleting forms
    """
    query = request.args.get('search', '').lower().strip()
    delete_form_url = request.args.get('form_url', '').strip()

    with get_storage_service() as storage:
        if delete_form_url:
            del_form = storage.get_form_by_url(delete_form_url)
            storage.delete_form(del_form.id)
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
    if not isinstance(form_url, str) or not form_url.startswith('https://docs.google.com/forms/'):
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400
        
    session['form_url'] = form_url

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)
        if not form:
            form_extractor = FormExtractor(
                chromebinary_path=Config.CHROME_BINARY_PATH,
                chromedriver_path=Config.CHROME_DRIVER_PATH,
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
                        "Chrome or ChromeDriver could not start. Please check that Chrome is installed "
                        "and the ChromeDriver path is configured correctly."
                    )
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
        return jsonify({"error": "No form_id provided"}), 400

    if 'answer_file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['answer_file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    import os
    import tempfile
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in ('.csv', '.json', '.xlsx'):
        return jsonify({"error": "Unsupported file format. Use CSV, JSON, or XLSX"}), 400

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        file_path = tmp.name
        file.save(file_path)

    try:
        with get_storage_service() as storage:
            form = storage._load_form(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404

            from app.core.form_processor import FormProcessor
            processor = FormProcessor(form)

            mapping = None
            mapping_json = request.form.get('mapping')
            if mapping_json:
                import json
                mapping = json.loads(mapping_json)

            responses_list = processor.load_data_from_file(file_path, mapping)

            return jsonify({
                "success": True,
                "rows_loaded": len(responses_list),
                "responses": responses_list,
                "message": f"Loaded {len(responses_list)} response sets"
            })

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return jsonify({"error": f"Error loading data: {str(e)}"}), 500
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
            form = storage._load_form(form_id)
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
        logger.error(f"Error generating responses: {e}")
        return jsonify({"error": f"Error generating responses: {str(e)}"}), 500


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
        from app.core.ai_responder import AIResponder, is_ai_available
        if not is_ai_available():
            return jsonify({"valid": False, "error": "AI not available. Install google-generativeai."}), 400

        responder = AIResponder(api_key)
        is_valid = responder.validate_api_key()

        return jsonify({
            "valid": is_valid,
            "message": "API key is valid" if is_valid else "API key validation failed"
        })

    except Exception as e:
        logger.error(f"API key validation error: {e}")
        return jsonify({"valid": False, "error": str(e)}), 400


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
            form = storage._load_form(form_id)
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
MAX_SUBMISSIONS_PER_BATCH = 500
MAX_CONCURRENT_THREADS = 10


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
    """Remove submitters that are no longer running."""
    finished = [fid for fid, sub in active_submitters.items() if not sub.status.get("running", False)]
    for fid in finished:
        del active_submitters[fid]


@bp.route('/start_submission', methods=['POST'])
def start_submission():
    """
    Start Form Submission

    POST /start_submission
    - Begins automated form submissions in background threads
    - Supports concurrent submissions for different forms
    - Accepts optional responses_list for data-driven submission
    """
    data = request.get_json() or {}

    form_id = data.get('form_id')
    responses_list = data.get('responses_list')
    responses = data.get('responses')
    use_file_data = data.get('use_file_data', False)
    use_ai_responses = data.get('use_ai_responses', False)

    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400

    try:
        num_submissions, concurrent_threads, min_delay, max_delay = _validate_submission_request(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    _cleanup_finished_submitters()

    if form_id in active_submitters and active_submitters[form_id].status.get("running", False):
        active_submitters[form_id].stop()

    try:
        with get_storage_service() as storage:
            form = storage._load_form(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404

            from app.core.form_submitter import FormSubmitter

            submitter = FormSubmitter(
                form=form,
                chromebinary_path=Config.CHROME_BINARY_PATH,
                chromedriver_path=Config.CHROME_DRIVER_PATH,
                headless=True
            )
            active_submitters[form_id] = submitter

            import threading
            submission_thread = threading.Thread(
                target=_run_submission,
                args=(submitter, form_id, num_submissions, concurrent_threads, min_delay, max_delay, responses_list, responses)
            )
            submission_thread.daemon = True
            submission_thread.start()

            if use_file_data:
                mode = "data-driven"
            elif use_ai_responses:
                mode = "AI-generated"
            else:
                mode = "random"

            return jsonify({
                "success": True,
                "message": f"Started {num_submissions} form submissions ({mode} mode) with {concurrent_threads} threads"
            })

    except Exception as e:
        return jsonify({"error": f"Error starting submission: {str(e)}"}), 500


def _run_submission(submitter, form_id, num_submissions, concurrent_threads, min_delay, max_delay, responses_list=None, responses=None):
    """Internal helper: Runs submission in background thread"""
    try:
        submission_result = submitter.submit_form(
            num_submissions=num_submissions,
            responses_list=responses_list,
            responses=responses,
            concurrent_threads=concurrent_threads,
            min_delay=min_delay,
            max_delay=max_delay
        )

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


@bp.route('/stop_submission', methods=['POST'])
def stop_submission():
    """
    Stop Form Submission

    POST /stop_submission
    - Stops submission for a specific form (pass form_id in body)
    - If no form_id provided, stops all active submissions
    """
    data = request.get_json() or {}
    form_id = data.get('form_id')

    if form_id:
        if form_id not in active_submitters:
            return jsonify({"success": False, "message": f"No active submission for form {form_id}"})
        try:
            active_submitters[form_id].stop()
            return jsonify({"success": True, "message": f"Submission for form {form_id} stopped"})
        except Exception as e:
            return jsonify({"error": f"Error stopping submission: {str(e)}"}), 500
    else:
        stopped = 0
        for sub in active_submitters.values():
            if sub.status.get("running", False):
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
        if form_id not in active_submitters:
            return jsonify({"running": False, "message": f"No submission for form {form_id}"})
        return jsonify(active_submitters[form_id].get_status())
    else:
        _cleanup_finished_submitters()
        all_status = {fid: sub.get_status() for fid, sub in active_submitters.items()}
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
            form = storage._load_form(form_id)
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
            form = storage._load_form(form_id)
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
        logger.error(f"Error exporting history: {e}")
        return jsonify({"error": str(e)}), 500


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
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({"error": "Failed to get system status", "details": str(e)}), 500


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
        logger.error(f"Error getting monitoring history: {str(e)}")
        return jsonify({"error": "Failed to get monitoring history", "details": str(e)}), 500

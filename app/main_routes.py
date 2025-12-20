"""
Main Routes Module

This module defines the main routes (API endpoints + UI pages) for the 
Google Form Automation Tool. Each section is grouped and separated 
for easier navigation and documentation.
"""

from flask import Blueprint, render_template, request, session, jsonify
from app.services import get_storage_service
from datetime import datetime
from app.core import FormExtractor
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
            except Exception as e:
                logger.error(f"Form extraction failed: {str(e)}")
                return jsonify({"error": "Failed to extract form data"}), 500
            
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
    - Uploads and maps data file (CSV/Excel) to form fields
    """
    form_id = request.form.get('form_id')
    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400
    
    if 'data_file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['data_file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    mappings = {}
    for key, value in request.form.items():
        if key.startswith('mapping_'):
            field_id = key.replace('mapping_', '')
            mappings[field_id] = value
    
    file_path = f"temp_{form_id}_{file.filename}"
    file.save(file_path)
    
    try:
        with get_storage_service() as storage:
            form = storage._load_form(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404
            
            from app.core.form_processor import FormProcessor
            processor = FormProcessor(form)
            processor.load_data_from_file(file_path, mappings)
            
            return jsonify({
                "success": True,
                "data_loaded": True,
                "message": "Data loaded successfully"
            })
    
    except Exception as e:
        return jsonify({"error": f"Error loading data: {str(e)}"}), 500
    
    finally:
        import os
        if os.path.exists(file_path):
            os.remove(file_path)


@bp.route('/generate_response', methods=['POST'])
def generate_response():
    """
    Generate AI Responses

    POST /generate_response
    - Generates random/AI-driven responses for a form
    """
    data = request.get_json()
    form_id = data.get('form_id')
    fill_percentage = data.get('fill_percentage', 100)
    
    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400
    
    try:
        with get_storage_service() as storage:
            form = storage._load_form(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404
            
            from app.core.form_processor import FormProcessor
            processor = FormProcessor(form)
            responses = processor.generate_random_responses(fill_percentage)
            
            return jsonify({
                "success": True,
                "form_id": form_id,
                "responses": responses
            })
    
    except Exception as e:
        return jsonify({"error": f"Error generating responses: {str(e)}"}), 500


@bp.route('/save_edit', methods=['POST'])
def save_edit():
    """
    Save Edited Form Configuration

    POST /save_edit
    - Applies user edits to a form and saves it
    """
    data = request.get_json()
    form_id = data.get('form_id')
    edits = data.get('edits', {})
    
    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400
    if not edits:
        return jsonify({"error": "No edits provided"}), 400
    
    try:
        with get_storage_service() as storage:
            form = storage._load_form(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404
            
            from app.core.form_processor import FormProcessor
            processor = FormProcessor(form)
            processor.apply_user_edits(edits)
            
            storage.save_form(form)
            
            return jsonify({
                "success": True,
                "message": "Form configuration saved successfully"
            })
    
    except Exception as e:
        return jsonify({"error": f"Error saving form configuration: {str(e)}"}), 500


#############################
###### Form Submission ######
#############################

active_submitter = None

@bp.route('/start_submission', methods=['POST'])
def start_submission():
    """
    Start Form Submission

    POST /start_submission
    - Begins automated form submissions in background threads
    """
    global active_submitter
    data = request.get_json()
    
    form_id = data.get('form_id')
    num_submissions = data.get('num_submissions', 1)
    concurrent_threads = data.get('concurrent_threads', 1)
    min_delay = data.get('min_delay', 1)
    max_delay = data.get('max_delay', 5)
    
    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400
    
    if active_submitter and active_submitter.status["running"]:
        active_submitter.stop()
    
    try:
        with get_storage_service() as storage:
            form = storage._load_form(form_id)
            if not form:
                return jsonify({"error": "Form not found"}), 404
            
            from app.core.form_submitter import FormSubmitter
            
            active_submitter = FormSubmitter(
                form=form,
                chromebinary_path=r"D:\application\chrome-win64\chrome-win64\chrome.exe",
                chromedriver_path=r"D:\application\chromedriver-win64\chromedriver-win64\chromedriver.exe",
                headless=True
            )
            
            import threading
            submission_thread = threading.Thread(
                target=_run_submission,
                args=(active_submitter, form, storage, num_submissions, concurrent_threads, min_delay, max_delay)
            )
            submission_thread.daemon = True
            submission_thread.start()
            
            return jsonify({
                "success": True,
                "message": f"Started {num_submissions} form submissions with {concurrent_threads} concurrent threads"
            })
    
    except Exception as e:
        return jsonify({"error": f"Error starting submission: {str(e)}"}), 500


def _run_submission(submitter, form, storage, num_submissions, concurrent_threads, min_delay, max_delay):
    """Internal helper: Runs submission in background thread"""
    try:
        submission_result = submitter.submit_form(
            num_submissions=num_submissions,
            concurrent_threads=concurrent_threads,
            min_delay=min_delay,
            max_delay=max_delay
        )
        
        storage.add_submission(form.id, submission_result)
        logger.info(f"Submission complete: {submission_result.success_rate}% success rate")
    
    except Exception as e:
        logger.error(f"Error in submission thread: {str(e)}")


@bp.route('/stop_submission', methods=['POST'])
def stop_submission():
    """
    Stop Form Submission

    POST /stop_submission
    - Stops any active submission process
    """
    global active_submitter
    if not active_submitter:
        return jsonify({"success": False, "message": "No active submission to stop"})
    
    try:
        active_submitter.stop()
        return jsonify({"success": True, "message": "Submission stopped successfully"})
    except Exception as e:
        return jsonify({"error": f"Error stopping submission: {str(e)}"}), 500


@bp.route('/submission_status', methods=['GET'])
def submission_status():
    """
    Submission Status

    GET /submission_status
    - Returns the current status of form submission
    """
    global active_submitter
    if not active_submitter:
        return jsonify({"running": False, "message": "No submission has been started"})
    
    status = active_submitter.get_status()
    return jsonify(status)


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
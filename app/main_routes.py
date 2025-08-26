"""
Main Routes Module

This module defines the main routes for the Google Form Automation Tool.
"""
from flask import Blueprint, render_template, request, redirect, session, make_response, jsonify
from app.services import get_storage_service
from datetime import datetime
from app.core import FormExtractor

# Create blueprint
bp = Blueprint('main', __name__)

# Home page
@bp.route('/', methods=['GET'])
def index():
    """Render the home page"""
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

# Form Filling page
@bp.route('/form_filling', methods=['GET', 'POST'])
def form_filling():
    """Render the form filling page"""
    return render_template(
        'form_filling.html',
        active_page="form_filling"
    )

# About page
@bp.route('/about', methods=['GET'])
def about():
    """Render the about page"""
    return render_template('about.html', active_page="about")

# TODO: Add Function to search form
@bp.route('/search', methods=['GET'])
def search():
    """Return searched form"""
    pass

# Extract form data
@bp.route('/extract', methods=['POST'])
def extract():
    """Extract form data from a Google Form Url"""
    form_url = request.get_json().get('form_url')
    session['form_url'] = form_url

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)
        if not form:
            form_extractor = FormExtractor(chromebinary_path=r"D:\application\chrome-win64\chrome-win64\chrome.exe", chromedriver_path=r"D:\application\chromedriver-win64\chromedriver-win64\chromedriver.exe", headless=True)
            try:
                form = form_extractor.extract_form_data(form_url)
                storage.save_form(form)
            except:
                return make_response('Failed to extract form data', 500)
            
    return make_response('Form extracted successfully', 200)


@bp.route('/form_filling/preview', methods=['GET'])
def preview():
    form_url = session.get('form_url')
    if not form_url:
        return jsonify({"error": "No form URL provided"}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)

    if not form:
        return jsonify({"error": "No data found for this form"}), 404

    return jsonify(form.model_dump(mode='json'))






  
# Load data file
@bp.route('/load_data', methods=['POST'])
def load_data():
    """Load data from a file"""
    pass

# Generate AI response
@bp.route('/generate_response', methods=['POST'])
def generate_response():
    """Generate AI response"""
    pass

# Save editted form configuration
@bp.route('/save_edit', methods=['POST'])
def save_edit():
    """Get form configuration"""
    pass

# Start submission
@bp.route('/start_submission', methods=['POST'])
def start_submission():
    """Start submission"""
    pass

# Stop submission
@bp.route('/stop_submission', methods=['POST'])
def stop_submission():
    """Stop submission"""
    pass

# Submission status
@bp.route('/submission_status', methods=['GET'])
def submission_status():
    """Get submission status"""
    pass

@bp.route('/setlang')
def setlang():
    lang = request.args.get('lang', 'en')
    session['lang'] = lang
    return redirect(request.referrer)

def get_locale():
    lang = request.cookies.get('language')
    if lang in ['en', 'vi']:
        return lang

    return request.accept_languages.best_match(['en', 'vi'])

@bp.context_processor
def inject_locale():
    # This makes the function available directly, allowing you to call it in the template
    return {'get_locale': get_locale}

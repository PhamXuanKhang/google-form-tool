"""
Main Routes Module

This module defines the main routes for the Google Form Automation Tool.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, make_response
from app.services import storage_service

# Create blueprint
bp = Blueprint('main', __name__)

# Home page
@bp.route('/', methods=['GET'])
def index():
    """Render the home page"""
    # TODO: Implement logic to get recent forms from database
    recent_forms = storage_service.get_all_forms_summary()
        # {
        #     'id': 'abc123',
        #     'title': 'Feedback Form',
        #     'timestamp': '2025-06-07 14:20',
        #     'submissions': 12,
        #     'url': 'https://forms.gle/example1',
        #     'description': 'A feedback form for user experience.'
        # }

    return render_template('index.html', recent_forms=recent_forms, active_page="home")

# Form Filling page
@bp.route('/form_filling', methods=['GET'])
def form_filling():
    """Render the form filling page"""
    return render_template('form_filling.html', active_page="form_filling")

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
    pass

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
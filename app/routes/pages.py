"""HTML page routes."""

from datetime import datetime

from flask import render_template, request

from app.routes import bp
from app.routes.health import _runtime_diagnostics
from app.services import get_storage_service


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

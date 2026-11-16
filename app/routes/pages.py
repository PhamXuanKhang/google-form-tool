"""HTML page routes."""

import json
from datetime import datetime
from pathlib import Path

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


MCP_SERVER_NAME = "google-form-automation"
SKILL_PATH = Path(__file__).resolve().parents[2] / "skills" / "google-form-automation" / "SKILL.md"


def _quote_arg(value: str) -> str:
    return f'"{value}"' if any(ch in value for ch in ' \t"') else value


def _mcp_settings(diagnostics: dict) -> dict:
    """Ready-to-paste MCP configuration for Claude Desktop and Claude Code."""
    launch = diagnostics.get("mcp")
    if not launch:
        return None
    desktop = {"mcpServers": {MCP_SERVER_NAME: {"command": launch["command"], "args": launch["args"]}}}
    command_line = " ".join(_quote_arg(part) for part in [launch["command"], *launch["args"]])
    return {
        "available": launch.get("available", False),
        "desktop_json": json.dumps(desktop, indent=2),
        "claude_code": f"claude mcp add {MCP_SERVER_NAME} -- {command_line}",
    }


def _skill_text():
    try:
        return SKILL_PATH.read_text(encoding="utf-8")
    except OSError:
        return None


@bp.route('/settings/diagnostics', methods=['GET'])
def settings_diagnostics():
    diagnostics = _runtime_diagnostics()
    return render_template(
        'settings_diagnostics.html',
        active_page="settings_diagnostics",
        diagnostics=diagnostics,
        mcp=_mcp_settings(diagnostics),
        skill_text=_skill_text(),
    )


@bp.route('/form_copy', methods=['GET'])
def form_copy():
    return render_template('form_copy.html', active_page="form_copy")

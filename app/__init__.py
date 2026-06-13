"""
Flask Application Factory

This module provides the application factory pattern for creating a Flask app.
It handles configuration, logging initialization, and blueprint registration.
"""

import os

from flask import Flask, request, session

from app.logging_config import logger

from app.models import *
from app.main_routes import bp
from config import Config
from app.logging_config import init_app_logging

try:
    from flask_babel import Babel
    BABEL_AVAILABLE = True
except ImportError:
    BABEL_AVAILABLE = False

SUPPORTED_LANGUAGES = ["en", "vi"]

__version__ = "1.1.0"


def _warn_production_guardrails() -> None:
    if str(os.getenv("FLASK_DEBUG", "0")) == "1":
        logger.warning(
            "Running in DEBUG mode. Do not expose this application to public networks."
        )


def get_locale():
    """Get locale from session, query param, or Accept-Language header."""
    if "lang" in request.args:
        lang = request.args.get("lang")
        if lang in SUPPORTED_LANGUAGES:
            session["lang"] = lang
            return lang
    if "lang" in session:
        return session.get("lang")
    return request.accept_languages.best_match(SUPPORTED_LANGUAGES, default="en")


def create_app(testing: bool = False):
    """
    Create and configure a Flask application instance.

    Args:
        testing (bool): If True, use testing configuration (e.g., temp DB).

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["APP_VERSION"] = __version__
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_UPLOAD_BYTES

    if testing:
        app.config["TESTING"] = True

    init_app_logging(app)
    _warn_production_guardrails()

    if BABEL_AVAILABLE:
        app.config["BABEL_DEFAULT_LOCALE"] = "en"
        app.config["BABEL_SUPPORTED_LOCALES"] = SUPPORTED_LANGUAGES
        babel = Babel(app, locale_selector=get_locale)

    @app.context_processor
    def inject_globals():
        return {
            "current_locale": get_locale() if BABEL_AVAILABLE else "en",
            "supported_languages": SUPPORTED_LANGUAGES,
            "app_version": __version__,
        }

    app.register_blueprint(bp)

    return app
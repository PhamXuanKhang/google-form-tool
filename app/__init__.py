"""
Flask Application Factory

This module provides the application factory pattern for creating a Flask app.
It handles configuration, logging initialization, and blueprint registration.
"""

from flask import Flask

from app.models import *
from app.main_routes import bp
from config import Config
from app.logging_config import init_app_logging


def create_app():
    """
    Create and configure a Flask application instance.

    - Loads configuration from `Config`
    - Initializes application logging
    - Registers main blueprint (`bp`)

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize logging
    init_app_logging(app)
    
    # Register blueprint
    app.register_blueprint(bp)

    return app
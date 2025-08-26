from flask import Flask, request

from app.models import *
from app.main_routes import bp
from config import Config
from app.logging_config import init_app_logging

def create_app():
    """
    Create and configure the app
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # TODO: Add language setting: babel = Babel(app, locale_selector=get_locale)
    
    app.register_blueprint(bp)

    return app
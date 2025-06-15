from flask import Flask, request
from flask_babel import Babel

from app.models import Form
from app.services import StorageService

from app.main_routes import bp, get_locale
from config import Config
from app.logging_config import logger


def create_app():
    """
    Create and configure the app
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # TODO: Add language setting: babel = Babel(app, locale_selector=get_locale)
    
    app.register_blueprint(bp)
    
    return app
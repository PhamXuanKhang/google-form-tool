from flask import Flask, request
from flask_babel import Babel, _

from app.models import *
from app.services import StorageService

from app.main_routes import bp, get_locale
from config import Config
from app.logging_config import logger

babel = Babel()

def create_app():
    """
    Create and configure the app
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    babel.init_app(app, locale_selector=get_locale)

    # Inject _ into Jinja2
    @app.context_processor
    def inject_translation():
        return dict(_=_)

    # TODO: Add language setting: babel = Babel(app, locale_selector=get_locale)
    
    app.register_blueprint(bp)


    return app
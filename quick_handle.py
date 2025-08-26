from flask import Flask, request
from flask_babel import Babel

app = Flask(__name__)
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
ab = Babel(app)

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(['en', 'de'])
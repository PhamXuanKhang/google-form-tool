"""
logging_config.py

This module sets up basic logging configuration for the application.
It logs messages to the console (default behavior).

Usage:
    from logging_config import logger
    logger.info("App started successfully.")
"""

import logging

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.propagate = False
logger.handlers.clear()

# Define formatter
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Flask app integration
def init_app_logging(app):
    """
    Integrate this logger with a Flask app instance.
    """
    app.logger.handlers.clear()
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)
    app.logger.propagate = False

    logging.getLogger('werkzeug').handlers.clear()
    logging.getLogger('werkzeug').addHandler(console_handler)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('werkzeug').propagate = False
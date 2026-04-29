"""
logging_config.py

This module sets up application logging.
It logs messages to the console and to logs/app.log.

Usage:
    from logging_config import logger
    logger.info("App started successfully.")
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

CONSOLE_HANDLER_NAME = "google_form_console"
FILE_HANDLER_NAME = "google_form_file"
DEFAULT_LOG_DIR = Path.cwd() / "logs"
LOG_FILE_NAME = "app.log"

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.propagate = False

# Define formatter
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s",
    "%Y-%m-%d %H:%M:%S"
)


def _has_named_handler(target_logger, handler_name):
    return any(handler.name == handler_name for handler in target_logger.handlers)


def configure_logging(log_dir=None):
    """
    Configure console and file logging without duplicating handlers.
    """
    target_log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    target_log_dir.mkdir(parents=True, exist_ok=True)

    if not _has_named_handler(logger, CONSOLE_HANDLER_NAME):
        console_handler = logging.StreamHandler()
        console_handler.name = CONSOLE_HANDLER_NAME
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if not _has_named_handler(logger, FILE_HANDLER_NAME):
        file_handler = RotatingFileHandler(
            target_log_dir / LOG_FILE_NAME,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.name = FILE_HANDLER_NAME
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


configure_logging()

# Flask app integration
def init_app_logging(app):
    """
    Integrate this logger with a Flask app instance.
    """
    configure_logging(Path(app.root_path).parent / "logs")

    app.logger.handlers.clear()
    app.logger.handlers = list(logger.handlers)
    app.logger.setLevel(logger.level)
    app.logger.propagate = False

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers.clear()
    for handler in logger.handlers:
        werkzeug_logger.addHandler(handler)
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.propagate = False

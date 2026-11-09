"""Health and runtime diagnostics routes."""

import os
import sys

from flask import jsonify

from app.core.driver_manager import get_chrome_binary, get_chromedriver_path, get_driver_diagnostics
from app.routes import bp
from config import Config


@bp.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"status": "ok"})


def _runtime_mode() -> str:
    if os.getenv("GOOGLE_FORM_TOOL_ELECTRON") == "1":
        return "electron"
    if getattr(sys, "frozen", False):
        return "frozen"
    return "dev"


def _runtime_diagnostics() -> dict:
    diagnostics = get_driver_diagnostics()
    return {
        "app_data_path": Config.APP_DATA_PATH,
        "db_path": Config.DB_PATH,
        "log_path": Config.LOG_DIR,
        "chrome_path": get_chrome_binary(Config.CHROME_BINARY_PATH),
        "chromedriver_path": get_chromedriver_path(Config.CHROME_DRIVER_PATH, allow_download=False),
        "mode": _runtime_mode(),
        **diagnostics,
    }


@bp.route('/diagnostics/runtime', methods=['GET'])
def runtime_diagnostics():
    return jsonify(_runtime_diagnostics())

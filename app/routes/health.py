"""Health and runtime diagnostics routes."""

import os
import sys
from pathlib import Path

from flask import jsonify

from app import __version__
from app.adapters.browser.driver_manager import get_chrome_binary, get_chromedriver_path, get_driver_diagnostics
from app.routes import bp
from app.config import Config


@bp.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"status": "ok"})


def _runtime_mode() -> str:
    if os.getenv("GOOGLE_FORM_TOOL_ELECTRON") == "1":
        return "electron"
    if getattr(sys, "frozen", False):
        return "frozen"
    return "dev"


MCP_EXE_NAME = "GoogleFormToolMcp.exe"


def _mcp_launch() -> dict:
    """How an MCP client starts this app's MCP server on this machine."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve().parent / MCP_EXE_NAME
        return {"command": str(exe), "args": [], "available": exe.exists()}
    repo_root = Path(__file__).resolve().parents[2]
    return {
        "command": "uv",
        "args": ["run", "--directory", str(repo_root), "python", "-m", "app.mcp_server"],
        "available": True,
    }


def _runtime_diagnostics() -> dict:
    diagnostics = get_driver_diagnostics()
    return {
        "app_data_path": Config.APP_DATA_PATH,
        "db_path": Config.DB_PATH,
        "log_path": Config.LOG_DIR,
        "chrome_path": get_chrome_binary(Config.CHROME_BINARY_PATH),
        "chromedriver_path": get_chromedriver_path(Config.CHROME_DRIVER_PATH, allow_download=False),
        "mode": _runtime_mode(),
        "version": __version__,
        "mcp": _mcp_launch(),
        **diagnostics,
    }


@bp.route('/diagnostics/runtime', methods=['GET'])
def runtime_diagnostics():
    return jsonify(_runtime_diagnostics())

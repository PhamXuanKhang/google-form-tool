"""Application configuration module."""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_app_data_path() -> Path:
    base_path = Path(os.getenv("APPDATA") or Path.home())
    return base_path / "GoogleFormTool"


_APP_DATA = get_app_data_path()


def _load_or_create_secret_key() -> str:
    """Return a persistent SECRET_KEY stored in the user-data dir.

    Generates a new key on first run and caches it so sessions survive
    app restarts without requiring a .env file.
    """
    key_file = _APP_DATA / "secret_key"
    try:
        _APP_DATA.mkdir(parents=True, exist_ok=True)
        if key_file.exists():
            key = key_file.read_text(encoding="utf-8").strip()
            if key:
                return key
        key = secrets.token_hex(32)
        key_file.write_text(key, encoding="utf-8")
        return key
    except OSError:
        return secrets.token_hex(32)  # ephemeral fallback (e.g. read-only FS)


class Config:
    """Base configuration class for the Flask application."""

    APP_DATA_PATH = str(_APP_DATA)
    LOG_DIR = os.getenv("LOG_DIR") or str(_APP_DATA / "logs")
    DRIVERS_DIR = os.getenv("DRIVERS_DIR") or str(_APP_DATA / "drivers")

    # Session / CSRF protection — auto-generated and persisted on first run.
    SECRET_KEY = os.getenv("SECRET_KEY") or _load_or_create_secret_key()

    # TinyDB storage — defaults to %APPDATA%\GoogleFormTool\db.json.
    DB_PATH = os.getenv("DB_PATH") or str(_APP_DATA / "db.json")

    # Chrome paths — None means Selenium Manager auto-detects the driver.
    CHROME_BINARY_PATH = os.getenv("CHROME_BINARY_PATH")
    CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")

    TEST_GOOGLE_FORM_URL = os.getenv("TEST_GOOGLE_FORM_URL")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL")
    PREFILL_DEBUG_SAMPLE = os.getenv("PREFILL_DEBUG_SAMPLE", "0") == "1"

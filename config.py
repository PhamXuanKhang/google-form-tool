"""Application configuration module."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class for the Flask application.
    
    Attributes:
        SECRET_KEY: Secret key for session and CSRF protection.
        DB_PATH: Path to the database file.
    """
    
    SECRET_KEY = os.getenv("SECRET_KEY")
    DB_PATH = os.getenv("DB_PATH")
    CHROME_BINARY_PATH = os.getenv("CHROME_BINARY_PATH")
    CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")
    TEST_GOOGLE_FORM_URL = os.getenv("TEST_GOOGLE_FORM_URL")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL")
    PREFILL_DEBUG_SAMPLE = os.getenv("PREFILL_DEBUG_SAMPLE", "0") == "1"

"""
Application configuration module.

Loads environment variables from a .env file using `python-dotenv`, and defines a base configuration class for use across the Flask app.

Typical usage:
    from config import Config
"""

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Base configuration class for the Flask application.

    Attributes:
        SECRET_KEY (str): Secret key for session and CSRF protection.
        DB_PATH (str): Path to the database file (e.g., for SQLite).
    """

    # Security and internationalization
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Service/database configuration
    DB_PATH = os.getenv("DB_PATH")
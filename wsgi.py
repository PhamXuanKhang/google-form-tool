"""
WSGI entry point for the Flask application.

This script initializes the Flask app using the application factory `create_app`
and runs it on host 0.0.0.0 and port 5000.

Usage:
    # Development (Flask built-in server)
    python wsgi.py

    # Production (Waitress - Windows/Linux)
    python -m waitress --host=0.0.0.0 --port=5000 wsgi:app

    # Production (Gunicorn - Linux only)
    gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

Set FLASK_DEBUG=1 in .env to enable debug mode (default: off for security).
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=debug, host="0.0.0.0", port=port)
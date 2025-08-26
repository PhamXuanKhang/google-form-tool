"""
Entry point for the Flask application.

This script initializes the Flask app using the application factory `create_app` and runs it with debugging enabled on host 0.0.0.0 and port 5000.

Usage:
    python app.py
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
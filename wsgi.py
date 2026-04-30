"""
WSGI entry point for the Flask application.

Usage:
    python wsgi.py                                          # development
    python -m waitress --host=0.0.0.0 --port=5000 wsgi:app # production
    GoogleFormTool.exe                                      # frozen exe (uses waitress)
"""

import os
import sys
import threading
import webbrowser
from app import create_app

app = create_app()


def _open_browser(port: int) -> None:
    import time
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}")


def _show_startup_error(msg: str) -> None:
    """Show a native Windows error dialog; falls back to stderr."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, "Google Form Tool — Startup Error", 0x10)
    except Exception:
        print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    frozen = getattr(sys, "frozen", False)

    # Auto-open browser (skip in Flask debug mode — the reloader starts two processes)
    if not debug:
        threading.Thread(target=_open_browser, args=(port,), daemon=True).start()

    if frozen:
        # Frozen exe: use waitress (production-grade, bundled in the exe)
        try:
            from waitress import serve
            print(f"Google Form Tool v{app.config.get('APP_VERSION', '')} running at http://127.0.0.1:{port}")
            print("Press Ctrl+C to stop.")
            serve(app, host="127.0.0.1", port=port)
        except OSError as exc:
            _is_port_conflict = (
                getattr(exc, "errno", None) in (10048, 98)
                or "address already in use" in str(exc).lower()
            )
            if _is_port_conflict:
                _show_startup_error(
                    f"Port {port} is already in use.\n\n"
                    "Close any other running instance of Google Form Tool,\n"
                    f"or set a PORT environment variable to use a different port."
                )
            else:
                _show_startup_error(f"Server failed to start:\n\n{exc}")
    else:
        app.run(debug=debug, host="0.0.0.0", port=port)
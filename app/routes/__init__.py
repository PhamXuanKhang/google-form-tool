"""Route package.

All route modules share one blueprint so endpoint names stay ``main.*``.
"""
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

bp = Blueprint('main', __name__)


def json_error(message: str, code: int = 400):
    return jsonify({"error": message}), code


def _same_origin_host(header_value: str) -> str:
    """Extract netloc (host:port) from an Origin or Referer header value."""
    try:
        return urlparse(header_value).netloc
    except Exception:
        return ""


@bp.before_request
def _check_same_origin():
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return None
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return None
    if _same_origin_host(origin) != request.host:
        return jsonify({"error": "Forbidden"}), 403
    return None


from app.routes import health, pages, forms, data, ai, submissions, history  # noqa: E402,F401

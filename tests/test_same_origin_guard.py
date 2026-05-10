"""Tests for A-1: same-origin guard on mutating routes.

The guard runs via @bp.before_request and only checks POST/PUT/DELETE/PATCH.
- No Origin/Referer header → pass (local clients, curl, etc.)
- Origin/Referer host matches request.host → pass
- Origin/Referer host differs → 403 {"error": "Forbidden"}
- GET requests are never blocked regardless of Origin.
"""


def test_no_origin_passes(client):
    """Request with no Origin/Referer must not be blocked."""
    resp = client.post("/forms/delete", json={"form_url": "x"})
    assert resp.status_code != 403


def test_same_origin_passes(client):
    """Origin matching request.host (localhost) must pass."""
    resp = client.post(
        "/forms/delete",
        json={"form_url": "x"},
        headers={"Origin": "http://localhost"},
    )
    assert resp.status_code != 403


def test_cross_origin_blocked(client):
    """Origin from a different host must be blocked with 403."""
    resp = client.post(
        "/forms/delete",
        json={"form_url": "x"},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "Forbidden"


def test_referer_cross_origin_blocked(client):
    """Referer from a different host must also be blocked with 403."""
    resp = client.post(
        "/forms/delete",
        json={"form_url": "x"},
        headers={"Referer": "https://evil.example/attack"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "Forbidden"


def test_origin_takes_priority_over_referer(client):
    """When both Origin and Referer are present, Origin is evaluated."""
    resp = client.post(
        "/forms/delete",
        json={"form_url": "x"},
        headers={
            "Origin": "https://evil.example",
            "Referer": "http://localhost/page",
        },
    )
    assert resp.status_code == 403


def test_get_not_blocked(client):
    """GET requests must never be blocked even with a cross-origin header."""
    resp = client.get(
        "/",
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code != 403

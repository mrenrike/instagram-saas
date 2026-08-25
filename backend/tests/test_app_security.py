"""End-to-end checks on the app's middleware stack and admin auth."""
import pytest

from backend.tests.conftest import TEST_ADMIN_SECRET


# --- Item 18: security headers ------------------------------------------------
@pytest.mark.parametrize(
    "header,expected",
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
        ("Cross-Origin-Opener-Policy", "same-origin"),
        ("Cache-Control", "no-store"),
    ],
)
def test_security_headers_are_present(client, header, expected):
    assert client.get("/health").headers[header] == expected


def test_csp_is_restrictive(client):
    csp = client.get("/health").headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp


def test_permissions_policy_is_present(client):
    assert "geolocation=()" in client.get("/health").headers["Permissions-Policy"]


def test_hsts_is_sent_only_over_https(client):
    # The TestClient speaks http:// and TRUST_PROXY is off in tests.
    assert "Strict-Transport-Security" not in client.get("/health").headers


def test_hsts_is_sent_when_the_request_is_https(client, monkeypatch):
    from backend.main import app

    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "SecurityHeadersMiddleware":
            middleware.kwargs["trust_proxy"] = True

    # Rebuilding the stack is the only way to pick up the change on a running app.
    app.middleware_stack = app.build_middleware_stack()
    try:
        resp = client.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert "max-age=" in resp.headers["Strict-Transport-Security"]
    finally:
        for middleware in app.user_middleware:
            if middleware.cls.__name__ == "SecurityHeadersMiddleware":
                middleware.kwargs["trust_proxy"] = False
        app.middleware_stack = app.build_middleware_stack()


# --- Item 18/19: CORS ---------------------------------------------------------
def test_cors_allows_the_configured_origin(client):
    resp = client.get("/health", headers={"Origin": "http://localhost:8080"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:8080"


def test_cors_does_not_allow_an_arbitrary_origin(client):
    resp = client.get("/health", headers={"Origin": "https://evil.example"})
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example"
    assert resp.headers.get("access-control-allow-origin") != "*"


# --- Item 16: body size -------------------------------------------------------
def test_oversized_body_is_rejected(client, new_session, auth_headers):
    session, token = new_session()
    resp = client.post(
        f"/questionnaire/{session.session_id}",
        content=b"x" * (300 * 1024),
        headers={**auth_headers(token), "Content-Type": "application/json"},
    )
    assert resp.status_code == 413


# --- Item 6/10/11: admin authentication --------------------------------------
SESSION_UUID = "00000000-0000-4000-8000-000000000000"


def test_admin_retry_requires_authorization(client):
    assert client.post(f"/admin/retry/{SESSION_UUID}").status_code == 401


def test_admin_retry_rejects_a_wrong_secret(client):
    resp = client.post(
        f"/admin/retry/{SESSION_UUID}", headers={"Authorization": "Bearer wrong-secret"}
    )
    assert resp.status_code == 401


def test_admin_retry_accepts_the_secret_with_and_without_bearer(client, new_session):
    session, _ = new_session(payment_status="paid")
    for value in (TEST_ADMIN_SECRET, f"Bearer {TEST_ADMIN_SECRET}"):
        resp = client.post(
            f"/admin/retry/{session.session_id}", headers={"Authorization": value}
        )
        assert resp.status_code == 200, value


def test_admin_brute_force_is_rate_limited(client):
    codes = [
        client.post(
            f"/admin/retry/{SESSION_UUID}", headers={"Authorization": "Bearer wrong"}
        ).status_code
        for _ in range(8)
    ]
    assert 429 in codes


def test_admin_secret_is_not_in_the_error_body(client):
    resp = client.post(
        f"/admin/retry/{SESSION_UUID}", headers={"Authorization": "Bearer wrong"}
    )
    assert TEST_ADMIN_SECRET not in resp.text


# --- Item 11: endpoint rate limiting -----------------------------------------
def test_questionnaire_is_rate_limited(client, new_session, auth_headers):
    session, token = new_session()
    body = {
        "name": "Test User", "email": "t@example.com", "niche": "F", "goal": "G",
        "audience": "A", "tone": "T", "management_style": "solo",
    }
    codes = [
        client.post(
            f"/questionnaire/{session.session_id}", json=body, headers=auth_headers(token)
        ).status_code
        for _ in range(14)
    ]
    assert 429 in codes


# --- Item 17: minimal error surface ------------------------------------------
def test_pipeline_status_hides_the_raw_error(client, new_session, auth_headers):
    session, token = new_session(
        pipeline_status="error",
        pipeline_error="Traceback (most recent call last): access_token=EAAsecret123",
        pipeline_error_kind="graph_error",
    )
    resp = client.get(f"/pipeline/status/{session.session_id}", headers=auth_headers(token))

    assert resp.status_code == 200
    assert "EAAsecret123" not in resp.text
    assert "Traceback" not in resp.text
    assert resp.json()["error"] == "graph_error"
    assert resp.json()["error_message"]


def test_openapi_schema_is_not_public_in_production(monkeypatch):
    """The schema enumerates every route and parameter — not something to publish."""
    import importlib

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://front.example.com")
    from backend.config import get_config

    get_config.cache_clear()
    import backend.main as main_module

    importlib.reload(main_module)
    try:
        assert main_module.app.openapi_url is None
        assert main_module.app.docs_url is None
    finally:
        monkeypatch.undo()
        get_config.cache_clear()
        importlib.reload(main_module)

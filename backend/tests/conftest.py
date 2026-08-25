"""Shared test configuration.

Every required environment variable is set here, once, before ``backend`` is imported.
The values are deliberately *valid-shaped* (a real 32-byte key, an admin secret of the
required length) so the tests exercise the same validation production runs through.
"""
import base64
import os

import pytest

TEST_ENCRYPTION_KEY = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
TEST_ADMIN_SECRET = "test-admin-secret-with-enough-entropy-000"

_TEST_ENV = {
    "ENVIRONMENT": "test",
    "SESSION_ENCRYPTION_KEY": TEST_ENCRYPTION_KEY,
    "SESSIONS_DIR": "/tmp/test_sessions",
    "ALLOWED_ORIGINS": "http://localhost:8080",
    "FORCE_HTTPS": "false",
    "TRUST_PROXY": "false",
    "FRONTEND_BASE_URL": "https://front.example.com",
    "OPENPIX_APP_ID": "test_app_id",
    "OPENPIX_WEBHOOK_SECRET": "test_webhook_secret",
    "META_APP_ID": "x",
    "META_APP_SECRET": "x",
    "META_REDIRECT_URI": "https://api.example.com/oauth/callback",
    "ANTHROPIC_API_KEY": "x",
    "RESEND_API_KEY": "x",
    "ADMIN_EMAIL": "a@b.com",
    "ADMIN_SECRET": TEST_ADMIN_SECRET,
    "GOOGLE_SHEETS_ID": "sheet123",
    "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
    "AGENCY_NAME": "Ag",
    "AGENCY_LINK": "https://ag.com",
    "AGENCY_HANDLE": "@ag",
    "AGENCY_EMAIL": "ag@ag.com",
}

for _key, _value in _TEST_ENV.items():
    os.environ[_key] = _value


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Give each test its own sessions directory and a fresh Config."""
    from backend.config import get_config

    monkeypatch.setenv("SESSIONS_DIR", str(tmp_path / "sessions"))
    get_config.cache_clear()
    yield
    get_config.cache_clear()


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Clear every limiter between tests.

    The limiters are module-level singletons, so without this a test that makes ten
    requests would starve the next test of its budget and produce a confusing 429.
    """
    import gc

    from backend.security import RateLimiter

    yield
    for obj in gc.get_objects():
        if isinstance(obj, RateLimiter):
            obj._hits.clear()  # noqa: SLF001 — test-only reset


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.main import app

    return TestClient(app)


@pytest.fixture
def new_session():
    """Create and persist a session, returning ``(session, access_token)``."""

    def _make(**overrides):
        from backend.session import Session, issue_access_token, save_session

        session = Session.new(
            overrides.pop("instagram_handle", "@test"),
            overrides.pop("account_type", "BUSINESS"),
            overrides.pop("access_token", "token123"),
        )
        for key, value in overrides.items():
            setattr(session, key, value)
        save_session(session)
        return session, issue_access_token(session.session_id)

    return _make


@pytest.fixture
def auth_headers():
    def _headers(token: str) -> dict:
        return {"X-Session-Token": token}

    return _headers

# backend/tests/test_webhook.py
import pytest
import hmac, hashlib, json, os
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

for k, v in {
    "SESSION_ENCRYPTION_KEY": "dGVzdGtleS10ZXN0a2V5LXRlc3RrZXkh",
    "SESSIONS_DIR": "/tmp/test_sessions_wh",
    "OPENPIX_APP_ID": "x",
    "META_APP_ID": "x", "META_APP_SECRET": "x", "META_REDIRECT_URI": "x",
    "ANTHROPIC_API_KEY": "x", "RESEND_API_KEY": "x",
    "ADMIN_EMAIL": "a@b.com", "ADMIN_SECRET": "x",
    "GOOGLE_SHEETS_ID": "x", "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
}.items():
    os.environ.setdefault(k, v)

# Force-set the webhook secret so it overrides any value set by other test modules,
# then clear the lru_cache so get_config() reloads with the correct secret.
os.environ["OPENPIX_WEBHOOK_SECRET"] = "mysecret"
from backend.config import get_config
get_config.cache_clear()


def sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _make_cfg():
    """Return a Config-like object with OPENPIX_WEBHOOK_SECRET = 'mysecret'."""
    from backend.config import Config
    cfg = Config.__new__(Config)
    # Copy all attributes from a real Config, then override the secret.
    real = get_config()
    cfg.__dict__.update(real.__dict__)
    cfg.OPENPIX_WEBHOOK_SECRET = "mysecret"
    return cfg


def test_webhook_rejects_invalid_signature(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)), \
         patch("backend.webhook.get_config", return_value=_make_cfg()):
        from backend.main import app
        client = TestClient(app)
        payload = json.dumps({"charge": {"status": "COMPLETED", "correlationID": "abc"}}).encode()
        resp = client.post(
            "/webhook/openpix",
            content=payload,
            headers={"x-webhook-token": "badsig", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401


def test_webhook_accepts_valid_signature_and_marks_paid(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)), \
         patch("backend.webhook.get_config", return_value=_make_cfg()):
        from backend.session import Session, save_session
        s = Session.new("@u", "BUSINESS", "tok")
        save_session(s)

        from backend.main import app
        with patch("backend.webhook.asyncio") as mock_asyncio:
            mock_asyncio.create_task = lambda coro: coro
            client = TestClient(app)
            payload = json.dumps({"charge": {"status": "COMPLETED", "correlationID": s.session_id}}).encode()
            sig = sign(payload, "mysecret")
            resp = client.post(
                "/webhook/openpix",
                content=payload,
                headers={"x-webhook-token": sig, "Content-Type": "application/json"},
            )
        assert resp.status_code == 200

        from backend.session import load_session
        updated = load_session(s.session_id)
        assert updated.payment_status == "paid"

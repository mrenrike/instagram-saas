# backend/tests/test_checkout.py
import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

for k, v in {
    "SESSION_ENCRYPTION_KEY": "dGVzdGtleS10ZXN0a2V5LXRlc3RrZXkh",
    "SESSIONS_DIR": "/tmp/test_sessions_co",
    "OPENPIX_APP_ID": "test_app_id",
    "OPENPIX_WEBHOOK_SECRET": "secret",
    "META_APP_ID": "x", "META_APP_SECRET": "x", "META_REDIRECT_URI": "x",
    "ANTHROPIC_API_KEY": "x", "RESEND_API_KEY": "x",
    "ADMIN_EMAIL": "a@b.com", "ADMIN_SECRET": "x",
    "GOOGLE_SHEETS_ID": "x", "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
}.items():
    os.environ.setdefault(k, v)

from backend.session import Session, save_session


def make_session(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        s = Session.new("@test", "BUSINESS", "token123")
        s.name = "Test User"
        s.email = "test@example.com"
        s.questionnaire.niche = "Fitness"
        save_session(s)
        return s


def test_checkout_creates_openpix_charge(tmp_path):
    s = make_session(tmp_path)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "charge": {
            "correlationID": s.session_id,
            "brCode": "00020126...",
            "globalID": "charge_abc",
        }
    }
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)), \
         patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        import asyncio
        from backend.checkout import create_checkout
        result = asyncio.run(create_checkout(s.session_id))
        assert "br_code" in result
        assert result["amount"] == 6700  # default price


def test_checkout_status_returns_pending(tmp_path):
    s = make_session(tmp_path)
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        import asyncio
        from backend.checkout import get_checkout_status
        result = asyncio.run(get_checkout_status(s.session_id))
        assert result["payment_status"] == "pending"

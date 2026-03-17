import pytest
import os, json
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SESSION_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleT0=")
os.environ.setdefault("SESSIONS_DIR", "/tmp/test_sessions")
for k in ["OPENPIX_APP_ID","OPENPIX_WEBHOOK_SECRET","META_APP_ID","META_APP_SECRET",
          "META_REDIRECT_URI","ANTHROPIC_API_KEY","RESEND_API_KEY","ADMIN_EMAIL",
          "ADMIN_SECRET","GOOGLE_SHEETS_ID","GOOGLE_SERVICE_ACCOUNT_JSON"]:
    os.environ.setdefault(k, "test")

from backend.session import Session, save_session, load_session, SessionNotFound


def test_session_encrypt_decrypt_roundtrip(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        s = Session.new(
            instagram_handle="@test",
            account_type="BUSINESS",
            access_token="secret_token",
        )
        save_session(s)
        loaded = load_session(s.session_id)
        assert loaded.instagram_handle == "@test"
        assert loaded.access_token == "secret_token"
        assert loaded.pipeline_status == "waiting_payment"


def test_access_token_not_in_file_plaintext(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        s = Session.new(instagram_handle="@x", account_type="CREATOR", access_token="supersecret")
        save_session(s)
        enc_file = list(tmp_path.glob("*.enc"))[0]
        raw = enc_file.read_bytes()
        assert b"supersecret" not in raw


def test_load_missing_session_raises(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        with pytest.raises(SessionNotFound):
            load_session("nonexistent-id")

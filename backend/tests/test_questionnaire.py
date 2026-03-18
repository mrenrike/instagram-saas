import pytest, os
from fastapi.testclient import TestClient
from unittest.mock import patch

for k, v in {
    "SESSION_ENCRYPTION_KEY": "dGVzdGtleS10ZXN0a2V5LXRlc3RrZXkh",
    "SESSIONS_DIR": "/tmp/test_sessions_q",
    "OPENPIX_APP_ID": "x", "OPENPIX_WEBHOOK_SECRET": "x",
    "META_APP_ID": "x", "META_APP_SECRET": "x", "META_REDIRECT_URI": "x",
    "ANTHROPIC_API_KEY": "x", "RESEND_API_KEY": "x",
    "ADMIN_EMAIL": "a@b.com", "ADMIN_SECRET": "x",
    "GOOGLE_SHEETS_ID": "x", "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
    "AGENCY_NAME": "Ag", "AGENCY_LINK": "https://ag.com",
    "AGENCY_HANDLE": "@ag", "AGENCY_EMAIL": "ag@ag.com",
}.items():
    os.environ.setdefault(k, v)

from backend.session import Session, save_session, load_session


def make_session(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        s = Session.new("@u", "BUSINESS", "tok")
        save_session(s)
        return s


VALID_BODY = {
    "name": "Test User",
    "email": "test@example.com",
    "niche": "Fitness",
    "goal": "Crescer seguidores",
    "audience": "Jovens 18-25",
    "tone": "Descontraído",
    "management_style": "solo",
    "competitors": [],
    "extra_context": "",
}


def test_questionnaire_saves_data(tmp_path):
    s = make_session(tmp_path)
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)), \
         patch("backend.coupons.COUPONS_FILE", str(tmp_path / "coupons.json")):
        from backend.main import app
        client = TestClient(app)
        resp = client.post(f"/questionnaire/{s.session_id}", json=VALID_BODY)
    assert resp.status_code == 200
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        updated = load_session(s.session_id)
    assert updated.name == "Test User"
    assert updated.questionnaire.niche == "Fitness"
    assert updated.questionnaire.management_style == "solo"


def test_questionnaire_unknown_session_returns_404(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        from backend.main import app
        client = TestClient(app)
        resp = client.post("/questionnaire/nonexistent-id", json=VALID_BODY)
    assert resp.status_code == 404


def test_questionnaire_invalid_coupon_returns_400(tmp_path):
    import json
    coupon_file = tmp_path / "coupons.json"
    coupon_file.write_text(json.dumps({}))
    s = make_session(tmp_path)
    body = {**VALID_BODY, "coupon_code": "BADCODE"}
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)), \
         patch("backend.coupons.COUPONS_FILE", str(coupon_file)):
        from backend.main import app
        client = TestClient(app)
        resp = client.post(f"/questionnaire/{s.session_id}", json=body)
    assert resp.status_code == 400
    assert "Cupom" in resp.json()["detail"]

# backend/tests/test_pipeline.py
import pytest, os, asyncio
from unittest.mock import patch, AsyncMock, MagicMock

for k, v in {
    "SESSION_ENCRYPTION_KEY": "dGVzdGtleS10ZXN0a2V5LXRlc3RrZXkh",
    "SESSIONS_DIR": "/tmp/test_sessions_pl",
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


def make_paid_session(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        s = Session.new("@user", "BUSINESS", "token")
        s.name = "User"
        s.email = "user@example.com"
        s.payment_status = "paid"
        s.pipeline_status = "queued"
        s.questionnaire.niche = "Fitness"
        s.questionnaire.management_style = "seeking_agency"
        save_session(s)
        return s


@pytest.mark.asyncio
async def test_pipeline_reaches_done_on_success(tmp_path):
    s = make_paid_session(tmp_path)

    mock_posts = [{"media_type": "REEL", "like_count": 100, "comments_count": 10,
                   "saved": 5, "shares": 2, "hour_brt": 18, "weekday_brt": 1,
                   "timestamp_brt": "2026-03-01T18:00:00-03:00", "caption": "test",
                   "permalink": "https://ig.com/p/abc", "reach": 500, "impressions": 600}]
    mock_user = {"id": "123", "username": "user", "followers_count": 1000}
    mock_analysis = "Análise completa do Claude aqui."

    with patch("backend.session.SESSIONS_DIR", str(tmp_path)), \
         patch("backend.pipeline.fetch_posts", AsyncMock(return_value=mock_posts)), \
         patch("backend.pipeline.fetch_user_info", AsyncMock(return_value=mock_user)), \
         patch("backend.pipeline.call_claude", AsyncMock(return_value=mock_analysis)), \
         patch("backend.pipeline.send_report_email", AsyncMock()), \
         patch("backend.pipeline.append_to_crm", AsyncMock()), \
         patch("backend.pipeline.notify_admin_error", AsyncMock()):
        from backend.pipeline import run_pipeline
        await run_pipeline(s.session_id)

    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        updated = load_session(s.session_id)
    assert updated.pipeline_status == "done"
    assert updated.report_generated_at is not None


@pytest.mark.asyncio
async def test_pipeline_sets_error_on_token_expired(tmp_path):
    s = make_paid_session(tmp_path)

    from backend.instagram import TokenExpiredError
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)), \
         patch("backend.pipeline.fetch_posts", AsyncMock(side_effect=TokenExpiredError("expired"))), \
         patch("backend.pipeline.fetch_user_info", AsyncMock(return_value={})), \
         patch("backend.pipeline.send_error_email", AsyncMock()), \
         patch("backend.pipeline.notify_admin_error", AsyncMock()):
        from backend.pipeline import run_pipeline
        await run_pipeline(s.session_id)

    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        updated = load_session(s.session_id)
    assert updated.pipeline_status == "error"

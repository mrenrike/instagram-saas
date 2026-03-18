import pytest, os
from unittest.mock import patch, MagicMock

for k, v in {
    "SESSION_ENCRYPTION_KEY": "dGVzdGtleS10ZXN0a2V5LXRlc3RrZXkh",
    "SESSIONS_DIR": "/tmp/test_crm",
    "OPENPIX_APP_ID": "x", "OPENPIX_WEBHOOK_SECRET": "x",
    "META_APP_ID": "x", "META_APP_SECRET": "x", "META_REDIRECT_URI": "x",
    "ANTHROPIC_API_KEY": "x", "RESEND_API_KEY": "x",
    "ADMIN_EMAIL": "a@b.com", "ADMIN_SECRET": "x",
    "GOOGLE_SHEETS_ID": "sheet123",
    "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type":"service_account","project_id":"p","private_key_id":"k","private_key":"-----BEGIN RSA PRIVATE KEY-----\\nMIIEow==\\n-----END RSA PRIVATE KEY-----","client_email":"sa@p.iam.gserviceaccount.com","client_id":"1","auth_uri":"https://a","token_uri":"https://t","auth_provider_x509_cert_url":"https://c","client_x509_cert_url":"https://c"}',
    "AGENCY_NAME": "Ag", "AGENCY_LINK": "https://ag.com",
    "AGENCY_HANDLE": "@ag", "AGENCY_EMAIL": "ag@ag.com",
}.items():
    os.environ.setdefault(k, v)


@pytest.mark.asyncio
async def test_crm_append_calls_sheets_api(tmp_path):
    with patch("backend.session.SESSIONS_DIR", str(tmp_path)):
        from backend.session import Session
        s = Session.new("@u", "BUSINESS", "tok")
        s.email = "u@example.com"
        s.name = "User"
        s.questionnaire.niche = "Fitness"
        s.questionnaire.goal = "Crescer seguidores"
        s.questionnaire.management_style = "seeking_agency"
        s.utm_source = "ig_bio"
        s.amount_paid_brl = 6700

        mock_service = MagicMock()
        mock_values = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value = mock_values
        mock_append = MagicMock()
        mock_append.execute.return_value = {}
        mock_values.append.return_value = mock_append

        with patch("backend.crm._get_sheets_service", return_value=mock_service):
            from backend.crm import append_to_crm
            await append_to_crm(s)

        mock_values.append.assert_called_once()
        call_kwargs = mock_values.append.call_args.kwargs
        assert call_kwargs["spreadsheetId"] == "sheet123"
        rows = call_kwargs["body"]["values"][0]
        assert "@u" in rows
        assert "Fitness" in rows
        assert "Quente" in rows  # seeking_agency → Quente

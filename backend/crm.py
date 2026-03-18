# backend/crm.py
import json
from datetime import datetime, timezone, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import get_config

BRT = timezone(timedelta(hours=-3))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
LEAD_SCORE = {
    "seeking_agency": "Quente",
    "solo": "Morno",
    "team": "Morno",
    "has_agency": "Frio",
}


def _get_sheets_service():
    cfg = get_config()
    creds_info = json.loads(cfg.GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


async def append_to_crm(session) -> None:
    cfg = get_config()
    now_brt = datetime.now(BRT).isoformat()
    management = session.questionnaire.management_style
    score = LEAD_SCORE.get(management, "Morno")

    row = [
        now_brt,
        session.name,
        session.email,
        session.instagram_handle,
        session.questionnaire.niche,
        session.questionnaire.goal,
        management,
        score,
        session.utm_source,
        session.amount_paid_brl / 100,
        session.coupon_code or "",
    ]

    service = _get_sheets_service()
    service.spreadsheets().values().append(
        spreadsheetId=cfg.GOOGLE_SHEETS_ID,
        range="Leads!A:K",
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()

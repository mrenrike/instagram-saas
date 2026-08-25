# backend/crm.py
import json
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import get_config
from .security import sanitize_for_spreadsheet

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

    # Item 13 (spreadsheet analogue of parameterised queries): every user-supplied
    # cell is neutralised so a name like "=IMPORTXML(...)" is stored as text instead of
    # executing as a formula the moment an operator opens the sheet.
    row = [
        now_brt,
        sanitize_for_spreadsheet(session.name),
        sanitize_for_spreadsheet(session.email),
        sanitize_for_spreadsheet(session.instagram_handle),
        sanitize_for_spreadsheet(session.questionnaire.niche),
        sanitize_for_spreadsheet(session.questionnaire.goal),
        sanitize_for_spreadsheet(management),
        score,
        sanitize_for_spreadsheet(session.utm_source),
        session.amount_paid_brl / 100,
        sanitize_for_spreadsheet(session.coupon_code or ""),
    ]

    service = _get_sheets_service()
    service.spreadsheets().values().append(
        spreadsheetId=cfg.GOOGLE_SHEETS_ID,
        range="Leads!A:K",
        # RAW keeps the API from re-interpreting a cell as a formula or a date.
        valueInputOption="RAW",
        body={"values": [row]},
    ).execute()

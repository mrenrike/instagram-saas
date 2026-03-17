import os
import base64
from functools import lru_cache


class Config:
    # Session
    SESSION_ENCRYPTION_KEY: bytes = base64.b64decode(
        os.environ["SESSION_ENCRYPTION_KEY"]
    )
    SESSIONS_DIR: str = os.getenv("SESSIONS_DIR", "./sessions")

    # Pricing
    REPORT_PRICE_BRL: int = int(os.getenv("REPORT_PRICE_BRL", "6700"))

    # OpenPix
    OPENPIX_APP_ID: str = os.environ["OPENPIX_APP_ID"]
    OPENPIX_WEBHOOK_SECRET: str = os.environ["OPENPIX_WEBHOOK_SECRET"]

    # Meta OAuth
    META_APP_ID: str = os.environ["META_APP_ID"]
    META_APP_SECRET: str = os.environ["META_APP_SECRET"]
    META_REDIRECT_URI: str = os.environ["META_REDIRECT_URI"]

    # Anthropic
    ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]

    # Resend
    RESEND_API_KEY: str = os.environ["RESEND_API_KEY"]
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "relatorios@example.com.br")

    # Admin
    ADMIN_EMAIL: str = os.environ["ADMIN_EMAIL"]
    ADMIN_SECRET: str = os.environ["ADMIN_SECRET"]

    # Google Sheets
    GOOGLE_SHEETS_ID: str = os.environ["GOOGLE_SHEETS_ID"]
    GOOGLE_SERVICE_ACCOUNT_JSON: str = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

    # Agency upsell
    AGENCY_NAME: str = os.getenv("AGENCY_NAME", "Nossa Agência")
    AGENCY_LINK: str = os.getenv("AGENCY_LINK", "https://agencia.com.br")
    AGENCY_HANDLE: str = os.getenv("AGENCY_HANDLE", "@agencia")
    AGENCY_EMAIL: str = os.getenv("AGENCY_EMAIL", "contato@agencia.com.br")


@lru_cache
def get_config() -> Config:
    return Config()

import os
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import get_config

SESSIONS_DIR = os.getenv("SESSIONS_DIR", "./sessions")


class SessionNotFound(Exception):
    pass


def _key() -> bytes:
    return get_config().SESSION_ENCRYPTION_KEY


def _encrypt(data: bytes) -> bytes:
    nonce = os.urandom(12)
    ct = AESGCM(_key()).encrypt(nonce, data, None)
    return nonce + ct


def _decrypt(data: bytes) -> bytes:
    nonce, ct = data[:12], data[12:]
    return AESGCM(_key()).decrypt(nonce, ct, None)


@dataclass
class Questionnaire:
    niche: str = ""
    goal: str = ""
    audience: str = ""
    tone: str = ""
    management_style: str = ""  # solo|team|seeking_agency|has_agency
    competitors: list = field(default_factory=list)
    extra_context: str = ""


@dataclass
class Session:
    session_id: str
    created_at: str
    expires_at: str
    instagram_handle: str
    account_type: str           # BUSINESS | CREATOR
    access_token: str           # plaintext in memory, encrypted at rest
    email: str = ""
    name: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    questionnaire: Questionnaire = field(default_factory=Questionnaire)
    coupon_code: Optional[str] = None
    discount_applied: int = 0   # centavos
    payment_status: str = "pending"  # pending|paid|expired
    payment_id: str = ""
    amount_paid_brl: int = 0    # centavos
    pipeline_status: str = "waiting_payment"
    pipeline_error: Optional[str] = None
    retry_token: Optional[str] = None
    report_generated_at: Optional[str] = None
    quick_wins: str = ""             # first 600 chars of TXT report — used in D+3 follow-up
    followup_scheduled_at: Optional[str] = None
    followup_sent_at: Optional[str] = None

    @classmethod
    def new(cls, instagram_handle: str, account_type: str, access_token: str, **kwargs) -> "Session":
        now = datetime.now(timezone.utc)
        return cls(
            session_id=str(uuid.uuid4()),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=24)).isoformat(),
            instagram_handle=instagram_handle,
            account_type=account_type,
            access_token=access_token,
            **kwargs,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["questionnaire"] = asdict(self.questionnaire)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        q = Questionnaire(**d.pop("questionnaire", {}))
        return cls(questionnaire=q, **d)


def _session_path(session_id: str) -> Path:
    return Path(SESSIONS_DIR) / f"{session_id}.json.enc"


def save_session(session: Session) -> None:
    Path(SESSIONS_DIR).mkdir(parents=True, exist_ok=True)
    raw = json.dumps(session.to_dict()).encode()
    enc = _encrypt(raw)
    _session_path(session.session_id).write_bytes(enc)


def load_session(session_id: str) -> Session:
    path = _session_path(session_id)
    if not path.exists():
        raise SessionNotFound(session_id)
    enc = path.read_bytes()
    raw = _decrypt(enc)
    return Session.from_dict(json.loads(raw))

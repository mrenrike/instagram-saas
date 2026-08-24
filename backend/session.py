"""Encrypted session storage.

Item 5  — the whole record is encrypted at rest with AES-256-GCM, and the file is
          written with 0600 permissions inside a 0700 directory.
Item 7  — the session id is validated as a UUID before it ever touches a path, and
          every read/write from the browser must also present a signed access token.
Item 14 — see :func:`backend.security.safe_identifier`.
"""
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import get_config
from .security import (
    InvalidIdentifier,
    InvalidResourceToken,
    safe_identifier,
    sign_resource_token,
    verify_resource_token,
)

_NONCE_BYTES = 12
_SESSION_SCOPE = "session"


class SessionNotFound(Exception):
    pass


class InvalidSessionId(Exception):
    pass


class SessionAccessDenied(Exception):
    pass


def _sessions_dir() -> Path:
    return Path(get_config().SESSIONS_DIR)


def _key() -> bytes:
    return get_config().SESSION_ENCRYPTION_KEY


def _encrypt(data: bytes, session_id: str) -> bytes:
    """Encrypt with the session id as associated data.

    Binding the id into the AEAD means a stolen ciphertext cannot be renamed onto
    another session's file and decrypted there — the tag check fails.
    """
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(_key()).encrypt(nonce, data, session_id.encode())
    return nonce + ciphertext


def _decrypt(data: bytes, session_id: str) -> bytes:
    nonce, ciphertext = data[:_NONCE_BYTES], data[_NONCE_BYTES:]
    aesgcm = AESGCM(_key())
    try:
        return aesgcm.decrypt(nonce, ciphertext, session_id.encode())
    except InvalidTag:
        # Sessions written before the id was bound in as associated data. Harmless to
        # accept for the 24h these live; drop this branch after one deploy cycle.
        return aesgcm.decrypt(nonce, ciphertext, None)


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
    coupon_code: str | None = None
    discount_applied: int = 0   # centavos
    payment_status: str = "pending"  # pending|paid|expired
    payment_id: str = ""
    amount_paid_brl: int = 0    # centavos
    pipeline_status: str = "waiting_payment"
    pipeline_error: str | None = None      # internal detail — never returned to the client
    pipeline_error_kind: str | None = None  # coarse category safe to expose (item 17)
    retry_token: str | None = None
    report_generated_at: str | None = None
    quick_wins: str = ""             # first 600 chars of TXT report — used in D+3 follow-up
    followup_scheduled_at: str | None = None
    followup_sent_at: str | None = None

    @classmethod
    def new(cls, instagram_handle: str, account_type: str, access_token: str, **kwargs) -> "Session":
        now = datetime.now(UTC)
        ttl = timedelta(hours=get_config().SESSION_TTL_HOURS)
        return cls(
            session_id=str(uuid.uuid4()),
            created_at=now.isoformat(),
            expires_at=(now + ttl).isoformat(),
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
        # Ignore fields removed in a later version rather than crashing on old records.
        known = {f for f in cls.__dataclass_fields__ if f != "questionnaire"}
        return cls(questionnaire=q, **{k: v for k, v in d.items() if k in known})

    def is_expired(self) -> bool:
        try:
            return datetime.now(UTC) > datetime.fromisoformat(self.expires_at)
        except (TypeError, ValueError):
            return True

    def public_view(self) -> dict:
        """Item 17 — the only session fields the browser is ever shown.

        Notably absent: access_token, email, payment_id and pipeline_error.
        """
        return {
            "session_id": self.session_id,
            "instagram_handle": self.instagram_handle,
            "payment_status": self.payment_status,
            "pipeline_status": self.pipeline_status,
        }


def validate_session_id(session_id: str) -> str:
    """Reject anything that is not a canonical UUID.

    Without this, ``session_id`` flows straight into ``SESSIONS_DIR / f"{id}.json.enc"``
    and ``../../`` walks out of the directory.
    """
    try:
        return safe_identifier(session_id, kind="uuid")
    except InvalidIdentifier as exc:
        raise InvalidSessionId(str(exc)) from exc


def issue_access_token(session_id: str) -> str:
    """Mint the token the browser must present alongside the session id."""
    cfg = get_config()
    return sign_resource_token(
        session_id,
        cfg.SESSION_TOKEN_KEY,
        ttl_seconds=cfg.SESSION_TTL_HOURS * 3600,
        scope=_SESSION_SCOPE,
    )


def require_access(session_id: str, token: str) -> str:
    """Validate the id and its access token together; return the safe id."""
    safe_id = validate_session_id(session_id)
    try:
        verify_resource_token(token, safe_id, get_config().SESSION_TOKEN_KEY, scope=_SESSION_SCOPE)
    except InvalidResourceToken as exc:
        raise SessionAccessDenied(str(exc)) from exc
    return safe_id


def _session_path(session_id: str) -> Path:
    return _sessions_dir() / f"{validate_session_id(session_id)}.json.enc"


def save_session(session: Session) -> None:
    directory = _sessions_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions
    # A regra sugere 0o644, que é o default para ARQUIVO. Aqui é um DIRETÓRIO:
    # 0o700 é mais restritivo que o 0o755 usual (só o dono entra), e 0o644 sem o
    # bit de execução tornaria o diretório inacessível. Ver o teste
    # test_session_file_is_owner_only.
    os.chmod(directory, 0o700)

    path = _session_path(session.session_id)
    payload = _encrypt(json.dumps(session.to_dict()).encode(), session.session_id)

    # Write via a temp file so a crash mid-write cannot leave a truncated session, and
    # create it 0600 from the start rather than widening then narrowing the mode.
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def load_session(session_id: str) -> Session:
    path = _session_path(session_id)
    if not path.exists():
        raise SessionNotFound(session_id)
    return Session.from_dict(json.loads(_decrypt(path.read_bytes(), validate_session_id(session_id))))


def delete_session(session_id: str) -> None:
    _session_path(session_id).unlink(missing_ok=True)

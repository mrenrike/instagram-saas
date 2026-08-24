"""Admin operations and pipeline status.

Item 6/10/11 — the retry endpoint is behind a constant-time, rate-limited secret check
               that accepts a pbkdf2 hash.
Item 15      — the alert e-mail escapes every value it interpolates.
Item 17      — the public status endpoint returns a coarse state, never the raw error.
"""
import asyncio
import logging

import resend
from fastapi import APIRouter, Depends, HTTPException, Path

from .config import get_config
from .deps import authorized_session, require_admin
from .security import RateLimiter, escape_html, rate_limit
from .security.responses import PUBLIC_ERROR_MESSAGES
from .session import (
    InvalidSessionId,
    Session,
    SessionNotFound,
    load_session,
    save_session,
    validate_session_id,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_status_limiter = RateLimiter(120, 60, name="pipeline_status")

_STEPS = {
    "waiting_payment": 0,
    "queued": 0,
    "fetching_data": 1,
    "analyzing": 2,
    "building_report": 3,
    "sending_email": 4,
    "done": 5,
    "error": -1,
}


async def notify_admin_error(session_id: str, error_msg: str) -> None:
    """Alert the operator. Everything interpolated here is escaped (item 15).

    ``session.name`` and ``session.instagram_handle`` are user-controlled, and the
    exception text can contain attacker-influenced content. Unescaped, that is HTML
    injection into the operator's inbox.
    """
    cfg = get_config()
    resend.api_key = cfg.RESEND_API_KEY

    try:
        session = load_session(session_id)
        client_info = (
            f"Cliente: {escape_html(session.name)} "
            f"({escape_html(session.email)}), {escape_html(session.instagram_handle)}"
        )
    except (SessionNotFound, InvalidSessionId):
        client_info = "(sessão não encontrada)"

    safe_id = escape_html(session_id)
    safe_error = escape_html(error_msg)

    try:
        resend.Emails.send(
            {
                "from": cfg.FROM_EMAIL,
                "to": [cfg.ADMIN_EMAIL],
                # The admin secret is NOT included here: e-mail is not a secure channel
                # and inboxes get forwarded, searched and breached.
                "subject": f"[ERRO] Pipeline falhou — {safe_id[:8]}",
                "html": f"""<h2>Erro no pipeline</h2>
            <p><strong>Session:</strong> {safe_id}</p>
            <p><strong>Erro:</strong> {safe_error}</p>
            <p><strong>{client_info}</strong></p>
            <p><strong>Para reprocessar:</strong><br>
            <code>POST /admin/retry/{safe_id}</code> com o header
            <code>Authorization: Bearer &lt;ADMIN_SECRET&gt;</code></p>""",
            }
        )
    except Exception:  # noqa: BLE001 — alerting is best effort, never fail the pipeline
        logger.exception("Could not send admin alert for %s", session_id)


@router.post("/admin/retry/{session_id}", dependencies=[Depends(require_admin)])
async def admin_retry(session_id: str = Path(..., min_length=36, max_length=36)):
    try:
        safe_id = validate_session_id(session_id)
    except InvalidSessionId as exc:
        raise HTTPException(404, "Session not found") from exc

    try:
        session = load_session(safe_id)
    except SessionNotFound as exc:
        raise HTTPException(404, "Session not found") from exc

    if session.payment_status != "paid":
        raise HTTPException(400, "Session not paid — cannot retry")

    from .pipeline import run_pipeline

    session.pipeline_status = "queued"
    session.pipeline_error = None
    session.pipeline_error_kind = None
    save_session(session)

    asyncio.create_task(run_pipeline(safe_id))
    return {"status": "queued", "session_id": safe_id}


@router.get("/pipeline/status/{session_id}", dependencies=[Depends(rate_limit(_status_limiter))])
async def pipeline_status(session: Session = Depends(authorized_session)):
    """Item 17 — a coarse status and a friendly message, never the raw exception.

    ``session.pipeline_error`` holds things like Graph API URLs with tokens in the query
    string and Python tracebacks. It stays server-side; the client gets a category.
    """
    kind = session.pipeline_error_kind
    return {
        "status": session.pipeline_status,
        "step": _STEPS.get(session.pipeline_status, 0),
        "error": kind,
        "error_message": PUBLIC_ERROR_MESSAGES.get(kind or "", "") if kind else None,
    }

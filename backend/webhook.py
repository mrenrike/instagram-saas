"""OpenPix payment webhook.

Item 6  — the payment state is only ever advanced by a request carrying a valid HMAC
          signature; the browser can never mark a session as paid.
Item 11 — rate limited so an unauthenticated endpoint cannot be used to exhaust CPU on
          signature checks.
Item 14 — the body is parsed defensively and the correlation id is validated as a UUID.
"""
import asyncio
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .config import get_config
from .pipeline import run_pipeline
from .security import RateLimiter, rate_limit
from .session import (
    InvalidSessionId,
    SessionNotFound,
    load_session,
    save_session,
    validate_session_id,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_limiter = RateLimiter(60, 60, name="webhook")


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Constant-time HMAC-SHA256 comparison over the exact raw body.

    The signature must be computed over the bytes as received: re-serialising the JSON
    first would change key order and whitespace and break verification (or, worse,
    tempt someone into skipping it).
    """
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


@router.post("/webhook/openpix", dependencies=[Depends(rate_limit(_limiter))])
async def openpix_webhook(request: Request):
    cfg = get_config()
    payload = await request.body()
    signature = request.headers.get("x-webhook-token", "")

    if not _verify_signature(payload, signature, cfg.OPENPIX_WEBHOOK_SECRET):
        logger.warning("Rejected webhook with invalid signature")
        raise HTTPException(401, "Invalid signature")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid payload") from None

    charge = data.get("charge") or {}
    if not isinstance(charge, dict):
        raise HTTPException(400, "Invalid payload")

    if charge.get("status") != "COMPLETED":
        return Response(status_code=200)  # Ignore non-completed events

    try:
        session_id = validate_session_id(str(charge.get("correlationID", "")))
    except InvalidSessionId:
        logger.warning("Webhook carried a non-UUID correlationID")
        return Response(status_code=200)  # Nothing to do — stay idempotent

    try:
        session = load_session(session_id)
    except SessionNotFound:
        return Response(status_code=200)  # Unknown session — idempotent

    if session.payment_status == "paid":
        return Response(status_code=200)  # Already processed — idempotent

    session.payment_status = "paid"
    session.pipeline_status = "queued"
    save_session(session)

    asyncio.create_task(run_pipeline(session_id))

    return Response(status_code=200)

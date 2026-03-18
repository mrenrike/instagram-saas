# backend/webhook.py
import asyncio
import hmac
import hashlib
from fastapi import APIRouter, Request, Response, HTTPException

from .config import get_config
from .session import load_session, save_session, SessionNotFound
from .pipeline import run_pipeline

router = APIRouter()


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook/openpix")
async def openpix_webhook(request: Request):
    cfg = get_config()
    payload = await request.body()
    sig = request.headers.get("x-webhook-token", "")

    if not _verify_signature(payload, sig, cfg.OPENPIX_WEBHOOK_SECRET):
        raise HTTPException(401, "Invalid signature")

    import json as _json
    data = _json.loads(payload)
    charge = data.get("charge", {})

    if charge.get("status") != "COMPLETED":
        return Response(status_code=200)  # Ignore non-completed events

    session_id = charge.get("correlationID", "")
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

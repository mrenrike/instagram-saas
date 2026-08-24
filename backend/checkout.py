"""Pix checkout.

Item 7  — both endpoints require the session's signed access token.
Item 8  — the amount is derived server-side from configuration and the stored discount.
Item 11 — charge creation and status polling have separate limits.
Item 17 — the response carries only what the checkout page renders.
"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from .config import get_config
from .deps import authorized_session
from .security import RateLimiter, rate_limit
from .session import Session, save_session

logger = logging.getLogger(__name__)
router = APIRouter()

OPENPIX_API = "https://api.openpix.com.br/api/v1"
CHARGE_TTL_SECONDS = 900  # 15 min

_create_limiter = RateLimiter(5, 60, name="checkout_create")
# Polling is expected here — the checkout page asks every few seconds — so the ceiling
# is high enough for legitimate polling and low enough to stop a scraping loop.
_status_limiter = RateLimiter(120, 60, name="checkout_status")


@router.post("/checkout/{session_id}", dependencies=[Depends(rate_limit(_create_limiter))])
async def checkout_create(session: Session = Depends(authorized_session)):
    cfg = get_config()
    price = max(0, cfg.REPORT_PRICE_BRL - session.discount_applied)

    if not session.email or not session.name:
        raise HTTPException(400, "Preencha o questionário antes do pagamento.")
    if session.payment_status == "paid":
        raise HTTPException(400, "Esta sessão já foi paga.")

    payload = {
        "correlationID": session.session_id,
        "value": price,
        "comment": f"Relatório Instagram Analytics — {session.instagram_handle}",
        "customer": {"name": session.name, "email": session.email},
        "expiresIn": CHARGE_TTL_SECONDS,
    }
    headers = {"Authorization": cfg.OPENPIX_APP_ID, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{OPENPIX_API}/charge", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.error("OpenPix unreachable for session %s: %s", session.session_id, exc)
        raise HTTPException(502, "Não foi possível criar a cobrança agora.") from exc

    if resp.status_code != 200:
        # The provider's error body can echo the API key back — log the status only.
        logger.error("OpenPix charge failed with status %s", resp.status_code)
        raise HTTPException(502, "Não foi possível criar a cobrança agora.")

    data = resp.json().get("charge", {})
    session.payment_id = str(data.get("globalID", ""))
    session.amount_paid_brl = price
    save_session(session)

    return {
        "session_id": session.session_id,
        "br_code": data.get("brCode", ""),
        "qr_code_image": data.get("qrCodeImage", ""),
        "amount": price,
        "expires_in": CHARGE_TTL_SECONDS,
    }


@router.get("/checkout/status/{session_id}", dependencies=[Depends(rate_limit(_status_limiter))])
async def checkout_status(session: Session = Depends(authorized_session)):
    return {"payment_status": session.payment_status}

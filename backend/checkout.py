# backend/checkout.py
import httpx
from fastapi import APIRouter, HTTPException

from .session import load_session, save_session, SessionNotFound
from .config import get_config

router = APIRouter()
OPENPIX_API = "https://api.openpix.com.br/api/v1"


async def create_checkout(session_id: str) -> dict:
    try:
        session = load_session(session_id)
    except SessionNotFound:
        raise HTTPException(404, "Session not found")

    cfg = get_config()
    price = cfg.REPORT_PRICE_BRL - session.discount_applied
    price = max(0, price)

    payload = {
        "correlationID": session_id,
        "value": price,
        "comment": f"Relatório Instagram Analytics — {session.instagram_handle}",
        "customer": {"name": session.name, "email": session.email},
        "expiresIn": 900,  # 15 min
    }
    headers = {"Authorization": cfg.OPENPIX_APP_ID, "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{OPENPIX_API}/charge", json=payload, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(502, "OpenPix charge creation failed")

    data = resp.json()["charge"]
    session.payment_id = data.get("globalID", "")
    session.amount_paid_brl = price
    save_session(session)

    return {
        "session_id": session_id,
        "br_code": data.get("brCode", ""),
        "qr_code_image": data.get("qrCodeImage", ""),
        "amount": price,
        "expires_in": 900,
    }


async def get_checkout_status(session_id: str) -> dict:
    try:
        session = load_session(session_id)
    except SessionNotFound:
        raise HTTPException(404, "Session not found")
    return {"payment_status": session.payment_status}


@router.post("/checkout/{session_id}")
async def checkout_create(session_id: str):
    return await create_checkout(session_id)


@router.get("/checkout/status/{session_id}")
async def checkout_status(session_id: str):
    return await get_checkout_status(session_id)

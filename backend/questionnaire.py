from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from .session import load_session, save_session, SessionNotFound, Questionnaire
from .coupons import apply_coupon, CouponNotFound, CouponExhausted
from .config import get_config

router = APIRouter()


class QuestionnaireRequest(BaseModel):
    name: str
    email: EmailStr
    niche: str
    goal: str
    audience: str
    tone: str
    management_style: str       # solo|team|seeking_agency|has_agency
    competitors: List[str] = []
    extra_context: str = ""
    coupon_code: Optional[str] = None


@router.post("/questionnaire/{session_id}")
async def submit_questionnaire(session_id: str, body: QuestionnaireRequest):
    try:
        session = load_session(session_id)
    except SessionNotFound:
        raise HTTPException(404, "Session not found")

    if session.payment_status == "paid":
        raise HTTPException(400, "Already paid — cannot modify questionnaire")

    # Apply coupon if provided
    cfg = get_config()
    price = cfg.REPORT_PRICE_BRL
    discount = 0

    if body.coupon_code:
        try:
            discount = apply_coupon(body.coupon_code, price)
        except CouponNotFound:
            raise HTTPException(400, "Cupom inválido")
        except CouponExhausted:
            raise HTTPException(400, "Cupom esgotado")

    session.name = body.name
    session.email = body.email
    session.coupon_code = body.coupon_code
    session.discount_applied = discount
    session.questionnaire = Questionnaire(
        niche=body.niche,
        goal=body.goal,
        audience=body.audience,
        tone=body.tone,
        management_style=body.management_style,
        competitors=body.competitors,
        extra_context=body.extra_context,
    )
    save_session(session)

    final_price = max(0, price - discount)
    return {
        "session_id": session_id,
        "original_price": price,
        "discount": discount,
        "final_price": final_price,
        "coupon_applied": bool(body.coupon_code and discount > 0),
    }

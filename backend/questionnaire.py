"""Questionnaire submission.

Item 8  — the body is a StrictModel: unknown fields are rejected, so a client cannot
          smuggle `price`, `discount_applied` or `payment_status` into the payload.
Item 11 — rate limited per source address.
Item 12 — honeypot field plus optional captcha verification.
Item 14 — every string has an explicit maximum length and an allowed shape.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import EmailStr, Field, field_validator

from .config import get_config
from .coupons import CouponExhausted, CouponNotFound, InvalidCouponCode, apply_coupon
from .deps import authorized_session
from .security import (
    CaptchaFailed,
    RateLimiter,
    StrictModel,
    client_ip,
    rate_limit,
    verify_captcha,
)
from .security.bots import honeypot_tripped
from .session import Questionnaire, Session, save_session

logger = logging.getLogger(__name__)
router = APIRouter()

_MANAGEMENT_STYLES = {"solo", "team", "seeking_agency", "has_agency"}
_MAX_COMPETITORS = 10

_limiter = RateLimiter(10, 60, name="questionnaire")


class QuestionnaireRequest(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    niche: str = Field(min_length=1, max_length=80)
    goal: str = Field(min_length=1, max_length=120)
    audience: str = Field(min_length=1, max_length=300)
    tone: str = Field(min_length=1, max_length=80)
    management_style: str = Field(min_length=1, max_length=32)
    competitors: list[str] = Field(default_factory=list, max_length=_MAX_COMPETITORS)
    extra_context: str = Field(default="", max_length=1_000)
    coupon_code: str | None = Field(default=None, max_length=32)
    captcha_token: str = Field(default="", max_length=4_096)
    # Item 12 — hidden in the form via CSS; a real user never fills it in.
    website: str = Field(default="", max_length=200)

    @field_validator("management_style")
    @classmethod
    def _known_management_style(cls, value: str) -> str:
        if value not in _MANAGEMENT_STYLES:
            raise ValueError("management_style inválido")
        return value

    @field_validator("competitors")
    @classmethod
    def _bounded_competitors(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip()[:80] for item in value if item and item.strip()]
        return cleaned[:_MAX_COMPETITORS]

    @field_validator("coupon_code")
    @classmethod
    def _normalize_coupon(cls, value: str | None) -> str | None:
        return value.strip().upper() if value and value.strip() else None


@router.post("/questionnaire/{session_id}", dependencies=[Depends(rate_limit(_limiter))])
async def submit_questionnaire(
    request: Request,
    body: QuestionnaireRequest,
    session: Session = Depends(authorized_session),
):
    cfg = get_config()

    # --- Item 12: bot filtering ------------------------------------------------
    if honeypot_tripped(body.website):
        logger.info("Honeypot tripped from %s", client_ip(request, trust_proxy=cfg.TRUST_PROXY))
        raise HTTPException(400, "Não foi possível validar o envio.")

    if cfg.TURNSTILE_SECRET:
        try:
            await verify_captcha(
                body.captcha_token,
                cfg.TURNSTILE_SECRET,
                provider=cfg.CAPTCHA_PROVIDER,
                remote_ip=client_ip(request, trust_proxy=cfg.TRUST_PROXY),
            )
        except CaptchaFailed as exc:
            logger.info("Captcha rejected: %s", exc)
            raise HTTPException(400, "Não foi possível validar o envio.") from exc

    # --- Item 8: the price is decided here, never received from the client -----
    if session.payment_status == "paid":
        raise HTTPException(400, "Já pago — o questionário não pode mais ser alterado.")

    price = cfg.REPORT_PRICE_BRL
    discount = 0

    if body.coupon_code:
        try:
            discount = apply_coupon(body.coupon_code, price)
        except (CouponNotFound, InvalidCouponCode) as exc:
            raise HTTPException(400, "Cupom inválido") from exc
        except CouponExhausted as exc:
            raise HTTPException(400, "Cupom esgotado") from exc

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

    return {
        "session_id": session.session_id,
        "original_price": price,
        "discount": discount,
        "final_price": max(0, price - discount),
        "coupon_applied": bool(body.coupon_code and discount > 0),
    }

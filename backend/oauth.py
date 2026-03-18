import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from .config import get_config
from .session import Session, save_session

router = APIRouter()

GRAPH_URL = "https://graph.facebook.com/v21.0"
IG_URL = "https://graph.instagram.com/v21.0"
SCOPES = "instagram_basic,instagram_manage_insights,pages_read_engagement"


@router.get("/oauth/start")
async def oauth_start(
    request: Request,
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
):
    cfg = get_config()
    state = f"{utm_source}|{utm_medium}|{utm_campaign}"
    auth_url = (
        f"https://www.facebook.com/dialog/oauth"
        f"?client_id={cfg.META_APP_ID}"
        f"&redirect_uri={cfg.META_REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&state={state}"
        f"&response_type=code"
    )
    return RedirectResponse(auth_url)


@router.get("/oauth/callback")
async def oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return RedirectResponse("/error.html?reason=oauth_denied")

    cfg = get_config()
    utm_source, utm_medium, utm_campaign = (state.split("|") + ["", "", ""])[:3]

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_resp = await client.get(
            f"{GRAPH_URL}/oauth/access_token",
            params={
                "client_id": cfg.META_APP_ID,
                "client_secret": cfg.META_APP_SECRET,
                "redirect_uri": cfg.META_REDIRECT_URI,
                "code": code,
            },
        )
    if token_resp.status_code != 200:
        return RedirectResponse("/error.html?reason=token_exchange_failed")

    access_token = token_resp.json().get("access_token", "")

    # Get Instagram account info
    async with httpx.AsyncClient() as client:
        me_resp = await client.get(
            f"{IG_URL}/me",
            params={"fields": "id,username,account_type", "access_token": access_token},
        )
    if me_resp.status_code != 200:
        return RedirectResponse("/error.html?reason=graph_api_failed")

    me = me_resp.json()
    account_type = me.get("account_type", "PERSONAL").upper()

    if account_type not in ("BUSINESS", "CREATOR"):
        return RedirectResponse("/error.html?reason=personal_account")

    session = Session.new(
        instagram_handle=f"@{me.get('username', '')}",
        account_type=account_type,
        access_token=access_token,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )
    save_session(session)

    return RedirectResponse(f"/questionnaire.html?session_id={session.session_id}")

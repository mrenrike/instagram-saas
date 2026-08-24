"""Meta OAuth entry and callback.

Item 6  — the account is established server-side from the token exchange; nothing the
          browser sends decides who the session belongs to.
Item 11 — both endpoints are rate limited.
Item 14 — the UTM values that ride along in ``state`` are validated and length-capped.
"""
import logging
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from .config import get_config
from .security import RateLimiter, rate_limit, sign_resource_token, verify_resource_token
from .security.tokens import InvalidResourceToken
from .security.validation import escape_html  # noqa: F401  (kept for template use)
from .session import Session, issue_access_token, save_session

logger = logging.getLogger(__name__)
router = APIRouter()

GRAPH_URL = "https://graph.facebook.com/v21.0"
IG_URL = "https://graph.instagram.com/v21.0"
SCOPES = "instagram_basic,instagram_manage_insights,pages_read_engagement"

_UTM_MAX_LEN = 64
_STATE_SCOPE = "oauth-state"
_STATE_TTL = 900  # 15 min — long enough to log in, short enough to not be replayable

_start_limiter = RateLimiter(20, 60, name="oauth_start")
_callback_limiter = RateLimiter(20, 60, name="oauth_callback")


def _clean_utm(value: str) -> str:
    """Keep UTMs to a harmless shape: they end up in a spreadsheet and in URLs."""
    allowed = [c for c in (value or "") if c.isalnum() or c in "-_. "]
    return "".join(allowed)[:_UTM_MAX_LEN].strip()


def _frontend_url(path: str, **params) -> str:
    """Build a redirect target from configuration only.

    Never interpolate a client-supplied URL here — that is how a login flow becomes an
    open redirect that phishes the user right after they authenticate.
    """
    base = get_config().FRONTEND_BASE_URL
    query = f"?{urlencode(params)}" if params else ""
    return f"{base}{path}{query}" if base else f"{path}{query}"


def _pack_state(utms: tuple[str, str, str]) -> str:
    """Sign the OAuth ``state`` so the callback can prove it started here.

    An unsigned state is the CSRF hole in OAuth: an attacker sends the victim a crafted
    callback URL carrying the attacker's ``code`` and the victim ends up logged into
    the attacker's account (or vice versa, leaking the victim's data).
    """
    cfg = get_config()
    payload = "|".join(utms)
    nonce = str(int(time.time()))
    signature = sign_resource_token(
        f"{payload}|{nonce}", cfg.SESSION_TOKEN_KEY, ttl_seconds=_STATE_TTL, scope=_STATE_SCOPE
    )
    return f"{payload}|{nonce}|{signature}"


def _unpack_state(state: str) -> tuple[str, str, str]:
    """Verify a signed state and return its UTMs; raise on tampering."""
    cfg = get_config()
    parts = state.split("|")
    if len(parts) != 5:
        raise InvalidResourceToken("malformed state")
    source, medium, campaign, nonce, signature = parts
    verify_resource_token(
        signature,
        f"{source}|{medium}|{campaign}|{nonce}",
        cfg.SESSION_TOKEN_KEY,
        scope=_STATE_SCOPE,
    )
    return source, medium, campaign


@router.get("/oauth/start", dependencies=[Depends(rate_limit(_start_limiter))])
async def oauth_start(
    request: Request,
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
):
    cfg = get_config()
    utms = (_clean_utm(utm_source), _clean_utm(utm_medium), _clean_utm(utm_campaign))

    auth_url = "https://www.facebook.com/dialog/oauth?" + urlencode(
        {
            "client_id": cfg.META_APP_ID,
            "redirect_uri": cfg.META_REDIRECT_URI,
            "scope": SCOPES,
            "state": _pack_state(utms),
            "response_type": "code",
        }
    )
    return RedirectResponse(auth_url, status_code=302)


@router.get("/oauth/callback", dependencies=[Depends(rate_limit(_callback_limiter))])
async def oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return RedirectResponse(_frontend_url("/error.html", reason="oauth_denied"), status_code=302)

    cfg = get_config()

    try:
        utm_source, utm_medium, utm_campaign = _unpack_state(state)
    except InvalidResourceToken as exc:
        logger.warning("Rejected OAuth callback with invalid state: %s", exc)
        return RedirectResponse(_frontend_url("/error.html", reason="oauth_denied"), status_code=302)

    async with httpx.AsyncClient(timeout=15) as client:
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
        # The response body can echo the app secret back in an error string — log the
        # status only (item 17).
        logger.error("Meta token exchange failed with status %s", token_resp.status_code)
        return RedirectResponse(
            _frontend_url("/error.html", reason="token_exchange_failed"), status_code=302
        )

    access_token = token_resp.json().get("access_token", "")
    if not access_token:
        return RedirectResponse(
            _frontend_url("/error.html", reason="token_exchange_failed"), status_code=302
        )

    async with httpx.AsyncClient(timeout=15) as client:
        me_resp = await client.get(
            f"{IG_URL}/me",
            params={"fields": "id,username,account_type", "access_token": access_token},
        )
    if me_resp.status_code != 200:
        logger.error("Instagram /me failed with status %s", me_resp.status_code)
        return RedirectResponse(_frontend_url("/error.html", reason="graph_api_failed"), status_code=302)

    me = me_resp.json()
    account_type = str(me.get("account_type", "PERSONAL")).upper()
    if account_type not in ("BUSINESS", "CREATOR"):
        return RedirectResponse(_frontend_url("/error.html", reason="personal_account"), status_code=302)

    username = _clean_utm(str(me.get("username", "")))  # same harmless-shape rule

    session = Session.new(
        instagram_handle=f"@{username}",
        account_type=account_type,
        access_token=access_token,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )
    save_session(session)

    # The access token travels in the URL fragment-free query because the frontend is a
    # static site on another origin and has no server to set a cookie. It is short-lived
    # and scoped to this one session id (item 7).
    return RedirectResponse(
        _frontend_url(
            "/questionnaire.html",
            session_id=session.session_id,
            t=issue_access_token(session.session_id),
        ),
        status_code=302,
    )

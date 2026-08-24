"""Shared FastAPI dependencies for record-level access control (item 7)."""
import logging

from fastapi import Header, HTTPException, Path, Request

from .config import get_config
from .security import RateLimiter, client_ip, constant_time_compare, rate_limit, verify_secret
from .session import (
    InvalidSessionId,
    Session,
    SessionAccessDenied,
    SessionNotFound,
    load_session,
    require_access,
)

logger = logging.getLogger(__name__)

# Deliberately the same message and status for "no such session", "bad token" and
# "expired": distinguishing them turns the endpoint into an oracle that confirms which
# session ids exist.
_DENIED = HTTPException(status_code=404, detail="Sessão não encontrada ou expirada.")

_admin_limiter = RateLimiter(5, 300, name="admin_auth")


async def authorized_session(
    request: Request,
    session_id: str = Path(..., min_length=36, max_length=36),
    x_session_token: str = Header(default=""),
) -> Session:
    """Resolve a session only when the caller presents a valid token for that exact id.

    The header is preferred over the ``?t=`` query parameter: query strings end up in
    access logs, browser history and Referer headers. The query fallback exists because
    the OAuth callback has to hand the token to a static frontend through a redirect.
    """
    presented = x_session_token or request.query_params.get("t", "")

    try:
        safe_id = require_access(session_id, presented)
    except (InvalidSessionId, SessionAccessDenied) as exc:
        logger.info("Session access denied: %s", exc)
        raise _DENIED from exc

    try:
        session = load_session(safe_id)
    except SessionNotFound as exc:
        raise _DENIED from exc

    if session.is_expired():
        raise _DENIED

    return session


async def require_admin(
    request: Request,
    authorization: str = Header(default=""),
) -> None:
    """Item 6/10/11 — constant-time secret check, hashed when configured, rate limited.

    Failed attempts are counted per source address so the admin secret cannot be
    brute-forced, and the counter is only consumed on failure.
    """
    cfg = get_config()

    await rate_limit(_admin_limiter)(request)

    presented = authorization.removeprefix("Bearer ").strip()
    if not presented:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if cfg.ADMIN_SECRET_HASH:
        ok = verify_secret(presented, cfg.ADMIN_SECRET_HASH)
    else:
        ok = constant_time_compare(presented, cfg.ADMIN_SECRET)

    if not ok:
        logger.warning("Failed admin authentication from %s", client_ip(request, trust_proxy=cfg.TRUST_PROXY))
        raise HTTPException(status_code=401, detail="Unauthorized")

    await _admin_limiter.reset(f"{_admin_limiter.name}:{client_ip(request, trust_proxy=cfg.TRUST_PROXY)}")

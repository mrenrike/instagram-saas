"""Item 9 — session cookie protection."""
from __future__ import annotations

from starlette.responses import Response

DEFAULT_MAX_AGE = 86_400  # 24h


def set_session_cookie(
    response: Response,
    name: str,
    value: str,
    *,
    max_age: int = DEFAULT_MAX_AGE,
    secure: bool = True,
    same_site: str = "lax",
    domain: str | None = None,
    path: str = "/",
) -> None:
    """Set a session cookie with the flags a session cookie must always carry.

    httponly    keeps it out of ``document.cookie``, so an XSS cannot exfiltrate it.
    secure      keeps it off plain HTTP.
    samesite    blocks it from riding along on cross-site requests (CSRF).

    ``same_site="none"`` is required when the frontend and API are on different sites
    (e.g. a static frontend on Hostinger calling an API on Railway). That combination
    only works with ``secure=True``, and it re-opens CSRF — pair it with an explicit
    CORS allowlist and a CSRF token, or prefer a signed token in the Authorization
    header instead of a cookie for cross-site setups.
    """
    same_site = same_site.lower()
    if same_site not in {"lax", "strict", "none"}:
        raise ValueError("same_site must be lax, strict or none")
    if same_site == "none" and not secure:
        raise ValueError("SameSite=None requires Secure")

    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        expires=max_age,
        path=path,
        domain=domain,
        secure=secure,
        httponly=True,
        samesite=same_site,
    )


def clear_session_cookie(
    response: Response,
    name: str,
    *,
    domain: str | None = None,
    path: str = "/",
    secure: bool = True,
    same_site: str = "lax",
) -> None:
    """Expire a session cookie. Must repeat path/domain or the browser keeps the old one."""
    response.set_cookie(
        key=name,
        value="",
        max_age=0,
        expires=0,
        path=path,
        domain=domain,
        secure=secure,
        httponly=True,
        samesite=same_site.lower(),
    )

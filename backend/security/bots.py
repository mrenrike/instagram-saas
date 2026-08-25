"""Item 12 — bot protection."""
from __future__ import annotations

import httpx

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"

_PROVIDERS = {
    "turnstile": TURNSTILE_VERIFY_URL,
    "hcaptcha": HCAPTCHA_VERIFY_URL,
}


class CaptchaFailed(Exception):
    pass


async def verify_captcha(
    token: str,
    secret: str,
    *,
    provider: str = "turnstile",
    remote_ip: str | None = None,
    timeout: float = 5.0,
) -> None:
    """Verify a captcha token server-side; raise :class:`CaptchaFailed` if it does not check out.

    The widget's client-side callback proves nothing — the token must be redeemed here,
    once, against the provider. Tokens are single-use, so never cache the result.

    A project without a configured secret should skip the call entirely rather than
    pass an empty secret: silently "verifying" with no secret is worse than no captcha
    because it reads as protection that is not there.
    """
    if not secret:
        raise CaptchaFailed("captcha secret not configured")
    if not token:
        raise CaptchaFailed("missing captcha token")

    url = _PROVIDERS.get(provider)
    if url is None:
        raise CaptchaFailed(f"unknown captcha provider {provider}")

    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, data=data)
    except httpx.HTTPError as exc:
        raise CaptchaFailed("captcha provider unreachable") from exc

    if response.status_code != 200:
        raise CaptchaFailed("captcha provider error")
    if not response.json().get("success"):
        raise CaptchaFailed("captcha rejected")


def honeypot_tripped(value: str | None) -> bool:
    """True when a hidden form field came back filled in.

    A field hidden with CSS and left empty by every real user is a cheap first filter:
    naive bots fill in every input they find. It complements a captcha, it does not
    replace one — a targeted script will skip it.
    """
    return bool(value and value.strip())

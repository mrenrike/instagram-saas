"""Item 7 — restrict access to records.

An unguessable identifier is not an authorisation check: identifiers leak through
logs, referrers, browser history and shared links, and any endpoint keyed on one alone
is an IDOR waiting to happen. These helpers mint a short-lived HMAC token bound to a
specific resource so possession of the id alone is not enough to read or modify it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time


class InvalidResourceToken(Exception):
    pass


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def sign_resource_token(
    resource_id: str,
    key: bytes,
    *,
    ttl_seconds: int = 86_400,
    scope: str = "",
    now: int | None = None,
) -> str:
    """Mint ``<expiry>.<signature>`` binding ``resource_id`` (+ optional scope) to ``key``."""
    expiry = int(now if now is not None else time.time()) + ttl_seconds
    payload = f"{scope}|{resource_id}|{expiry}".encode()
    signature = hmac.new(key, payload, hashlib.sha256).digest()
    return f"{expiry}.{_b64(signature)}"


def verify_resource_token(
    token: str,
    resource_id: str,
    key: bytes,
    *,
    scope: str = "",
    now: int | None = None,
) -> None:
    """Raise :class:`InvalidResourceToken` unless ``token`` is valid for this resource."""
    if not token:
        raise InvalidResourceToken("missing token")

    try:
        expiry_s, signature_b64 = token.split(".", 1)
        expiry = int(expiry_s)
        signature = _unb64(signature_b64)
    except (ValueError, TypeError) as exc:
        raise InvalidResourceToken("malformed token") from exc

    payload = f"{scope}|{resource_id}|{expiry}".encode()
    expected = hmac.new(key, payload, hashlib.sha256).digest()
    # Signature first, so an expired-but-forged token still fails on the signature and
    # the check stays constant-time with respect to the secret.
    if not hmac.compare_digest(expected, signature):
        raise InvalidResourceToken("bad signature")

    if int(now if now is not None else time.time()) > expiry:
        raise InvalidResourceToken("expired")

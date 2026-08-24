"""Items 6 and 10 — server-side secret comparison and storage."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets as _secrets

# PBKDF2 rounds. bcrypt/argon2 are better, but this module stays dependency-free; a
# project that already depends on passlib should use passlib for *user* passwords and
# keep this for machine-to-machine shared secrets.
_PBKDF2_ROUNDS = 600_000
_PBKDF2_ALGO = "sha256"


def constant_time_compare(a: str | bytes, b: str | bytes) -> bool:
    """Compare two secrets without leaking their contents through timing.

    ``a == b`` returns as soon as it finds a differing byte, which is enough to
    recover a token one character at a time over enough requests.
    """
    if isinstance(a, str):
        a = a.encode("utf-8")
    if isinstance(b, str):
        b = b.encode("utf-8")
    return hmac.compare_digest(a, b)


def hash_secret(secret: str, *, salt: bytes | None = None) -> str:
    """Hash a secret for storage as ``pbkdf2_sha256$rounds$salt$hash``.

    Never store an API key, admin token or password in plaintext — not in the database,
    not in a config file that ships with the app.
    """
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, secret.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_{_PBKDF2_ALGO}${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_secret(candidate: str, stored: str) -> bool:
    """Verify ``candidate`` against a plaintext secret or a :func:`hash_secret` digest.

    Both paths are constant-time. Accepting a plaintext ``stored`` value keeps this
    usable for shared secrets that come straight from the environment (a webhook token
    the provider also holds in plaintext), while letting a project migrate to hashes
    without changing call sites.
    """
    if stored.startswith("pbkdf2_"):
        try:
            _, rounds_s, salt_hex, digest_hex = stored.split("$")
            rounds = int(rounds_s)
            salt = bytes.fromhex(salt_hex)
        except (ValueError, TypeError):
            return False
        digest = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, candidate.encode("utf-8"), salt, rounds)
        return hmac.compare_digest(digest.hex(), digest_hex)

    return constant_time_compare(candidate, stored)


def generate_secret(nbytes: int = 32) -> str:
    """Generate a URL-safe random secret. Use this, never uuid4 or random."""
    return _secrets.token_urlsafe(nbytes)

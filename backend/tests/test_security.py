"""Tests for the reusable security module."""
import asyncio

import pytest

from backend.security import (
    RateLimiter,
    RateLimitExceeded,
    UploadRejected,
    constant_time_compare,
    escape_html,
    hash_secret,
    sanitize_for_spreadsheet,
    validate_upload,
    verify_secret,
)
from backend.security.bots import honeypot_tripped
from backend.security.tokens import (
    InvalidResourceToken,
    sign_resource_token,
    verify_resource_token,
)

KEY = b"0123456789abcdef0123456789abcdef"


# --- Item 6/10: secret comparison and storage ---------------------------------
def test_constant_time_compare():
    assert constant_time_compare("abc", "abc")
    assert not constant_time_compare("abc", "abd")
    assert not constant_time_compare("abc", "abcd")


def test_hash_and_verify_secret():
    stored = hash_secret("s3cr3t")
    assert "s3cr3t" not in stored
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_secret("s3cr3t", stored)
    assert not verify_secret("wrong", stored)


def test_verify_secret_accepts_plaintext_for_shared_secrets():
    assert verify_secret("token", "token")
    assert not verify_secret("token", "other")


def test_verify_secret_rejects_malformed_hash():
    assert not verify_secret("x", "pbkdf2_sha256$broken")


# --- Item 7: resource tokens --------------------------------------------------
def test_resource_token_roundtrip():
    token = sign_resource_token("res-1", KEY, scope="s")
    verify_resource_token(token, "res-1", KEY, scope="s")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"resource_id": "res-2"},          # different resource
        {"scope": "other"},                # different scope
        {"key": b"f" * 32},                # different key
    ],
)
def test_resource_token_is_bound_to_its_inputs(kwargs):
    token = sign_resource_token("res-1", KEY, scope="s")
    args = {"resource_id": "res-1", "key": KEY, "scope": "s", **kwargs}
    with pytest.raises(InvalidResourceToken):
        verify_resource_token(token, args["resource_id"], args["key"], scope=args["scope"])


def test_resource_token_expires():
    token = sign_resource_token("res-1", KEY, ttl_seconds=10, scope="s", now=1_000)
    verify_resource_token(token, "res-1", KEY, scope="s", now=1_005)
    with pytest.raises(InvalidResourceToken):
        verify_resource_token(token, "res-1", KEY, scope="s", now=1_011)


def test_resource_token_expiry_cannot_be_extended():
    """Rewriting the expiry in the token must invalidate the signature."""
    token = sign_resource_token("res-1", KEY, ttl_seconds=10, scope="s", now=1_000)
    _, signature = token.split(".", 1)
    forged = f"{9_999_999}.{signature}"
    with pytest.raises(InvalidResourceToken):
        verify_resource_token(forged, "res-1", KEY, scope="s", now=1_005)


# --- Item 11: rate limiting ---------------------------------------------------
def test_rate_limiter_blocks_over_the_limit():
    limiter = RateLimiter(3, 60, name="t")

    async def run():
        for _ in range(3):
            await limiter.check("ip")
        with pytest.raises(RateLimitExceeded):
            await limiter.check("ip")

    asyncio.run(run())


def test_rate_limiter_is_per_key():
    limiter = RateLimiter(1, 60, name="t")

    async def run():
        await limiter.check("a")
        await limiter.check("b")  # a different key has its own budget

    asyncio.run(run())


def test_rate_limiter_reset_clears_history():
    limiter = RateLimiter(1, 60, name="t")

    async def run():
        await limiter.check("ip")
        await limiter.reset("ip")
        await limiter.check("ip")

    asyncio.run(run())


def test_rate_limiter_window_slides():
    limiter = RateLimiter(1, 0.05, name="t")

    async def run():
        await limiter.check("ip")
        await asyncio.sleep(0.06)
        await limiter.check("ip")

    asyncio.run(run())


# --- Item 15: escaping --------------------------------------------------------
@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        "' onmouseover='alert(1)",
    ],
)
def test_escape_html_neutralises_injection(payload):
    escaped = escape_html(payload)
    assert "<" not in escaped
    assert ">" not in escaped
    assert '"' not in escaped
    assert "'" not in escaped


def test_escape_html_handles_none():
    assert escape_html(None) == ""


# --- Item 13 analogue: spreadsheet formula injection --------------------------
@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_sanitize_for_spreadsheet_prefixes_formulas(prefix):
    assert sanitize_for_spreadsheet(f"{prefix}CMD()").startswith("'")


def test_sanitize_for_spreadsheet_leaves_normal_text_alone():
    assert sanitize_for_spreadsheet("Maria Silva") == "Maria Silva"


# --- Item 16: upload restriction ---------------------------------------------
IMAGES = frozenset({"png", "jpg"})
TYPES = frozenset({"image/png", "image/jpeg"})


def test_validate_upload_accepts_a_good_file():
    assert validate_upload("photo.png", "image/png", 1_000, allowed_extensions=IMAGES,
                           allowed_content_types=TYPES, max_bytes=10_000) == "photo.png"


def test_validate_upload_strips_path_components():
    assert validate_upload("../../etc/passwd.png", "image/png", 10, allowed_extensions=IMAGES,
                           allowed_content_types=TYPES, max_bytes=10_000) == "passwd.png"


@pytest.mark.parametrize(
    "filename,content_type,size",
    [
        ("evil.php", "image/png", 10),        # extension not allowed
        ("evil.png", "text/html", 10),        # content type not allowed
        ("big.png", "image/png", 999_999),    # too large
        ("empty.png", "image/png", 0),        # empty
        ("noext", "image/png", 10),           # no extension
        (".hidden.png", "image/png", 10),     # dotfile
    ],
)
def test_validate_upload_rejects_bad_files(filename, content_type, size):
    with pytest.raises(UploadRejected):
        validate_upload(filename, content_type, size, allowed_extensions=IMAGES,
                        allowed_content_types=TYPES, max_bytes=100_000)


# --- Item 12: honeypot --------------------------------------------------------
def test_honeypot():
    assert honeypot_tripped("filled in")
    assert not honeypot_tripped("")
    assert not honeypot_tripped(None)
    assert not honeypot_tripped("   ")

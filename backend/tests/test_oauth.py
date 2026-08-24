"""OAuth flow hardening (items 6, 11, 14)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.oauth import _pack_state, _unpack_state
from backend.security.tokens import InvalidResourceToken


def test_state_roundtrip():
    assert _unpack_state(_pack_state(("ig", "bio", "launch"))) == ("ig", "bio", "launch")


@pytest.mark.parametrize(
    "state",
    [
        "",
        "ig|bio|launch",                        # unsigned, as the old flow produced
        "ig|bio|launch|1|deadbeef",             # bogus signature
        "attacker|bio|launch|1|",               # tampered payload, no signature
    ],
)
def test_unsigned_or_tampered_state_is_rejected(state):
    """An unsigned OAuth state is the CSRF hole in the login flow."""
    with pytest.raises(InvalidResourceToken):
        _unpack_state(state)


def test_tampered_utm_invalidates_the_state():
    state = _pack_state(("ig", "bio", "launch"))
    source, medium, campaign, nonce, signature = state.split("|")
    with pytest.raises(InvalidResourceToken):
        _unpack_state(f"attacker|{medium}|{campaign}|{nonce}|{signature}")


def test_callback_with_a_forged_state_redirects_to_error(client):
    resp = client.get(
        "/oauth/callback",
        params={"code": "abc", "state": "ig|bio|launch"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "reason=oauth_denied" in resp.headers["location"]


def test_start_redirects_to_meta_with_a_signed_state(client):
    resp = client.get("/oauth/start", params={"utm_source": "ig"}, follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://www.facebook.com/dialog/oauth?")
    assert "state=" in location
    # The client secret must never appear in a redirect the browser can read.
    assert "client_secret" not in location


def test_utm_values_are_sanitised_and_bounded(client):
    """A UTM ends up in a URL and a spreadsheet — it must not carry markup."""
    resp = client.get(
        "/oauth/start",
        params={"utm_source": "<script>alert(1)</script>" + "x" * 500},
        follow_redirects=False,
    )
    location = resp.headers["location"]
    assert "script" in location  # letters survive
    assert "%3C" not in location and "<" not in location  # angle brackets do not


def test_callback_redirects_to_the_configured_frontend(client):
    """The redirect target comes from config, never from the request (open redirect)."""
    token_resp = MagicMock(status_code=200)
    token_resp.json.return_value = {"access_token": "tok"}
    me_resp = MagicMock(status_code=200)
    me_resp.json.return_value = {"id": "1", "username": "user", "account_type": "BUSINESS"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=[token_resp, me_resp]
        )
        resp = client.get(
            "/oauth/callback",
            params={"code": "abc", "state": _pack_state(("ig", "", ""))},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://front.example.com/questionnaire.html")
    assert "t=" in location  # the session access token is handed over

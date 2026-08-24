from unittest.mock import AsyncMock, MagicMock, patch


def _charge_response(session_id):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "charge": {"correlationID": session_id, "brCode": "00020126...", "globalID": "charge_abc"}
    }
    return resp


def test_checkout_creates_openpix_charge(client, new_session, auth_headers):
    session, token = new_session(name="Test User", email="test@example.com")

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=_charge_response(session.session_id)
        )
        resp = client.post(f"/checkout/{session.session_id}", headers=auth_headers(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["br_code"] == "00020126..."
    assert body["amount"] == 6700  # default price, decided server-side


def test_checkout_status_returns_pending(client, new_session, auth_headers):
    session, token = new_session(name="Test User", email="test@example.com")
    resp = client.get(f"/checkout/status/{session.session_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == {"payment_status": "pending"}


# --- Item 7 -------------------------------------------------------------------
def test_checkout_rejects_foreign_token(client, new_session, auth_headers):
    victim, _ = new_session(name="V", email="v@example.com")
    _, attacker_token = new_session()

    resp = client.post(f"/checkout/{victim.session_id}", headers=auth_headers(attacker_token))
    assert resp.status_code == 404


def test_checkout_status_requires_token(client, new_session):
    session, _ = new_session(name="V", email="v@example.com")
    assert client.get(f"/checkout/status/{session.session_id}").status_code == 404


# --- Item 8: the client cannot set its own price ------------------------------
def test_checkout_ignores_a_client_supplied_amount(client, new_session, auth_headers):
    session, token = new_session(name="Test User", email="test@example.com")

    with patch("httpx.AsyncClient") as mock_client:
        post = AsyncMock(return_value=_charge_response(session.session_id))
        mock_client.return_value.__aenter__.return_value.post = post
        resp = client.post(
            f"/checkout/{session.session_id}",
            json={"value": 1, "amount": 1},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert post.call_args.kwargs["json"]["value"] == 6700


def test_checkout_requires_a_completed_questionnaire(client, new_session, auth_headers):
    session, token = new_session()  # no name/email yet
    resp = client.post(f"/checkout/{session.session_id}", headers=auth_headers(token))
    assert resp.status_code == 400


# --- Item 17: the provider's error body never reaches the client --------------
def test_provider_error_is_not_echoed(client, new_session, auth_headers):
    session, token = new_session(name="Test User", email="test@example.com")
    failing = MagicMock()
    failing.status_code = 401
    failing.json.return_value = {"error": "invalid AppID sk_live_supersecret"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=failing)
        resp = client.post(f"/checkout/{session.session_id}", headers=auth_headers(token))

    assert resp.status_code == 502
    assert "sk_live_supersecret" not in resp.text

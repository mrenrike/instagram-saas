import hashlib
import hmac
import json
from unittest.mock import patch

from backend.tests.conftest import _TEST_ENV

WEBHOOK_SECRET = _TEST_ENV["OPENPIX_WEBHOOK_SECRET"]


def sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _completed(session_id: str) -> bytes:
    return json.dumps({"charge": {"status": "COMPLETED", "correlationID": session_id}}).encode()


def test_webhook_rejects_invalid_signature(client):
    payload = _completed("00000000-0000-4000-8000-000000000000")
    resp = client.post(
        "/webhook/openpix",
        content=payload,
        headers={"x-webhook-token": "badsig", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401


def test_webhook_rejects_missing_signature(client):
    payload = _completed("00000000-0000-4000-8000-000000000000")
    resp = client.post(
        "/webhook/openpix", content=payload, headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401


def test_webhook_accepts_valid_signature_and_marks_paid(client, new_session):
    from backend.session import load_session

    session, _ = new_session(instagram_handle="@u")
    payload = _completed(session.session_id)

    with patch("backend.webhook.asyncio") as mock_asyncio:
        mock_asyncio.create_task = lambda coro: coro.close()
        resp = client.post(
            "/webhook/openpix",
            content=payload,
            headers={"x-webhook-token": sign(payload), "Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    assert load_session(session.session_id).payment_status == "paid"


def test_webhook_is_idempotent(client, new_session):
    from backend.session import load_session, save_session

    session, _ = new_session()
    session.payment_status = "paid"
    save_session(session)
    payload = _completed(session.session_id)

    with patch("backend.webhook.asyncio") as mock_asyncio:
        called = []
        mock_asyncio.create_task = lambda coro: (called.append(1), coro.close())
        resp = client.post(
            "/webhook/openpix",
            content=payload,
            headers={"x-webhook-token": sign(payload), "Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    assert called == []  # the pipeline is not re-queued
    assert load_session(session.session_id).payment_status == "paid"


# --- Item 14 ------------------------------------------------------------------
def test_webhook_with_traversal_correlation_id_is_ignored(client):
    payload = json.dumps(
        {"charge": {"status": "COMPLETED", "correlationID": "../../../etc/passwd"}}
    ).encode()
    resp = client.post(
        "/webhook/openpix",
        content=payload,
        headers={"x-webhook-token": sign(payload), "Content-Type": "application/json"},
    )
    assert resp.status_code == 200  # accepted and discarded, never a filesystem read


def test_webhook_rejects_malformed_json(client):
    payload = b"{not json"
    resp = client.post(
        "/webhook/openpix",
        content=payload,
        headers={"x-webhook-token": sign(payload), "Content-Type": "application/json"},
    )
    assert resp.status_code == 400

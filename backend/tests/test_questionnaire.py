import json

from backend.session import load_session

VALID_BODY = {
    "name": "Test User",
    "email": "test@example.com",
    "niche": "Fitness",
    "goal": "Crescer seguidores",
    "audience": "Jovens 18-25",
    "tone": "Descontraído",
    "management_style": "solo",
    "competitors": [],
    "extra_context": "",
}


def test_questionnaire_saves_data(client, new_session, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.coupons.COUPONS_FILE", str(tmp_path / "coupons.json"))
    session, token = new_session()

    resp = client.post(
        f"/questionnaire/{session.session_id}", json=VALID_BODY, headers=auth_headers(token)
    )

    assert resp.status_code == 200
    updated = load_session(session.session_id)
    assert updated.name == "Test User"
    assert updated.questionnaire.niche == "Fitness"
    assert updated.questionnaire.management_style == "solo"


def test_questionnaire_unknown_session_returns_404(client):
    resp = client.post(
        "/questionnaire/00000000-0000-4000-8000-000000000000",
        json=VALID_BODY,
        headers={"X-Session-Token": "nope"},
    )
    assert resp.status_code == 404


def test_questionnaire_invalid_coupon_returns_400(client, new_session, auth_headers, tmp_path, monkeypatch):
    coupon_file = tmp_path / "coupons.json"
    coupon_file.write_text(json.dumps({}))
    monkeypatch.setattr("backend.coupons.COUPONS_FILE", str(coupon_file))
    session, token = new_session()

    resp = client.post(
        f"/questionnaire/{session.session_id}",
        json={**VALID_BODY, "coupon_code": "BADCODE"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 400
    assert "Cupom" in resp.json()["detail"]


# --- Item 7: another session's token must not work ---------------------------
def test_questionnaire_rejects_token_from_another_session(client, new_session, auth_headers):
    victim, _ = new_session()
    _, attacker_token = new_session()

    resp = client.post(
        f"/questionnaire/{victim.session_id}",
        json=VALID_BODY,
        headers=auth_headers(attacker_token),
    )

    assert resp.status_code == 404


def test_questionnaire_requires_a_token(client, new_session):
    session, _ = new_session()
    resp = client.post(f"/questionnaire/{session.session_id}", json=VALID_BODY)
    assert resp.status_code == 404


# --- Item 8: field tampering -------------------------------------------------
def test_unknown_fields_are_rejected(client, new_session, auth_headers):
    session, token = new_session()
    resp = client.post(
        f"/questionnaire/{session.session_id}",
        json={**VALID_BODY, "discount_applied": 6700, "payment_status": "paid"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422

    assert load_session(session.session_id).payment_status == "pending"


def test_price_is_not_taken_from_the_client(client, new_session, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.coupons.COUPONS_FILE", str(tmp_path / "coupons.json"))
    session, token = new_session()

    resp = client.post(
        f"/questionnaire/{session.session_id}", json=VALID_BODY, headers=auth_headers(token)
    )

    assert resp.json()["final_price"] == 6700


# --- Item 14: input validation -----------------------------------------------
def test_overlong_field_is_rejected(client, new_session, auth_headers):
    session, token = new_session()
    resp = client.post(
        f"/questionnaire/{session.session_id}",
        json={**VALID_BODY, "extra_context": "x" * 5_000},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_unknown_management_style_is_rejected(client, new_session, auth_headers):
    session, token = new_session()
    resp = client.post(
        f"/questionnaire/{session.session_id}",
        json={**VALID_BODY, "management_style": "admin"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_invalid_email_is_rejected(client, new_session, auth_headers):
    session, token = new_session()
    resp = client.post(
        f"/questionnaire/{session.session_id}",
        json={**VALID_BODY, "email": "not-an-email"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


# --- Item 12: bot protection -------------------------------------------------
def test_honeypot_submission_is_rejected(client, new_session, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.coupons.COUPONS_FILE", str(tmp_path / "coupons.json"))
    session, token = new_session()

    resp = client.post(
        f"/questionnaire/{session.session_id}",
        json={**VALID_BODY, "website": "http://spam.example"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 400
    assert load_session(session.session_id).name == ""

import pytest

from backend.session import (
    InvalidSessionId,
    Session,
    SessionAccessDenied,
    SessionNotFound,
    issue_access_token,
    load_session,
    require_access,
    save_session,
    validate_session_id,
)


def test_session_encrypt_decrypt_roundtrip():
    s = Session.new(instagram_handle="@test", account_type="BUSINESS", access_token="secret_token")
    save_session(s)
    loaded = load_session(s.session_id)
    assert loaded.instagram_handle == "@test"
    assert loaded.access_token == "secret_token"
    assert loaded.pipeline_status == "waiting_payment"


def test_access_token_not_in_file_plaintext(tmp_path):
    s = Session.new(instagram_handle="@x", account_type="CREATOR", access_token="supersecret")
    save_session(s)
    enc_file = next((tmp_path / "sessions").glob("*.enc"))
    assert b"supersecret" not in enc_file.read_bytes()


def test_session_file_is_owner_only(tmp_path):
    s = Session.new("@x", "CREATOR", "tok")
    save_session(s)
    enc_file = next((tmp_path / "sessions").glob("*.enc"))
    assert enc_file.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "sessions").stat().st_mode & 0o777 == 0o700


def test_load_missing_session_raises():
    with pytest.raises(SessionNotFound):
        load_session("00000000-0000-4000-8000-000000000000")


# --- Item 14: path traversal --------------------------------------------------
@pytest.mark.parametrize(
    "bad_id",
    [
        "../../etc/passwd",
        "..%2f..%2fetc%2fpasswd",
        "/etc/passwd",
        "nonexistent-id",
        "",
        "0000000-0000-4000-8000-000000000000",  # one digit short
    ],
)
def test_non_uuid_session_id_is_rejected(bad_id):
    with pytest.raises(InvalidSessionId):
        validate_session_id(bad_id)


def test_traversal_id_never_reaches_the_filesystem(tmp_path):
    """A traversal attempt must fail on validation, not by happening to miss a file."""
    with pytest.raises(InvalidSessionId):
        load_session("../../../../etc/passwd")


# --- Item 7: record access control -------------------------------------------
def test_valid_token_grants_access():
    s = Session.new("@x", "BUSINESS", "tok")
    save_session(s)
    assert require_access(s.session_id, issue_access_token(s.session_id)) == s.session_id


def test_token_for_another_session_is_rejected():
    a = Session.new("@a", "BUSINESS", "tok")
    b = Session.new("@b", "BUSINESS", "tok")
    save_session(a)
    save_session(b)
    with pytest.raises(SessionAccessDenied):
        require_access(a.session_id, issue_access_token(b.session_id))


def test_missing_or_tampered_token_is_rejected():
    s = Session.new("@x", "BUSINESS", "tok")
    save_session(s)
    token = issue_access_token(s.session_id)
    with pytest.raises(SessionAccessDenied):
        require_access(s.session_id, "")
    with pytest.raises(SessionAccessDenied):
        require_access(s.session_id, token[:-4] + "AAAA")


def test_expired_token_is_rejected(monkeypatch):
    import backend.session as session_module

    s = Session.new("@x", "BUSINESS", "tok")
    save_session(s)
    token = issue_access_token(s.session_id)

    real_verify = session_module.verify_resource_token
    monkeypatch.setattr(
        session_module,
        "verify_resource_token",
        lambda t, rid, key, scope="": real_verify(t, rid, key, scope=scope, now=2**31),
    )
    with pytest.raises(SessionAccessDenied):
        require_access(s.session_id, token)


# --- Item 17: minimal responses ----------------------------------------------
def test_public_view_hides_secrets():
    s = Session.new("@x", "BUSINESS", "tok")
    s.email = "user@example.com"
    s.pipeline_error = "Traceback: /app/backend/pipeline.py line 42"
    view = s.public_view()
    assert "access_token" not in view
    assert "email" not in view
    assert "pipeline_error" not in view

"""Email verification uses a mocked Resend client and never sends a real message."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from database import SessionLocal
from models.user import User
from services.email_service import EmailDeliveryError, send_verification_email


@pytest.fixture(autouse=True)
def require_email_verification(monkeypatch):
    monkeypatch.setattr("services.user_services.EMAIL_VERIFICATION_ENABLED", True)


def _otp(monkeypatch):
    monkeypatch.setattr("services.user_services.secrets.randbelow", lambda _n: 123456)
    return "123456"


def _register(client, monkeypatch, email="otp.user@example.com"):
    _otp(monkeypatch)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.delete(existing)
            db.commit()
    finally:
        db.close()
    response = client.post(
        "/users/register",
        json={"email": email, "password": "VerifyPass123", "role": "candidate"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_verification_can_be_turned_off(client, monkeypatch):
    monkeypatch.setattr("services.user_services.EMAIL_VERIFICATION_ENABLED", False)
    email = "open.signup@example.com"
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.delete(existing)
            db.commit()
    finally:
        db.close()
    with patch("services.user_services.send_verification_email") as mailer:
        response = client.post(
            "/users/register",
            json={"email": email, "password": "VerifyPass123", "role": "candidate"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["verified"] is True
    mailer.assert_not_called()
    login = client.post("/auth/login", data={"username": email, "password": "VerifyPass123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200


def test_register_sends_code_and_blocks_login_until_verified(client, monkeypatch):
    calls = []

    def fake_send(to_email, otp, expires_at):
        calls.append({"to": to_email, "otp": otp})
        return {"accepted": True, "provider_id": "email_test_1"}

    with patch("services.user_services.send_verification_email", side_effect=fake_send):
        body = _register(client, monkeypatch, "new.otp@example.com")

    assert body["verification_email_sent"] is True
    assert body["verified"] is False
    assert "otp" not in body
    assert calls[0]["otp"] == "123456"
    assert calls[0]["to"] == "new.otp@example.com"

    login = client.post("/auth/login", data={"username": "new.otp@example.com", "password": "VerifyPass123"})
    assert login.status_code == 403
    assert "verify" in login.json()["detail"].lower()


def test_valid_otp_verifies_and_cannot_be_reused(client, monkeypatch):
    with patch("services.user_services.send_verification_email", return_value={"accepted": True, "provider_id": "email_test_2"}):
        _register(client, monkeypatch, "reuse.otp@example.com")

    ok = client.post("/auth/verify-email", json={"email": "reuse.otp@example.com", "otp": "123456"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["detail"] == "Email verified successfully."

    again = client.post("/auth/verify-email", json={"email": "reuse.otp@example.com", "otp": "123456"})
    assert again.status_code == 200
    assert again.json()["detail"] == "Email already verified."

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "reuse.otp@example.com").first()
        assert user.is_verified is True
        assert user.verification_token_hash is None
    finally:
        db.close()

    login = client.post("/auth/login", data={"username": "reuse.otp@example.com", "password": "VerifyPass123"})
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_invalid_and_unknown_otp_use_the_same_error(client, monkeypatch):
    with patch("services.user_services.send_verification_email", return_value={"accepted": True, "provider_id": "email_test_3"}):
        _register(client, monkeypatch, "wrong.otp@example.com")

    wrong = client.post("/auth/verify-email", json={"email": "wrong.otp@example.com", "otp": "000000"})
    missing = client.post("/auth/verify-email", json={"email": "nobody.otp@example.com", "otp": "000000"})
    assert wrong.status_code == 400
    assert missing.status_code == 400
    assert wrong.json()["detail"] == missing.json()["detail"] == "Invalid or expired code."


def test_expired_otp_is_rejected(client, monkeypatch):
    with patch("services.user_services.send_verification_email", return_value={"accepted": True, "provider_id": "email_test_4"}):
        _register(client, monkeypatch, "expired.otp@example.com")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "expired.otp@example.com").first()
        user.verification_token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    response = client.post("/auth/verify-email", json={"email": "expired.otp@example.com", "otp": "123456"})
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


def test_attempt_limit_retires_the_code(client, monkeypatch):
    with patch("services.user_services.send_verification_email", return_value={"accepted": True, "provider_id": "email_test_5"}):
        _register(client, monkeypatch, "limited.otp@example.com")

    for _ in range(4):
        response = client.post("/auth/verify-email", json={"email": "limited.otp@example.com", "otp": "000000"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired code."

    locked = client.post("/auth/verify-email", json={"email": "limited.otp@example.com", "otp": "000000"})
    assert locked.status_code == 400
    assert "too many" in locked.json()["detail"].lower()

    correct = client.post("/auth/verify-email", json={"email": "limited.otp@example.com", "otp": "123456"})
    assert correct.status_code == 400
    assert "too many" in correct.json()["detail"].lower()


def test_resend_cooldown_and_later_resend(client, monkeypatch):
    calls = {"count": 0}

    def fake_send(to_email, otp, expires_at):
        calls["count"] += 1
        return {"accepted": True, "provider_id": f"email_test_{calls['count']}"}

    with patch("services.user_services.send_verification_email", side_effect=fake_send):
        _register(client, monkeypatch, "resend.otp@example.com")
        cooling = client.post("/auth/resend-otp", json={"email": "resend.otp@example.com"})
        assert cooling.status_code == 200
        assert "wait" in cooling.json()["detail"].lower()
        assert cooling.json()["retry_after_seconds"] <= 60
        assert calls["count"] == 1

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "resend.otp@example.com").first()
            user.verification_token_sent_at = datetime.now(timezone.utc) - timedelta(seconds=90)
            db.commit()
        finally:
            db.close()

        sent = client.post("/auth/resend-otp", json={"email": "resend.otp@example.com"})
        assert sent.status_code == 200
        assert calls["count"] == 2


def test_resend_does_not_reveal_unknown_email(client):
    with patch("services.user_services.send_verification_email") as mailer:
        response = client.post("/auth/resend-otp", json={"email": "unknown.otp@example.com"})
    assert response.status_code == 200
    assert "waiting for verification" in response.json()["detail"].lower()
    mailer.assert_not_called()


def test_duplicate_verified_registration_is_rejected(client, monkeypatch):
    with patch("services.user_services.send_verification_email", return_value={"accepted": True, "provider_id": "email_test_6"}):
        _register(client, monkeypatch, "dup.otp@example.com")
    client.post("/auth/verify-email", json={"email": "dup.otp@example.com", "otp": "123456"})
    again = client.post(
        "/users/register",
        json={"email": "dup.otp@example.com", "password": "VerifyPass123", "role": "candidate"},
    )
    assert again.status_code == 400
    assert "sign in" in again.json()["detail"].lower()


def test_register_reports_resend_failure_without_leaking_secrets(client, monkeypatch):
    def explode(to_email, otp, expires_at):
        raise EmailDeliveryError("invalid_api_key", status_code=401)

    with patch("services.user_services.send_verification_email", side_effect=explode):
        body = _register(client, monkeypatch, "failed.otp@example.com")
    assert body["verification_email_sent"] is False
    assert "invalid_api_key" not in body["detail"]
    assert "123456" not in body["detail"]


def test_resend_client_classifies_provider_errors(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_FROM", "RecruitAI <noreply@example.com>")

    class Response:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.content = b"{}"

        def json(self):
            return self._payload

    def post(url, json, headers, timeout):
        assert url == "https://api.resend.com/emails"
        assert headers["Authorization"] == "Bearer re_test_key"
        assert json["to"] == ["person@example.com"]
        assert "re_test_key" not in json["html"]
        return Response(200, {"id": "email_123"})

    monkeypatch.setattr("services.email_service.requests.post", post)
    result = send_verification_email("person@example.com", "654321", datetime.now(timezone.utc))
    assert result["accepted"] is True
    assert result["provider_id"] == "email_123"

    def rejected(url, json, headers, timeout):
        return Response(403, {"name": "validation_error", "message": "The from domain is not verified"})

    monkeypatch.setattr("services.email_service.requests.post", rejected)
    with pytest.raises(EmailDeliveryError) as caught:
        send_verification_email("person@example.com", "654321", datetime.now(timezone.utc))
    assert caught.value.reason == "unverified_sender_domain"

    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    with pytest.raises(EmailDeliveryError) as missing:
        send_verification_email("person@example.com", "654321", datetime.now(timezone.utc))
    assert missing.value.reason == "missing_api_key"

"""Send verification email through Resend.

A 2xx response means Resend accepted the message. It does not mean the
recipient's mail server has delivered it.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

RESEND_EMAILS_URL = "https://api.resend.com/emails"
_REQUEST_TIMEOUT_SECONDS = 10


class EmailDeliveryError(Exception):
    """Raised when Resend does not accept a verification email."""

    def __init__(self, reason: str, status_code: int | None = None):
        self.reason = reason
        self.status_code = status_code
        super().__init__(reason)


def _classify_resend_failure(status_code: int, payload: dict) -> str:
    name = str(payload.get("name") or "").lower()
    message = str(payload.get("message") or "").lower()
    combined = f"{name} {message}"
    if status_code == 401 or "api key" in combined or "invalid_api_key" in combined:
        return "invalid_api_key"
    if status_code == 429 or "rate" in combined:
        return "rate_limited"
    if "domain" in combined or "not verified" in combined or "verify" in combined and "from" in combined:
        return "unverified_sender_domain"
    if status_code in (400, 422) or "recipient" in combined or "email" in combined:
        return "invalid_recipient"
    return "api_failure"


def send_verification_email(to_email: str, otp: str, expires_at):
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    sender = (os.getenv("EMAIL_FROM") or "").strip()
    recipient_domain = to_email.split("@")[-1] if "@" in to_email else "invalid"

    if not api_key:
        logger.error("email.resend_not_configured reason=missing_api_key")
        raise EmailDeliveryError("missing_api_key")
    if not sender:
        logger.error("email.resend_not_configured reason=missing_sender")
        raise EmailDeliveryError("missing_sender")

    logger.info(
        "email.resend_request recipient_domain=%s sender_configured=true",
        recipient_domain,
    )

    payload = {
        "from": sender,
        "to": [to_email],
        "subject": "Your RecruitAI verification code",
        "html": (
            "<p>Use this code to verify your RecruitAI account:</p>"
            f"<p style=\"font-size:24px;letter-spacing:4px;font-weight:700\">{otp}</p>"
            "<p>This code expires in 5 minutes. If you did not create an account, you can ignore this email.</p>"
        ),
        "text": (
            f"Your RecruitAI verification code is {otp}. "
            "It expires in 5 minutes. If you did not create an account, you can ignore this email."
        ),
    }

    try:
        response = requests.post(
            RESEND_EMAILS_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        logger.exception("email.resend_network_failure recipient_domain=%s", recipient_domain)
        raise EmailDeliveryError("network")

    body = {}
    try:
        if response.content:
            body = response.json()
    except ValueError:
        body = {}

    accepted = response.status_code in (200, 201)
    logger.info(
        "email.resend_response status=%s accepted=%s provider_id=%s",
        response.status_code,
        accepted,
        body.get("id") if accepted else None,
    )

    if not accepted:
        reason = _classify_resend_failure(response.status_code, body if isinstance(body, dict) else {})
        logger.error(
            "email.resend_rejected status=%s reason=%s",
            response.status_code,
            reason,
        )
        raise EmailDeliveryError(reason, status_code=response.status_code)

    return {
        "accepted": True,
        "provider_id": body.get("id"),
        "expires_at": expires_at.isoformat() if hasattr(expires_at, "isoformat") else None,
    }

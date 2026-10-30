import os
import requests
from datetime import datetime


def send_verification_email(
    to_email: str,
    otp: str,
    expires_at: datetime
):

    webhook_url = os.getenv(
        "N8N_OTP_WEBHOOK_URL"
    )

    if not webhook_url:
        raise RuntimeError(
            "N8N_OTP_WEBHOOK_URL is not configured"
        )

    payload = {
        "email": to_email,
        "otp": otp,
        "expires_at": expires_at.isoformat()
    }

    response = requests.post(
        webhook_url,
        json=payload,
        timeout=10
    )

    if response.status_code >= 400:

        raise RuntimeError(
            f"n8n webhook failed: "
            f"{response.status_code} "
            f"{response.text}"
        )

    return response.json() if response.content else {
        "success": True
    }
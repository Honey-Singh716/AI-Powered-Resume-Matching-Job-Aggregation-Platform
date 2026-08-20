import os
import requests
from datetime import datetime

RESEND_API_URL = "https://api.resend.com/emails"


def _get_env(name, required=False):
    v = os.getenv(name)
    if required and not v:
        raise RuntimeError(f"Environment variable {name} is required")
    return v


def send_verification_email(to_email: str, raw_token: str, expires_at: datetime):
    """Send a verification email using Resend.

    The function expects these environment variables:
      - RESEND_API_KEY
      - EMAIL_FROM
      - FRONTEND_URL

    The verification link will be FRONTEND_URL + "/auth/verify-email?token=<token>"
    """
    api_key = _get_env('RESEND_API_KEY', required=True)
    email_from = _get_env('EMAIL_FROM', required=True)
    frontend = _get_env('FRONTEND_URL', required=True).rstrip('/')

    verify_path = f"{frontend}/auth/verify-email?token={raw_token}"

    subject = "Verify your email — AI Recruitment Platform"

    html = f"""
    <html>
      <body>
        <p>Hi,</p>
        <p>Thanks for creating an account on our platform. Please verify your email by clicking the button below. The link will expire at {expires_at.isoformat()} UTC.</p>
        <p style=\"text-align:center\"><a href=\"{verify_path}\" style=\"display:inline-block;padding:12px 20px;background:#2563eb;color:#fff;text-decoration:none;border-radius:6px\">Verify Email</a></p>
        <p>If the button doesn't work, copy and paste this URL into your browser:</p>
        <p><small>{verify_path}</small></p>
        <hr>
        <p>If you did not create an account, you can ignore this message.</p>
      </body>
    </html>
    """

    payload = {
        "from": email_from,
        "to": [to_email],
        "subject": subject,
        "html": html
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    resp = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=10)
    if resp.status_code >= 400:
        raise RuntimeError(f"Failed to send email: {resp.status_code} {resp.text}")

    return resp.json()
import logging
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from repositories.user_repo_ext import (
    create_user,
    get_user_by_email,
    set_verification_token,
    clear_verification_token,
)

from services.auth_service import (
    SECRET_KEY,
    hash_password,
    verify_password,
    create_access_token,
)

from services.email_service import EmailDeliveryError, send_verification_email

logger = logging.getLogger(__name__)

# Keep the OTP mailer. Set this to True when registration and login must require email verification again.
EMAIL_VERIFICATION_ENABLED = False
OTP_TTL = timedelta(minutes=5)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_ATTEMPTS = 5


def _email_domain(email: str) -> str:
    return email.split("@")[-1] if email and "@" in email else "invalid"


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_otp(otp: str) -> str:
    return hmac.new(SECRET_KEY.encode(), otp.encode(), hashlib.sha256).hexdigest()


def _issue_otp(user, db):
    """Create a new single-use OTP. The plaintext is returned only to the mailer."""
    now = datetime.now(timezone.utc)
    sent_at = _as_utc(user.verification_token_sent_at)
    if sent_at is not None:
        elapsed = now - sent_at
        if elapsed < OTP_RESEND_COOLDOWN:
            retry_after = int((OTP_RESEND_COOLDOWN - elapsed).total_seconds()) + 1
            logger.info(
                "otp.resend_cooldown email_domain=%s retry_after_seconds=%s",
                _email_domain(user.email),
                retry_after,
            )
            return {"sent": False, "cooldown": True, "retry_after_seconds": max(retry_after, 1)}

    otp = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = now + OTP_TTL
    # sent_at is recorded only after Resend accepts the message
    set_verification_token(user, _hash_otp(otp), expires_at, None, db)
    logger.info("otp.generated email_domain=%s ttl_seconds=%s", _email_domain(user.email), int(OTP_TTL.total_seconds()))

    try:
        result = send_verification_email(user.email, otp, expires_at)
    except EmailDeliveryError as exc:
        logger.error(
            "otp.email_failed email_domain=%s reason=%s status=%s",
            _email_domain(user.email),
            exc.reason,
            exc.status_code,
        )
        return {"sent": False, "cooldown": False, "reason": exc.reason}
    except Exception:
        logger.exception("otp.email_failed email_domain=%s reason=unexpected", _email_domain(user.email))
        return {"sent": False, "cooldown": False, "reason": "unexpected"}

    user.verification_token_sent_at = now
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(
        "otp.email_accepted email_domain=%s provider_id=%s",
        _email_domain(user.email),
        result.get("provider_id"),
    )
    return {"sent": True, "cooldown": False, "retry_after_seconds": int(OTP_RESEND_COOLDOWN.total_seconds())}


def _find_user(email, db):
    typed = str(email or "").strip()
    normalized = typed.lower()
    user = get_user_by_email(normalized, db)
    if user or normalized == typed:
        return user
    return get_user_by_email(typed, db)


def save_user(user_data, db):
    email = str(user_data.email).strip().lower()
    logger.info("registration.requested email_domain=%s role=%s", _email_domain(email), user_data.role)

    existing_user = _find_user(email, db)

    if existing_user and getattr(existing_user, "is_verified", False):
        logger.info("registration.duplicate_verified email_domain=%s", _email_domain(email))
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please sign in.",
        )

    if existing_user:
        user = existing_user
        logger.info("registration.unverified_retry email_domain=%s", _email_domain(email))
    else:
        user = create_user(
            email,
            hash_password(user_data.password),
            user_data.role,
            db,
        )

    if not EMAIL_VERIFICATION_ENABLED:
        user.is_verified = True
        db.commit()
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "detail": "Account created successfully.",
            "verification_email_sent": False,
            "verified": True,
        }

    issued = _issue_otp(user, db)
    if issued.get("cooldown"):
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "detail": "A verification code was just sent. Please check your email.",
            "verification_email_sent": True,
            "verified": False,
            "retry_after_seconds": issued["retry_after_seconds"],
        }
    if not issued.get("sent"):
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "detail": "Account created, but the verification email could not be sent. You can request another code.",
            "verification_email_sent": False,
            "verified": False,
        }

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "detail": "Account created. A verification code was sent to your email.",
        "verification_email_sent": True,
        "verified": False,
        "retry_after_seconds": issued["retry_after_seconds"],
    }


def resend_verification(email, db):
    """Always use the same public response so this endpoint does not reveal which emails exist."""
    normalized = str(email).strip().lower()
    public = {
        "detail": "If an account is waiting for verification, a new code has been sent.",
        "retry_after_seconds": int(OTP_RESEND_COOLDOWN.total_seconds()),
    }
    user = _find_user(normalized, db)
    if not user or getattr(user, "is_verified", False):
        logger.info("otp.resend_skipped email_domain=%s", _email_domain(normalized))
        return public

    issued = _issue_otp(user, db)
    if issued.get("cooldown"):
        public["retry_after_seconds"] = issued["retry_after_seconds"]
        public["detail"] = "Please wait before requesting another code."
    elif not issued.get("sent"):
        public["detail"] = "We could not send a verification email right now. Please try again shortly."
    return public


def verify_email_otp(email, otp, db):
    normalized = str(email).strip().lower()
    code = (otp or "").strip()
    user = _find_user(normalized, db)
    invalid = HTTPException(status_code=400, detail="Invalid or expired code.")

    if not user:
        logger.info("otp.verify_failed email_domain=%s reason=unknown_email", _email_domain(normalized))
        raise invalid

    if getattr(user, "is_verified", False) and not user.verification_token_hash:
        return {"detail": "Email already verified."}

    if (user.verification_attempts or 0) >= OTP_MAX_ATTEMPTS or not user.verification_token_hash:
        clear_verification_token(user, db)
        logger.info("otp.verify_failed email_domain=%s reason=attempt_limit", _email_domain(normalized))
        raise HTTPException(status_code=400, detail="Too many incorrect attempts. Request a new code.")

    expires_at = _as_utc(user.verification_token_expires_at)
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        logger.info("otp.verify_failed email_domain=%s reason=expired", _email_domain(normalized))
        raise HTTPException(status_code=400, detail="This code has expired. Request a new code.")

    if not code.isdigit() or len(code) != 6 or not hmac.compare_digest(_hash_otp(code), user.verification_token_hash):
        user.verification_attempts = (user.verification_attempts or 0) + 1
        locked = user.verification_attempts >= OTP_MAX_ATTEMPTS
        if locked:
            user.verification_token_hash = None
            user.verification_token_expires_at = None
        db.add(user)
        db.commit()
        logger.info(
            "otp.verify_failed email_domain=%s reason=%s",
            _email_domain(normalized),
            "attempt_limit" if locked else "mismatch",
        )
        if locked:
            raise HTTPException(status_code=400, detail="Too many incorrect attempts. Request a new code.")
        raise invalid

    user.is_verified = True
    clear_verification_token(user, db)
    logger.info("otp.verify_success email_domain=%s", _email_domain(normalized))
    return {"detail": "Email verified successfully."}


def login_user(login_data, db):

    user = _find_user(login_data.email, db)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        login_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Email MUST be verified
    if EMAIL_VERIFICATION_ENABLED:

        if not getattr(user, "is_verified", False):

            raise HTTPException(
                status_code=403,
                detail="Please verify your email before logging in."
            )

    token = create_access_token({
        "sub": user.email,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
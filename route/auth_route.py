from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from types import SimpleNamespace

from database import get_db
from schemas.user import OTPVerify
from services.user_services import login_user, resend_verification, verify_email_otp


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


class ResendOTP(BaseModel):
    email: EmailStr


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form sends 'username' — we treat it as email
    login_data = SimpleNamespace(email=form_data.username, password=form_data.password)
    return login_user(login_data, db)


@router.post("/verify-email")
def verify_email(payload: OTPVerify, db: Session = Depends(get_db)):
    """Verify an email using a single-use OTP."""
    return verify_email_otp(payload.email, payload.otp, db)


@router.post("/resend-otp")
def resend_otp(payload: ResendOTP, db: Session = Depends(get_db)):
    """Send another verification code, with a 60 second cooldown."""
    return resend_verification(payload.email, db)

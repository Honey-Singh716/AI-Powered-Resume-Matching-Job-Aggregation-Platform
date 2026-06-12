from fastapi import APIRouter
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from database import get_db

from schemas.user import UserLogin

from services.user_services import login_user

router = APIRouter(
    prefix="/auth",
    tags=['Authentication']
)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):

    # OAuth2 form sends 'username' — we treat it as email
    from types import SimpleNamespace
    login_data = SimpleNamespace(email=form_data.username, password=form_data.password)
    return login_user(login_data,db)

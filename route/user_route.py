from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from services.user_services import save_user
from services.auth_service import current_user
from services.profile_service import build_account_profile
from database import get_db
from schemas.user import UserCreate, UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/register",response_model=UserResponse)
def register_user(user: UserCreate,db:Session = Depends(get_db)):

    return save_user(user,db)


@router.get("/me")
def get_me(db: Session = Depends(get_db), user=Depends(current_user)):
    """Account and editable profile for the signed-in user."""
    return build_account_profile(user, db)    
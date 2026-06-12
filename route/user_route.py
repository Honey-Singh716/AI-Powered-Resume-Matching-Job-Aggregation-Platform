from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from services.user_services import save_user
from database import get_db
from schemas.user import UserCreate, UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/register",response_model=UserResponse)
def register_user(user: UserCreate,db:Session = Depends(get_db)):

    return save_user(user,db)    
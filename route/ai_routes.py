from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

from schemas.chat import ChatRequest

from services.ai_service import ask_ai

router = APIRouter()


@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):

    response = ask_ai(
        request.message,
        request.candidate_id,
        request.role,
        db
    )

    return {
        "response": response
    }
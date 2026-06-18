from pydantic import BaseModel

from typing import Optional

class ChatRequest(BaseModel):
    message: str
    candidate_id: Optional[int] = None
    role: Optional[str] = None
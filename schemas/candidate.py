from pydantic import BaseModel
from typing import Optional

class CandidateResponse(BaseModel):
    id: int
    skills: str
    experience: str

    class Config:
        from_attributes = True
from pydantic import BaseModel
from typing import List

class ApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    status: str

    class Config:
        from_attributes = True

class ApplicantDetailResponse(BaseModel):
    application_id: int
    candidate_id: int
    skills: str
    experience: str
    match_score: float
    semantic_score: float
    status: str

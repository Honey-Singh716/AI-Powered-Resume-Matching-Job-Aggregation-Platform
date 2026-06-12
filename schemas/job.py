from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    title: str
    company: Optional[str] = "Not Specified"
    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    skills_required: str
    experience_required: Optional[str] = None
    job_url: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    source: str
    external_job_id: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RecommendedJobResponse(BaseModel):
    id: Optional[int] = None
    title: str
    company: str
    location: Optional[str] = None
    source: str
    job_url: Optional[str] = None
    similarity_score: float

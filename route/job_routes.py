from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from schemas.job import JobCreate, JobResponse, RecommendedJobResponse
from services.auth_service import current_user
from services.job_service import save_job, get_jobs_list, recommend_jobs_for_candidate

router = APIRouter()

@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_new_job(
    job_in: JobCreate,
    db: Session = Depends(get_db),
    user = Depends(current_user)
):
    """Endpoint for recruiters to manually create jobs."""
    if user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can create jobs")
    
    new_job = save_job(job_in.model_dump(), user.id, db)
    return new_job

@router.get("/jobs", response_model=List[JobResponse])
def read_jobs(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get list of all jobs (internal and external) with pagination and optional search filter."""
    return get_jobs_list(skip=skip, limit=limit, db=db, q=q)

@router.get("/recommended-jobs", response_model=List[RecommendedJobResponse])
def get_recommended_jobs_endpoint(
    limit: int = 10,
    skip: int = 0,
    db: Session = Depends(get_db),
    user = Depends(current_user)
):
    """Get top recommended jobs for the authenticated candidate based on resume embedding similarity."""
    if user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can request recommended jobs")
    
    return recommend_jobs_for_candidate(user_id=user.id, db=db, limit=limit, skip=skip)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import current_user
from services.application_service import apply_to_job, get_job_applicants, get_my_applications
from schemas.application import ApplicationResponse, ApplicantDetailResponse
from typing import List

from repositories.candidate_repo import get_candidate_by_id
from models.candidate import Candidate

router = APIRouter()

# Helper to find candidate_id for the logged-in user
def get_current_candidate(db: Session, user_id: int):
    # This is a bit tricky since we don't store candidate_id in the token,
    # but candidate has a user_id foreign key.
    candidate = db.query(Candidate).filter(Candidate.user_id == user_id).first()
    return candidate

@router.post("/apply/{job_id}", response_model=ApplicationResponse)
def apply_to_job_route(
    job_id: int, 
    db: Session = Depends(get_db), 
    user = Depends(current_user)
):
    if user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can apply to jobs")
    
    candidate = get_current_candidate(db, user.id)
    if not candidate:
         raise HTTPException(status_code=404, detail="Candidate profile not found. Please parse/upload a resume first.")

    return apply_to_job(candidate.id, job_id, db)

@router.get("/jobs/{job_id}/applicants", response_model=List[ApplicantDetailResponse])
def get_job_applicants_route(
    job_id: int, 
    db: Session = Depends(get_db), 
    user = Depends(current_user)
):
    if user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can view applicants")
    
    return get_job_applicants(job_id, db)

@router.get("/my-applications")
def get_my_applications_route(
    db: Session = Depends(get_db), 
    user = Depends(current_user)
):
    if user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can view their applications")
    
    candidate = get_current_candidate(db, user.id)
    if not candidate:
         return []

    return get_my_applications(candidate.id, db)

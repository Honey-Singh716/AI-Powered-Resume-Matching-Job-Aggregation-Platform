from fastapi import APIRouter, Depends, HTTPException
from fastapi import status


from sqlalchemy.orm import Session

from database import get_db
from services.auth_service import current_user
from services.match_service import match_candidate_to_job as calculate_match
from services.match_service import recommend_jobs

router = APIRouter()


@router.get("/match/{candidate_id}/{job_id}")
def match_candidate_to_job(
    candidate_id: int,
    job_id: int,
    db: Session = Depends(get_db)
):
    return calculate_match(candidate_id, job_id, db)


@router.get("/recommend/{candidate_id}")
def recommend_job_route(
    candidate_id: int,
    db:Session = Depends(get_db)
):
    
    return recommend_jobs(candidate_id,db)
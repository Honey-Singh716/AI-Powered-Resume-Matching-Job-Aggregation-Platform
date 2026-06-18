from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends
from schemas.resume import ResumeRequest
from database import get_db
from services.auth_service import current_user
from services.candidate_service import save_candidate
from services.ai_service import parse_resume
from repositories.candidate_repo import search_candidates

from PyPDF2 import PdfReader
import io



from models.candidate import Candidate




router = APIRouter()


@router.post("/parse_resume")
def resume_parser(
    resume: ResumeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(current_user)
):
    if current_user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can parse resumes")


    result = parse_resume(
        resume.resume_text
    )

    candidate = save_candidate(result,current_user.id,db)

    return {
        "id": candidate.id,
        "user_id" : candidate.user_id,
        "skills": candidate.skills,
        "experience": candidate.experience,
        "education": candidate.education
    }


@router.post("/upload_resume")
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(current_user)
):
    if current_user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can upload resumes")

    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Extract text from PDF
    contents = file.file.read()
    pdf_reader = PdfReader(io.BytesIO(contents))

    resume_text = ""
    for page in pdf_reader.pages:
        resume_text += page.extract_text() or ""

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    # Send to Groq AI for parsing (same as /parse_resume)
    result = parse_resume(resume_text)

    # Save candidate to DB
    candidate = save_candidate(result, current_user.id, db)

    return {
        "id": candidate.id,
        "user_id": candidate.user_id,
        "skills": candidate.skills,
        "experience": candidate.experience,
        "education": candidate.education
    }


@router.get("/my-profile")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user = Depends(current_user)
):
    if current_user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates have profiles")
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="No profile found")
    return {
        "id": candidate.id,
        "user_id": candidate.user_id,
        "skills": candidate.skills,
        "experience": candidate.experience,
        "education": candidate.education
    }





@router.get("/candidates/search")
def search_for_candidates(
    query: str,
    db: Session = Depends(get_db),
    user = Depends(current_user)
):
    if user.role != "recruiter":
        return {"error": "Only recruiters can search for candidates"}

    candidates = search_candidates(query, db)
    return [
        {
            "id": c.id,
            "skills": c.skills,
            "experience": c.experience
        }
        for c in candidates
    ]
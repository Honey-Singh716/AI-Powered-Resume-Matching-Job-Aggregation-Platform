from sqlalchemy.orm import Session
from fastapi import HTTPException
import numpy as np

from repositories.job_repo import create_job, get_recommended_jobs, get_all_jobs
from repositories.candidate_repo import get_candidate_by_user_id
from services.embedding_service import generate_embedding

def build_job_embedding_text(title: str, skills_required: str, description: str = "", company: str = "") -> str:
    """Helper to compile text representation of a job for embedding generation."""
    return f"""
    Title: {title}
    Company: {company}
    Skills Required: {skills_required}
    Description: {description or ''}
    """

def save_job(data: dict, recruiter_id: int, db: Session):
    """Save a manually created internal recruiter job."""
    title = data.get("title")
    skills_required = data.get("skills_required")
    experience_required = data.get("experience_required")
    company = data.get("company")
    description = data.get("description", "")
    
    # Generate embedding
    job_text = build_job_embedding_text(
        title=title, 
        skills_required=skills_required, 
        description=description, 
        company=company
    )
    embedding = generate_embedding(job_text)
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()
    
    job_data = {
        "title": title,
        "company": company,
        "location": data.get("location"),
        "employment_type": data.get("employment_type"),
        "salary_min": data.get("salary_min"),
        "salary_max": data.get("salary_max"),
        "description": description,
        "skills_required": skills_required,
        "experience_required": experience_required,
        "source": "internal",
        "external_job_id": None,
        "job_url": data.get("job_url"),
        "embedding": embedding,
        "created_by": recruiter_id
    }
    
    return create_job(db, job_data)

def get_jobs_list(skip: int, limit: int, db: Session, q: str = None):
    """Retrieve jobs list with optional query filter."""
    return get_all_jobs(db, q=q, skip=skip, limit=limit)

def recommend_jobs_for_candidate(user_id: int, db: Session, limit: int = 5, skip: int = 0):
    """Find matching jobs for candidate using pgvector similarity search on resume embedding."""
    candidate = get_candidate_by_user_id(user_id, db)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found. Please parse/upload your resume first.")
    
    if candidate.embedding is None:
        raise HTTPException(status_code=400, detail="Candidate profile does not have an embedding. Please upload your resume.")
        
    results = get_recommended_jobs(db, candidate.embedding, limit=limit, skip=skip)
    
    recommended = []
    for job, score in results:
        if score >= 0.30:
            recommended.append({
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "source": job.source,
                "job_url": job.job_url,
                "similarity_score": float(round(score, 4))
            })
    return recommended

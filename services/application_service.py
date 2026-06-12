from fastapi import HTTPException
from repositories.application_repo import create_application, get_applications_by_job, get_applications_by_candidate, check_if_applied
from repositories.job_repo import get_job_by_id
from repositories.candidate_repo import get_candidate_by_id
from services.embedding_service import calculate_semantic_score_from_embeddings
from services.notification_service import send_application_notification

def apply_to_job(candidate_id, job_id, db):
    candidate = get_candidate_by_id(candidate_id, db)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found. Please upload a resume first.")

    job = get_job_by_id(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_application = check_if_applied(candidate_id, job_id, db)
    if existing_application:
        raise HTTPException(status_code=400, detail="You have already applied to this job")

    application = create_application(candidate_id, job_id, db)
    
    # Send simulated email notification
    send_application_notification(
        candidate_name=f"Candidate #{candidate.id}", 
        job_title=job.title, 
        recruiter_id=job.created_by
    )

    return application

def get_job_applicants(job_id, db):
    job = get_job_by_id(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    applications = get_applications_by_job(job_id, db)
    
    applicants_data = []
    for app in applications:
        candidate = get_candidate_by_id(app.candidate_id, db)
        if not candidate:
            continue

        # Calculate exact skill match
        candidate_skills = set(skill.strip().lower() for skill in candidate.skills.split(",") if skill.strip())
        job_skills = set(skill.strip().lower() for skill in job.skills_required.split(",") if skill.strip())
        matched_skills = candidate_skills.intersection(job_skills)
        score = (len(matched_skills) / len(job_skills)) * 100 if job_skills else 0

        # Calculate semantic score
        semantic_score = calculate_semantic_score_from_embeddings(candidate.embedding, job.embedding)

        applicants_data.append({
            "application_id": app.id,
            "candidate_id": candidate.id,
            "skills": candidate.skills,
            "experience": candidate.experience,
            "match_score": float(round(score, 2)),
            "semantic_score": float(round(semantic_score, 2)),
            "status": app.status
        })

    # Sort applicants by semantic score (highest first)
    applicants_data.sort(key=lambda x: x["semantic_score"], reverse=True)
    return applicants_data

def get_my_applications(candidate_id, db):
    applications = get_applications_by_candidate(candidate_id, db)
    
    results = []
    for app in applications:
        job = get_job_by_id(app.job_id, db)
        if job:
            results.append({
                "application_id": app.id,
                "job_id": job.id,
                "job_title": job.title,
                "status": app.status
            })
    return results

from repositories.job_repo import get_job_by_id, get_recommended_jobs
from repositories.candidate_repo import get_candidate_by_id
from services.embedding_service import calculate_semantic_score_from_embeddings
from fastapi import HTTPException



def match_candidate_to_job(candidate_id,job_id,db):

    candidate = get_candidate_by_id(candidate_id,db)
    job = get_job_by_id(job_id,db)
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")


    candidate_skills = set(
        skill.strip().lower()
        for skill in candidate.skills.split(",")
        if skill.strip()
    )  

    job_skills = set(
        skill.strip().lower()
        for skill in job.skills_required.split(",")
        if skill.strip()
    )  

    matched_skills = candidate_skills.intersection(job_skills)

    score = (len(matched_skills)/len(job_skills)) * 100 if job_skills else 0

    # Use stored embeddings from DB instead of re-encoding text
    semantic_score = calculate_semantic_score_from_embeddings(
        candidate.embedding, job.embedding
    )


    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "matched_skills": list(matched_skills),
        "match_score": float(round(score, 2)),
        "semantic_score" : float(round(semantic_score,2))
    }



def recommend_jobs(candidate_id, db):
    candidate = get_candidate_by_id(candidate_id, db)

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate.embedding is None:
        return []

    # Query matching jobs from DB using pgvector similarity search (limit=5)
    results = get_recommended_jobs(db, candidate.embedding, limit=5)

    recommendations = []
    for job, score in results:
        recommendations.append(
            {
                "job_id" : job.id,
                "title": job.title,
                "semantic_score": float(round(score, 2))
            }
        )

    return recommendations
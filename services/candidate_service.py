from repositories.candidate_repo import create_candidate, get_candidate_by_user_id
from services.embedding_service import generate_embedding



def save_candidate(parsed_resume,user_id,db):
    

    skills = ",".join(parsed_resume["skills"])

    experience = parsed_resume["experience"]

    education = parsed_resume.get("education", "")

    candidate_text = f"""
    Skills: {skills}
    Experience: {experience}
    Education: {education}
    """
    
    embedding = generate_embedding(candidate_text)

    embedding = embedding.tolist()

    candidate = get_candidate_by_user_id(user_id, db)
    from services.redis_service import invalidate_candidate_recommendations
    
    if candidate:
        candidate.skills = skills
        candidate.experience = experience
        candidate.education = education
        candidate.embedding = embedding
        db.commit()
        db.refresh(candidate)
        invalidate_candidate_recommendations(user_id)
        return candidate
    else:
        new_candidate = create_candidate(skills,experience,embedding,user_id,db,education=education)
        invalidate_candidate_recommendations(user_id)
        return new_candidate
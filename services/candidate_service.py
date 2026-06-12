from repositories.candidate_repo import create_candidate, get_candidate_by_user_id
from services.embedding_service import generate_embedding



def save_candidate(parsed_resume,user_id,db):
    

    skills = ",".join(parsed_resume["skills"])

    experience = parsed_resume["experience"]

    candidate_text = f"""
    Skills: {skills}
    Experience: {experience}
    """
    
    embedding = generate_embedding(candidate_text)

    embedding = embedding.tolist()

    candidate = get_candidate_by_user_id(user_id, db)
    if candidate:
        candidate.skills = skills
        candidate.experience = experience
        candidate.embedding = embedding
        db.commit()
        db.refresh(candidate)
        return candidate
    else:
        return create_candidate(skills,experience,embedding,user_id,db)
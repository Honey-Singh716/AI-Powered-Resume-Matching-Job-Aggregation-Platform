from models.candidate import Candidate
from sqlalchemy.orm import Session, defer

def create_candidate(
        skills,experience,embedding,user_id,db,education=None
):
    
    candidate = Candidate(skills=skills,experience=experience,embedding=embedding,user_id=user_id,education=education)

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return candidate


def search_candidates(query: str, db: Session):
    """Search candidates by skills (case insensitive simple match)"""
    search_term = f"%{query}%"
    return db.query(Candidate).filter(Candidate.skills.ilike(search_term)).options(defer(Candidate.embedding)).all()


def update_candidate(candidate_id,skills,experience,education,db):
    candidate = get_candidate_by_id(candidate_id,db)
    candidate.skills = skills
    candidate.experience = experience
    candidate.education = education
    db.commit()
    db.refresh(candidate)
    
    # Invalidate Redis recommendations cache
    try:
        from services.redis_service import invalidate_candidate_recommendations
        invalidate_candidate_recommendations(candidate.user_id)
    except Exception:
        pass
        
    return candidate
    
def get_candidate_by_id(candidate_id,db):
    return db.query(Candidate).filter(Candidate.id == candidate_id).first()


def get_candidate_by_user_id(user_id, db):
    return db.query(Candidate).filter(Candidate.user_id == user_id).first()
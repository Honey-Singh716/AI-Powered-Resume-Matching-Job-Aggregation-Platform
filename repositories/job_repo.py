from sqlalchemy.orm import Session, defer
from models.job import Job

def create_job(db: Session, job_data: dict) -> Job:
    """Create a new job in the database."""
    job = Job(**job_data)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def get_job_by_id(job_id, db: Session) -> Job:
    """Retrieve a job by its database ID."""
    return db.query(Job).filter(Job.id == job_id).first()

def get_job_by_source_and_external_id(db: Session, source: str, external_job_id: str) -> Job:
    """Retrieve a job by its source and external job ID (used for duplicate detection)."""
    if not external_job_id:
        return None
    return db.query(Job).filter(Job.source == source, Job.external_job_id == external_job_id).options(defer(Job.embedding)).first()

def get_all_jobs(db: Session, q: str = None, skip: int = 0, limit: int = 20,
                 location: str = None, employment_type: str = None, experience: str = None):
    """Retrieve all jobs with pagination, search, and filter support."""
    query = db.query(Job).options(defer(Job.embedding))
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (Job.title.ilike(search_filter)) |
            (Job.skills_required.ilike(search_filter)) |
            (Job.company.ilike(search_filter)) |
            (Job.description.ilike(search_filter))
        )
    if location == 'remote':
        query = query.filter(Job.location.ilike('%remote%'))
    elif location == 'onsite':
        query = query.filter(~Job.location.ilike('%remote%'))
    if employment_type:
        query = query.filter(Job.employment_type.ilike(f'%{employment_type}%'))
    if experience == 'entry':
        query = query.filter(Job.experience_required.ilike('%0%') | Job.experience_required.ilike('%1%') | Job.experience_required.ilike('%entry%') | Job.experience_required.ilike('%junior%'))
    elif experience == 'mid':
        query = query.filter(Job.experience_required.ilike('%2%') | Job.experience_required.ilike('%3%') | Job.experience_required.ilike('%mid%'))
    elif experience == 'senior':
        query = query.filter(Job.experience_required.ilike('%5%') | Job.experience_required.ilike('%senior%') | Job.experience_required.ilike('%lead%'))
    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return jobs, total

def get_recommended_jobs(db: Session, candidate_embedding, limit: int = 5, skip: int = 0):
    """
    Perform a similarity search using pgvector cosine distance.
    Returns a list of tuples: (Job, similarity_score)
    """
    if candidate_embedding is None:
        return []
    
    similarity_score = 1.0 - Job.embedding.cosine_distance(candidate_embedding)
    
    results = (
        db.query(Job, similarity_score.label("similarity_score"))
        .order_by(similarity_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return results
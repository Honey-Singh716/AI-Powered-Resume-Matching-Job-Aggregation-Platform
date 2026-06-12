from models.application import Application

def create_application(candidate_id, job_id, db):
    application = Application(candidate_id=candidate_id, job_id=job_id, status="applied")
    db.add(application)
    db.commit()
    db.refresh(application)
    return application

def get_applications_by_job(job_id, db):
    return db.query(Application).filter(Application.job_id == job_id).all()

def get_applications_by_candidate(candidate_id, db):
    return db.query(Application).filter(Application.candidate_id == candidate_id).all()

def check_if_applied(candidate_id, job_id, db):
    return db.query(Application).filter(
        Application.candidate_id == candidate_id, 
        Application.job_id == job_id
    ).first()

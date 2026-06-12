from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime, func, UniqueConstraint
from pgvector.sqlalchemy import Vector

from database import Base

class Job(Base):

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    skills_required = Column(String, nullable=False)
    experience_required = Column(String, nullable=True)
    source = Column(String, nullable=False)  # internal, remoteok, greenhouse, lever
    external_job_id = Column(String, nullable=True, index=True)
    job_url = Column(String, nullable=True)
    embedding = Column(Vector(384), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('source', 'external_job_id', name='uq_source_external_job_id'),
    )


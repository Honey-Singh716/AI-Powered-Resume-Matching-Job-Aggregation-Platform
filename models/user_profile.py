from sqlalchemy import Column, ForeignKey, Integer, String, Text

from database import Base


class UserProfile(Base):
    """Editable profile details that sit beside the existing candidate record.

    The candidate table remains the source used for resume parsing and job
    matching. This table stores the fields a person edits by hand.
    """

    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name = Column(String(80), nullable=True)
    professional_title = Column(String(120), nullable=True)
    profile_photo = Column(Text, nullable=True)
    skills_json = Column(Text, nullable=True)
    experience_items = Column(Text, nullable=True)
    education_items = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    experience_summary = Column(Text, nullable=True)
    education_summary = Column(Text, nullable=True)
    resume_filename = Column(String(180), nullable=True)

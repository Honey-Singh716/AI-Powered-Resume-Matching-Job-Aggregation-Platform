from sqlalchemy import Column, ForeignKey ,Integer,String
from pgvector.sqlalchemy import Vector

from database import Base

class Candidate(Base):

    __tablename__ = "candidates"

    id = Column(Integer,primary_key= True,index =True)
    user_id = Column(Integer,ForeignKey("users.id"), nullable=False)
    skills = Column(String,nullable=False)
    experience = Column(String,nullable=False)
    education = Column(String,nullable=True)

    embedding = Column(Vector(384))

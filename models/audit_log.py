from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from database import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, default="success", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

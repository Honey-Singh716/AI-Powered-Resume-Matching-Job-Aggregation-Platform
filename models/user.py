from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import DateTime

from database import Base
from datetime import datetime


class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    password = Column(
        String,
        nullable=False
    )

    role = Column(
        String,
        nullable=False
    )

    # Email verification fields
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default='0'
    )

    verification_token_hash = Column(
        String,
        nullable=True
    )

    verification_token_expires_at = Column(
        DateTime,
        nullable=True
    )

    verification_token_sent_at = Column(
        DateTime,
        nullable=True
    )
from pydantic import BaseModel
from pydantic import EmailStr
from typing import Literal


class UserCreate(BaseModel):

    email: EmailStr

    password: str

    role: Literal["candidate", "recruiter"]

class UserLogin(BaseModel):
    email: EmailStr

    password: str


class UserResponse(BaseModel):

    id: int

    email: str

    role: str

    detail: str | None = None
    verification_email_sent: bool | None = None

    class Config:

        from_attributes = True
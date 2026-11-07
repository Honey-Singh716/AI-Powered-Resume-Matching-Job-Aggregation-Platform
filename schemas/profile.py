import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_YEAR = re.compile(r"^(19|20)\d{2}$")
_PHOTO = re.compile(r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=\s]+$")
_MAX_PHOTO_LENGTH = 1_800_000


def _clean(value: Optional[str]) -> str:
    return " ".join((value or "").split())


def _check_month(value: str, label: str) -> str:
    value = (value or "").strip()
    if value and not _MONTH.match(value):
        raise ValueError(f"{label} must use a month in YYYY-MM format.")
    return value


def _check_year(value: str, label: str) -> str:
    value = (value or "").strip()
    if value and not _YEAR.match(value):
        raise ValueError(f"{label} must be a four-digit year.")
    return value


class ExperienceItem(BaseModel):
    role: str
    company: str
    start_date: str = ""
    end_date: str = ""
    current: bool = False
    description: str = ""

    @field_validator("role", "company")
    @classmethod
    def required_text(cls, value: str, info) -> str:
        cleaned = _clean(value)
        label = "Role" if info.field_name == "role" else "Company"
        if not cleaned:
            raise ValueError(f"{label} is required.")
        if len(cleaned) > 120:
            raise ValueError(f"{label} must be 120 characters or fewer.")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) > 2000:
            raise ValueError("Description must be 2000 characters or fewer.")
        return cleaned

    @model_validator(mode="after")
    def check_dates(self):
        self.start_date = _check_month(self.start_date, "Start date")
        self.end_date = _check_month(self.end_date, "End date")
        if self.current:
            self.end_date = ""
        elif self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be the same month as the start date, or later.")
        return self


class EducationItem(BaseModel):
    school: str
    degree: str
    field: str = ""
    start_year: str = ""
    end_year: str = ""

    @field_validator("school", "degree")
    @classmethod
    def required_text(cls, value: str, info) -> str:
        cleaned = _clean(value)
        label = "School" if info.field_name == "school" else "Degree"
        if not cleaned:
            raise ValueError(f"{label} is required.")
        if len(cleaned) > 160:
            raise ValueError(f"{label} must be 160 characters or fewer.")
        return cleaned

    @field_validator("field")
    @classmethod
    def clean_field(cls, value: str) -> str:
        cleaned = _clean(value)
        if len(cleaned) > 120:
            raise ValueError("Field of study must be 120 characters or fewer.")
        return cleaned

    @model_validator(mode="after")
    def check_years(self):
        self.start_year = _check_year(self.start_year, "Start year")
        self.end_year = _check_year(self.end_year, "End year")
        if self.start_year and self.end_year and int(self.end_year) < int(self.start_year):
            raise ValueError("End year must be the same as the start year, or later.")
        return self


class CertificationItem(BaseModel):
    name: str
    issuer: str = ""
    year: str = ""

    @field_validator("name")
    @classmethod
    def required_name(cls, value: str) -> str:
        cleaned = _clean(value)
        if not cleaned:
            raise ValueError("Certification name is required.")
        if len(cleaned) > 160:
            raise ValueError("Certification name must be 160 characters or fewer.")
        return cleaned

    @field_validator("issuer")
    @classmethod
    def clean_issuer(cls, value: str) -> str:
        cleaned = _clean(value)
        if len(cleaned) > 160:
            raise ValueError("Issuer must be 160 characters or fewer.")
        return cleaned

    @field_validator("year")
    @classmethod
    def clean_year(cls, value: str) -> str:
        return _check_year(value, "Year")


class ProfileUpdate(BaseModel):
    full_name: str = ""
    email: EmailStr
    professional_title: str = ""
    profile_photo: str = ""
    skills: list[str] = Field(default_factory=list, max_length=40)
    experience_items: list[ExperienceItem] = Field(default_factory=list, max_length=20)
    education_items: list[EducationItem] = Field(default_factory=list, max_length=15)
    certifications: list[CertificationItem] = Field(default_factory=list, max_length=20)
    experience_summary: str = ""
    education_summary: str = ""

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = _clean(value)
        if len(cleaned) > 80:
            raise ValueError("Name must be 80 characters or fewer.")
        if cleaned and not all(ch.isalpha() or ch.isspace() or ch in ".'-" for ch in cleaned):
            raise ValueError("Name can only include letters, spaces, apostrophes, periods, and hyphens.")
        return cleaned

    @field_validator("professional_title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = _clean(value)
        if len(cleaned) > 120:
            raise ValueError("Professional title must be 120 characters or fewer.")
        if cleaned and not all(ch.isalnum() or ch.isspace() or ch in "&/,.+#-'()" for ch in cleaned):
            raise ValueError("Professional title contains unsupported characters.")
        return cleaned

    @field_validator("profile_photo")
    @classmethod
    def clean_photo(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            return ""
        if len(cleaned) > _MAX_PHOTO_LENGTH or not _PHOTO.match(cleaned):
            raise ValueError("Profile photo must be a JPG, PNG, or WebP image.")
        return cleaned

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str]) -> list[str]:
        cleaned = []
        seen = set()
        for skill in value:
            item = _clean(str(skill))
            if not item:
                continue
            if len(item) > 40:
                raise ValueError("Each skill must be 40 characters or fewer.")
            if "," in item:
                raise ValueError("Enter one skill at a time, without commas.")
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(item)
        return cleaned

    @field_validator("experience_summary", "education_summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) > 8000:
            raise ValueError("Summary must be 8000 characters or fewer.")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

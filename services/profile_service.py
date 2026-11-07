import json
import logging
import os
import re

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.candidate import Candidate
from models.user_profile import UserProfile
from repositories.candidate_repo import create_candidate, get_candidate_by_user_id
from repositories.user_repo_ext import get_user_by_email
from services.auth_service import create_access_token

logger = logging.getLogger(__name__)

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._ ()-]")


def clean_resume_filename(name: str) -> str:
    base = os.path.basename(name or "resume.pdf")
    cleaned = _FILENAME_SAFE.sub("", base).strip().strip(".") or "resume.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned[:180]


def _loads(value, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def _skill_list(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def _get_profile(db: Session, user_id: int):
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def _ensure_profile(db: Session, user_id: int) -> UserProfile:
    row = _get_profile(db, user_id)
    if row is None:
        row = UserProfile(user_id=user_id)
        db.add(row)
    return row


def _compose_experience(summary: str, items: list[dict]) -> str:
    lines = []
    if summary:
        lines.append(summary)
    for item in items:
        dates = []
        if item.get("start_date"):
            dates.append(item["start_date"])
        if item.get("current"):
            dates.append("Present")
        elif item.get("end_date"):
            dates.append(item["end_date"])
        header = f"{item.get('role', '')} at {item.get('company', '')}".strip()
        if dates:
            header = f"{header} ({' – '.join(dates)})"
        description = (item.get("description") or "").strip()
        lines.append(f"{header}. {description}".strip() if description else header)
    return "\n".join(line for line in lines if line).strip()


def _compose_education(summary: str, items: list[dict]) -> str:
    lines = []
    if summary:
        lines.append(summary)
    for item in items:
        years = " – ".join(part for part in (item.get("start_year"), item.get("end_year")) if part)
        field = item.get("field") or ""
        header = f"{item.get('degree', '')}, {item.get('school', '')}".strip(", ")
        if field:
            header = f"{header}, {field}"
        if years:
            header = f"{header} ({years})"
        lines.append(header)
    return "\n".join(line for line in lines if line).strip()


def _compose_certifications(items: list[dict]) -> str:
    parts = []
    for item in items:
        label = item.get("name") or ""
        if item.get("issuer"):
            label = f"{label} ({item['issuer']})"
        if item.get("year"):
            label = f"{label}, {item['year']}"
        if label:
            parts.append(label)
    return "; ".join(parts)


def _embed(text: str):
    try:
        from services.embedding_service import generate_embedding
        return generate_embedding(text).tolist()
    except Exception:
        logger.exception("Could not refresh the profile match embedding")
        return None


def _invalidate(user_id: int):
    try:
        from services.redis_service import invalidate_candidate_recommendations
        invalidate_candidate_recommendations(user_id)
    except Exception:
        logger.exception("Could not clear cached recommendations for user %s", user_id)


def build_account_profile(user, db: Session) -> dict:
    """Return the editor payload. Missing sections stay empty."""
    row = _get_profile(db, user.id)
    candidate = get_candidate_by_user_id(user.id, db)

    if row is None or row.skills_json is None:
        skills = _skill_list(candidate.skills) if candidate else []
    else:
        skills = _loads(row.skills_json, [])

    experience_items = _loads(row.experience_items, []) if row is not None else []
    education_items = _loads(row.education_items, []) if row is not None else []
    certifications = _loads(row.certifications, []) if row is not None else []

    if row is None or row.experience_summary is None:
        experience_summary = "" if experience_items else ((candidate.experience or "") if candidate else "")
    else:
        experience_summary = row.experience_summary or ""

    if row is None or row.education_summary is None:
        education_summary = "" if education_items else ((candidate.education or "") if candidate else "")
    else:
        education_summary = row.education_summary or ""

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": (row.full_name or "") if row else "",
        "professional_title": (row.professional_title or "") if row else "",
        "profile_photo": (row.profile_photo or "") if row else "",
        "candidate_id": candidate.id if candidate else None,
        "skills": skills,
        "experience": candidate.experience if candidate else "",
        "education": candidate.education if candidate else "",
        "experience_summary": experience_summary,
        "education_summary": education_summary,
        "experience_items": experience_items,
        "education_items": education_items,
        "certifications": certifications,
        "resume_filename": (row.resume_filename or "") if row else "",
        "match_ready": bool(candidate is not None and candidate.embedding is not None),
    }


def remember_parsed_resume(user, candidate: Candidate, db: Session, filename: str | None = None):
    """Copy a real parse result into the editable profile without inventing entries."""
    row = _ensure_profile(db, user.id)
    row.skills_json = json.dumps(_skill_list(candidate.skills), ensure_ascii=False)
    row.experience_summary = candidate.experience or ""
    row.education_summary = candidate.education or ""
    if filename:
        row.resume_filename = clean_resume_filename(filename)
    db.commit()
    db.refresh(row)
    return row


def update_profile(user, payload, db: Session) -> dict:
    if user.role != "candidate" and (
        payload.skills
        or payload.experience_items
        or payload.education_items
        or payload.certifications
        or payload.experience_summary
        or payload.education_summary
    ):
        raise HTTPException(status_code=403, detail="Only candidates can save resume details.")

    new_email = payload.email
    email_changed = new_email.casefold() != (user.email or "").casefold()
    if email_changed:
        existing = get_user_by_email(new_email, db)
        if existing is not None and existing.id != user.id:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        user.email = new_email

    experience_items = [item.model_dump() for item in payload.experience_items]
    education_items = [item.model_dump() for item in payload.education_items]
    certifications = [item.model_dump() for item in payload.certifications]

    row = _ensure_profile(db, user.id)
    row.full_name = payload.full_name or None
    row.professional_title = payload.professional_title or None
    row.profile_photo = payload.profile_photo or None
    row.skills_json = json.dumps(payload.skills, ensure_ascii=False)
    row.experience_items = json.dumps(experience_items, ensure_ascii=False)
    row.education_items = json.dumps(education_items, ensure_ascii=False)
    row.certifications = json.dumps(certifications, ensure_ascii=False)
    row.experience_summary = payload.experience_summary
    row.education_summary = payload.education_summary

    notice = None
    if user.role == "candidate":
        notice = _sync_candidate(
            user,
            db,
            skills=payload.skills,
            experience=_compose_experience(payload.experience_summary, experience_items),
            education=_compose_education(payload.education_summary, education_items),
            certifications=_compose_certifications(certifications),
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    db.refresh(user)
    db.refresh(row)

    account = build_account_profile(user, db)
    if email_changed:
        account["access_token"] = create_access_token({"sub": user.email, "role": user.role})
    if notice:
        account["notice"] = notice
    return account


def _sync_candidate(user, db: Session, skills: list[str], experience: str, education: str, certifications: str):
    """Project the edited profile onto the existing candidate record used for matching."""
    skills_csv = ",".join(skills)
    match_text = (
        f"Skills: {skills_csv}\n"
        f"Experience: {experience}\n"
        f"Education: {education}\n"
        f"Certifications: {certifications}"
    )
    has_content = bool(skills_csv or experience or education)
    candidate = get_candidate_by_user_id(user.id, db)

    if candidate is None and not has_content:
        return None

    if candidate is None:
        embedding = _embed(match_text)
        if embedding is None:
            return "Your profile was saved. Job matching will update once your background can be processed."
        create_candidate(skills_csv, experience, embedding, user.id, db, education=education or "")
        _invalidate(user.id)
        return None

    previous = (candidate.skills or "", candidate.experience or "", candidate.education or "")
    candidate.skills = skills_csv
    candidate.experience = experience
    candidate.education = education or ""
    if (candidate.skills, candidate.experience, candidate.education) != previous:
        embedding = _embed(match_text)
        if embedding is not None:
            candidate.embedding = embedding
        _invalidate(user.id)
    return None

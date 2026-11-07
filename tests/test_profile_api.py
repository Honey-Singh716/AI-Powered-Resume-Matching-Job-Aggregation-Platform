"""Profile editor contract: auth stays required, and empty sections are allowed."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from database import SessionLocal
from models.user import User
from schemas.profile import ProfileUpdate


def test_users_me_requires_auth(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_update_profile_requires_auth(client):
    response = client.put("/my-profile", json={"email": "person@example.com"})
    assert response.status_code == 401


def test_profile_update_allows_partial_sections():
    profile = ProfileUpdate(email="person@example.com")
    assert profile.full_name == ""
    assert profile.skills == []
    assert profile.experience_items == []
    assert profile.education_items == []
    assert profile.certifications == []


def test_profile_update_rejects_invalid_photo():
    with pytest.raises(ValidationError):
        ProfileUpdate(email="person@example.com", profile_photo="data:text/plain;base64,aaaa")


def test_save_profile_persists_optional_sections(client):
    email = "profile.editor@example.com"
    password = "ProfilePass123"
    client.post("/users/register", json={"email": email, "password": password, "role": "candidate"})

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.is_verified = True
        db.commit()
    finally:
        db.close()

    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    class _Embedding:
        def tolist(self):
            return [0.0] * 384

    with patch("services.embedding_service.generate_embedding", return_value=_Embedding()):
        saved = client.put(
            "/my-profile",
            headers=headers,
            json={
                "full_name": "Amina Shah",
                "email": email,
                "professional_title": "Backend Engineer",
                "skills": ["Python"],
                "experience_items": [{
                    "role": "Engineer",
                    "company": "Northwind",
                    "start_date": "2022-01",
                    "end_date": "",
                    "current": True,
                    "description": "Built APIs.",
                }],
            },
        )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["full_name"] == "Amina Shah"
    assert body["skills"] == ["Python"]
    assert body["experience_items"][0]["company"] == "Northwind"
    assert body["education_items"] == []
    assert body["certifications"] == []

    again = client.get("/users/me", headers=headers)
    assert again.status_code == 200
    assert again.json()["professional_title"] == "Backend Engineer"
    assert again.json()["resume_filename"] == ""


def test_profile_update_rejects_blank_experience_role():
    with pytest.raises(ValidationError):
        ProfileUpdate(
            email="person@example.com",
            experience_items=[{"role": " ", "company": "Acme"}],
        )

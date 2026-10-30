"""
Shared pytest fixtures for the AI Resume Matcher test suite.

Strategy
--------
* Use an in-memory SQLite database so tests never need a real PostgreSQL instance.
* Patch the scheduler, Redis, and Sentence-Transformer model so tests are fast
  and self-contained — no external services required.
* Override FastAPI's get_db dependency to point at the SQLite session.
"""

import os

# ── Set test environment variables BEFORE any app imports ────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_db_pytest.sqlite")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-32x")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8000")

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Patch heavy services before importing main ────────────────────────────────

# Prevent the scheduler from actually starting background threads
_scheduler_patch = patch("scheduler.start_scheduler", return_value=None)
_scheduler_stop_patch = patch("scheduler.stop_scheduler", return_value=None)

# Prevent Redis connection attempts
_redis_patch = patch(
    "services.redis_service.get_redis_client",
    return_value=None
)
_redis_close_patch = patch(
    "services.redis_service.close_redis",
    return_value=None
)

_scheduler_patch.start()
_scheduler_stop_patch.start()
_redis_patch.start()
_redis_close_patch.start()

# ── Now it is safe to import the FastAPI app ──────────────────────────────────
from main import app  # noqa: E402  (import after patches)
from database import Base, get_db  # noqa: E402

# ── SQLite in-memory engine for tests ────────────────────────────────────────
TEST_DB_URL = os.environ["DATABASE_URL"]

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def client():
    """Return a synchronous TestClient backed by the test SQLite database."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

"""
Admin System Health Service — checks each service's availability.
Does NOT expose connection strings, credentials, or secrets.
"""
import logging
import time
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)


def _check_postgres(db) -> dict:
    start = time.perf_counter()
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "name": "PostgreSQL",
            "status": "healthy",
            "response_ms": ms,
            "message": "Connection OK",
            "last_checked": datetime.now(timezone.utc),
        }
    except Exception as e:
        return {
            "name": "PostgreSQL",
            "status": "unhealthy",
            "response_ms": None,
            "message": str(e)[:120],
            "last_checked": datetime.now(timezone.utc),
        }


def _check_redis() -> dict:
    start = time.perf_counter()
    try:
      
        from services.redis_service import get_redis_client
        client = get_redis_client()
        if client:
            client.ping()                       
            ms = round((time.perf_counter() - start) * 1000, 1)
            return {
                "name": "Redis",
                "status": "healthy",
                "response_ms": ms,
                "message": "Connection OK",
                "last_checked": datetime.now(timezone.utc),
            }
        else:
            return {
                "name": "Redis",
                "status": "unhealthy",
                "response_ms": None,
                "message": "Redis connection failed",
                "last_checked": datetime.now(timezone.utc),
            }
    except Exception as e:
        return {
            "name": "Redis",
            "status": "unhealthy",
            "response_ms": None,
            "message": str(e)[:120],
            "last_checked": datetime.now(timezone.utc),
        }


def _check_n8n() -> dict:
    """Check n8n connectivity by attempting a HEAD request to the webhook host."""
    import os, requests
    webhook_url = os.getenv("N8N_OTP_WEBHOOK_URL", "")
    if not webhook_url:
        return {
            "name": "n8n / Email",
            "status": "warning",
            "response_ms": None,
            "message": "N8N_OTP_WEBHOOK_URL not configured",
            "last_checked": datetime.now(timezone.utc),
        }
    try:
        # Extract base URL for a simple reachability check
        from urllib.parse import urlparse
        parsed = urlparse(webhook_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        start = time.perf_counter()
        resp = requests.head(base, timeout=5)
        ms = round((time.perf_counter() - start) * 1000, 1)
        status = "healthy" if resp.status_code < 500 else "warning"
        return {
            "name": "n8n / Email",
            "status": status,
            "response_ms": ms,
            "message": f"HTTP {resp.status_code}",
            "last_checked": datetime.now(timezone.utc),
        }
    except Exception as e:
        return {
            "name": "n8n / Email",
            "status": "unhealthy",
            "response_ms": None,
            "message": str(e)[:120],
            "last_checked": datetime.now(timezone.utc),
        }


def _check_groq_ai() -> dict:
    """Check if GROQ_API_KEY is configured (don't make a live AI call)."""
    import os
    key = os.getenv("GROQ_API_KEY", "")
    if key:
        return {
            "name": "AI Service (Groq)",
            "status": "healthy",
            "response_ms": None,
            "message": "API key configured",
            "last_checked": datetime.now(timezone.utc),
        }
    return {
        "name": "AI Service (Groq)",
        "status": "unhealthy",
        "response_ms": None,
        "message": "GROQ_API_KEY not set",
        "last_checked": datetime.now(timezone.utc),
    }


def _check_embedding_model() -> dict:
    """Check if the sentence-transformer model is already loaded in memory."""
    try:
        
        from services.embedding_service import _model
        if _model is not None:
            return {
                "name": "Embedding Model",
                "status": "healthy",
                "response_ms": None,
                "message": "Model loaded in memory (all-MiniLM-L6-v2)",
                "last_checked": datetime.now(timezone.utc),
            }
        return {
            "name": "Embedding Model",
            "status": "warning",
            "response_ms": None,
            "message": "Model not yet loaded — will load on first resume upload",
            "last_checked": datetime.now(timezone.utc),
        }
    except Exception as e:
        return {
            "name": "Embedding Model",
            "status": "warning",
            "response_ms": None,
            "message": str(e)[:120],
            "last_checked": datetime.now(timezone.utc),
        }


def get_system_health(db) -> dict:
    services = [
        _check_postgres(db),
        _check_redis(),
        _check_n8n(),
        _check_groq_ai(),
        _check_embedding_model(),
    ]

    statuses = [s["status"] for s in services]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "healthy"

    return {"services": services, "overall_status": overall}

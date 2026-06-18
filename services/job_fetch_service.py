import requests
from sqlalchemy.orm import Session
import logging
from typing import List, Dict, Any

from repositories.job_repo import create_job, get_job_by_source_and_external_id
from services.embedding_service import generate_embedding
from services.job_service import build_job_embedding_text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# User-Agent header to avoid 403 Forbidden errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_remoteok_jobs() -> List[Dict[str, Any]]:
    """Fetch jobs from RemoteOK public API."""
    url = "https://remoteok.com/api"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # The first item is a disclaimer/info object, not a job
            if isinstance(data, list) and len(data) > 1:
                return data[1:]
    except Exception as e:
        logger.error(f"Error fetching from RemoteOK: {e}")
    
    # Fallback/Mock data if API fails
    logger.info("Using mock data fallback for RemoteOK")
    return [
        {
            "id": "rok-101",
            "position": "Senior Backend Developer (FastAPI)",
            "company": "FastAPI Solutions Ltd",
            "location": "Remote, US",
            "tags": ["python", "fastapi", "postgresql", "sqlalchemy"],
            "description": "We are seeking a senior python backend developer skilled in FastAPI, SQLalchemy, and PostgreSQL.",
            "url": "https://remoteok.com/remote-jobs/rok-101",
            "salary_min": 100000,
            "salary_max": 140000
        },
        {
            "id": "rok-102",
            "position": "Data Engineer (ML/AI)",
            "company": "DeepData Corp",
            "location": "Remote, Europe",
            "tags": ["python", "pandas", "machine-learning", "pgvector"],
            "description": "Build high performance vector search pipelines. Experience with pgvector and numpy is a plus.",
            "url": "https://remoteok.com/remote-jobs/rok-102",
            "salary_min": 90000,
            "salary_max": 120000
        }
    ]

def fetch_greenhouse_jobs(board_token: str = "github") -> List[Dict[str, Any]]:
    """Fetch jobs from Greenhouse public board API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("jobs", [])
    except Exception as e:
        logger.error(f"Error fetching from Greenhouse: {e}")
    
    # Fallback/Mock data if API fails
    logger.info("Using mock data fallback for Greenhouse")
    return [
        {
            "id": "gh-201",
            "title": "Machine Learning Engineer",
            "company": "GitHub",
            "location": {"name": "San Francisco, CA"},
            "metadata": [
                {"name": "Employment Type", "value": "Full-time"},
                {"name": "Skills Required", "value": "Python, PyTorch, Transformers, LLMs"}
            ],
            "content": "Looking for an ML engineer to build next-gen developer tools using LLMs and machine learning.",
            "absolute_url": "https://boards.greenhouse.io/github/jobs/gh-201"
        }
    ]

def fetch_lever_jobs(company: str = "lever") -> List[Dict[str, Any]]:
    """Fetch jobs from Lever public postings API."""
    url = f"https://api.lever.co/v0/postings/{company}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching from Lever: {e}")
        
    # Fallback/Mock data if API fails
    logger.info("Using mock data fallback for Lever")
    return [
        {
            "id": "lev-301",
            "title": "Full Stack Engineer (React/Python)",
            "company": "Lever Inc",
            "categories": {"commitment": "Full-time", "location": "Toronto, Canada"},
            "description": "Work on Lever core applications using React, Python, and SQL databases.",
            "hostedUrl": "https://jobs.lever.co/lever/lev-301"
        }
    ]

def process_and_normalize_jobs(db: Session) -> Dict[str, int]:
    """
    Fetches all jobs from sources, normalizes them, filters duplicates,
    computes embeddings, and stores them in database.
    """
    summary = {"fetched": 0, "inserted": 0, "skipped": 0}
    
    # --- 1. REMOTE OK ---
    logger.info("Fetching RemoteOK jobs...")
    rok_raw = fetch_remoteok_jobs()
    for item in rok_raw:
        ext_id = str(item.get("id"))
        summary["fetched"] += 1
        
        if get_job_by_source_and_external_id(db, "remoteok", ext_id):
            summary["skipped"] += 1
            continue
            
        tags = item.get("tags", [])
        skills_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        if not skills_str.strip():
            skills_str = "Python, General Software Engineering"
            
        norm_job = {
            "title": item.get("position", "Remote Job"),
            "company": item.get("company", "Remote OK Employer"),
            "location": item.get("location", "Remote"),
            "employment_type": "Full-time",
            "salary_min": item.get("salary_min"),
            "salary_max": item.get("salary_max"),
            "description": item.get("description", ""),
            "skills_required": skills_str,
            "experience_required": "Not specified",
            "source": "remoteok",
            "external_job_id": ext_id,
            "job_url": item.get("url"),
            "created_by": None
        }
        
        save_normalized_job(db, norm_job)
        summary["inserted"] += 1
        
    # --- 2. GREENHOUSE ---
    greenhouse_companies = ["github", "twitch", "stripe", "reddit", "discord", "airbnb", "dropbox", "lyft", "pinterest", "plaid", "instacart"]
    for company_slug in greenhouse_companies:
        logger.info(f"Fetching Greenhouse jobs for {company_slug}...")
        gh_raw = fetch_greenhouse_jobs(company_slug)
        for item in gh_raw:
            ext_id = str(item.get("id"))
            summary["fetched"] += 1
            
            if get_job_by_source_and_external_id(db, "greenhouse", ext_id):
                summary["skipped"] += 1
                continue
                
            skills_str = "Software Development"
            emp_type = "Full-time"
            metadata = item.get("metadata", [])
            if isinstance(metadata, list):
                for meta in metadata:
                    name = str(meta.get("name", "")).lower()
                    val = str(meta.get("value", ""))
                    if "skills" in name:
                        skills_str = val
                    elif "employment" in name or "type" in name:
                        emp_type = val
                        
            location_data = item.get("location")
            loc_str = location_data.get("name") if isinstance(location_data, dict) else str(location_data)
            
            norm_job = {
                "title": item.get("title", "Software Engineer"),
                "company": item.get("company", company_slug.capitalize()),
                "location": loc_str,
                "employment_type": emp_type,
                "salary_min": None,
                "salary_max": None,
                "description": item.get("content", ""),
                "skills_required": skills_str,
                "experience_required": "Not specified",
                "source": "greenhouse",
                "external_job_id": ext_id,
                "job_url": item.get("absolute_url"),
                "created_by": None
            }
            
            save_normalized_job(db, norm_job)
            summary["inserted"] += 1
        
    # --- 3. LEVER ---
    lever_companies = ["lever", "coursera", "yelp", "eventbrite", "atlassian", "auth0"]
    for company_slug in lever_companies:
        logger.info(f"Fetching Lever jobs for {company_slug}...")
        lever_raw = fetch_lever_jobs(company_slug)
        for item in lever_raw:
            ext_id = str(item.get("id"))
            summary["fetched"] += 1
            
            if get_job_by_source_and_external_id(db, "lever", ext_id):
                summary["skipped"] += 1
                continue
                
            categories = item.get("categories", {})
            emp_type = categories.get("commitment", "Full-time")
            loc_str = categories.get("location", "Remote")
            
            norm_job = {
                "title": item.get("text", item.get("title", "Developer")),
                "company": item.get("company", company_slug.capitalize()),
                "location": loc_str,
                "employment_type": emp_type,
                "salary_min": None,
                "salary_max": None,
                "description": item.get("descriptionPlain", item.get("description", "")),
                "skills_required": "Python, APIs, Backend Development", 
                "experience_required": "Not specified",
                "source": "lever",
                "external_job_id": ext_id,
                "job_url": item.get("hostedUrl"),
                "created_by": None
            }
            
            save_normalized_job(db, norm_job)
            summary["inserted"] += 1
        
    logger.info(f"Aggregation session completed. Summary: {summary}")
    return summary

def save_normalized_job(db: Session, norm_job: dict):
    """Generates embedding and creates job model in repository."""
    # Generate embedding
    job_text = build_job_embedding_text(
        title=norm_job["title"],
        skills_required=norm_job["skills_required"],
        description=norm_job["description"],
        company=norm_job["company"]
    )
    
    embedding = generate_embedding(job_text)
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()
        
    norm_job["embedding"] = embedding
    create_job(db, norm_job)

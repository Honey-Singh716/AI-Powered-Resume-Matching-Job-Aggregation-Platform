import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import logging

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from route.match_routes import router as match_router
from route.resume_routes import router as resume_parser
from route.ai_routes import router as ai_router
from route.user_route import router as user_router
from route.auth_route import router as auth_router
from route.application_routes import router as application_router
from route.job_routes import router as job_router
# admin_router is the master router that aggregates all admin sub-routers.
# admin_routes.router (the flat route module) is already included inside admin.router,
# so we must NOT register admin_routes.router a second time here.
from admin.router import router as admin_router

from models.user import User
from models.user_profile import UserProfile
from models.application import Application
from models.audit_log import AdminAuditLog


from database import Base
from database import engine


try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not connect to database during startup. Error: {e}")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from scheduler import start_scheduler
    start_scheduler()
    logging.info("Application startup complete. Embedding model will load on first embedding request.")
    yield
    # Shutdown
    from scheduler import stop_scheduler
    from services.redis_service import close_redis
    stop_scheduler()
    close_redis()

app = FastAPI(lifespan=lifespan)

logging.basicConfig(level=logging.INFO)



@app.get("/api/health", tags=["Health"])
def health_check_get():
    """
    Lightweight public health check — GET variant.
    Returns HTTP 200 + JSON body.  No auth required.
    Used by UptimeRobot and any HTTP(s) monitor that sends GET.
    """
    return {"status": "healthy"}


@app.head("/api/health", tags=["Health"])
def health_check_head():
    """
    Lightweight public health check — HEAD variant.
    Returns HTTP 200 with correct headers and an empty body.
    UptimeRobot sometimes sends HEAD; this ensures it also works.
    """
    # FastAPI automatically strips the body for HEAD responses.
    return {"status": "healthy"}


# Legacy root health check kept for backwards compatibility.
@app.get("/health", include_in_schema=False)
def health_check_legacy():
    return {"status": "ok"}

# CORS: read allowed origins from env, default to localhost for development
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    match_router
)
app.include_router(
    resume_parser
)

app.include_router(
    ai_router
)

app.include_router(
    user_router
)

app.include_router(
    auth_router
)

app.include_router(
    application_router
)
app.include_router(
    job_router
)
app.include_router(
    admin_router
)

# Create frontend directory if it doesn't exist
os.makedirs("frontend", exist_ok=True)

# Mount the frontend directory to serve static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

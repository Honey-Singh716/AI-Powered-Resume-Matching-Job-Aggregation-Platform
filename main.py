from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from route.match_routes import router as match_router
from route.resume_routes import router as resume_parser
from route.ai_routes import router as ai_router
from route.user_route import router as user_router
from route.auth_route import router as auth_router
from route.application_routes import router as application_router
from route.job_routes import router as job_router

from models.user import User
from models.application import Application


from database import Base
from database import engine


try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not connect to database during startup. Error: {e}")

app = FastAPI()

@app.on_event("startup")
def on_startup():
    from scheduler import start_scheduler
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    from scheduler import stop_scheduler
    stop_scheduler()

from dotenv import load_dotenv
load_dotenv()

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

# Create frontend directory if it doesn't exist
os.makedirs("frontend", exist_ok=True)

# Mount the frontend directory to serve static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
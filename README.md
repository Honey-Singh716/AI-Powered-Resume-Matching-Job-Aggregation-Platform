# 🤖 AI Resume Matcher — Intelligent Job Matching Platform

An AI-powered recruitment platform that connects candidates with the best job opportunities using **semantic similarity matching**, **LLM-based resume parsing**, and **real-time job aggregation** from multiple external sources.

Built with **FastAPI**, **PostgreSQL + pgvector**, **Sentence Transformers**, and **Groq LLM API**.

---

## ✨ Key Features

### For Candidates
- **AI Resume Parsing** — Upload a PDF resume; the system uses Groq LLM (Llama 3.3 70B) to extract structured skills and experience automatically.
- **Semantic Job Matching** — Get personalized job recommendations ranked by AI cosine similarity, not just keyword matching.
- **One-Click Apply** — Apply to jobs directly from the dashboard and track application status.
- **AI Career Chat** — Chat with an AI career advisor that gives personalized advice based on your profile.

### For Recruiters
- **Post & Manage Jobs** — Create job listings with required skills and experience levels.
- **AI-Ranked Applicants** — View applicants for each job, automatically sorted by semantic match score (best candidates first).
- **Talent Search** — Search the candidate database by skills to find talent proactively.

### Platform-Wide
- **Multi-Source Job Aggregation** — Automatically fetches and normalizes jobs from **RemoteOK**, **Greenhouse**, and **Lever** APIs every 6 hours.
- **Duplicate Detection** — Prevents the same external job from being inserted twice using source + external ID uniqueness.
- **Vector Embeddings** — All jobs and candidate profiles are stored as 384-dimensional vectors (via `all-MiniLM-L6-v2`) in PostgreSQL using the `pgvector` extension for lightning-fast similarity search.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (SPA)                     │
│        HTML + CSS + JavaScript + Chart.js            │
└────────────────────────┬────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────┐
│                   FastAPI Server                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  Routes   │→│ Services  │→│  Repositories      │  │
│  │ (API)     │  │ (Logic)  │  │ (Database Access)  │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
│                      │                               │
│  ┌──────────────┐  ┌▼────────────┐  ┌────────────┐  │
│  │ Groq LLM API │  │ Sentence    │  │ APScheduler │  │
│  │ (Resume/Chat)│  │ Transformers│  │ (Job Fetch) │  │
│  └──────────────┘  └─────────────┘  └────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│            PostgreSQL + pgvector                     │
│   users │ candidates │ jobs │ applications           │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
AI/
├── main.py                  # FastAPI app entry point, middleware, router registration
├── database.py              # SQLAlchemy engine, session, Base
├── scheduler.py             # APScheduler for periodic job aggregation
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
│
├── models/                  # SQLAlchemy ORM models
│   ├── user.py              # User model (email, password, role)
│   ├── candidate.py         # Candidate profile (skills, experience, embedding)
│   ├── job.py               # Job model (title, skills, embedding, source)
│   └── application.py       # Application model (candidate → job link)
│
├── schemas/                 # Pydantic request/response schemas
│   ├── user.py              # UserCreate, UserLogin, UserResponse
│   ├── job.py               # JobCreate, JobResponse, RecommendedJobResponse
│   ├── application.py       # ApplicationResponse, ApplicantDetailResponse
│   ├── candidate.py         # Candidate schemas
│   ├── chat.py              # ChatRequest schema
│   └── resume.py            # ResumeRequest schema
│
├── route/                   # API route handlers
│   ├── user_route.py        # POST /users/register
│   ├── auth_route.py        # POST /auth/login
│   ├── resume_routes.py     # POST /upload_resume, /parse_resume, GET /my-profile
│   ├── job_routes.py        # POST /jobs, GET /jobs, GET /recommended-jobs
│   ├── match_routes.py      # GET /match/{cid}/{jid}, GET /recommend/{cid}
│   ├── application_routes.py# POST /apply/{jid}, GET /my-applications, GET /jobs/{jid}/applicants
│   └── ai_routes.py         # POST /chat
│
├── services/                # Business logic layer
│   ├── auth_service.py      # JWT creation, password hashing, token verification
│   ├── user_services.py     # Registration & login logic
│   ├── candidate_service.py # Save/update candidate profiles with embeddings
│   ├── job_service.py       # Create jobs, embedding generation, recommendations
│   ├── job_fetch_service.py # External job aggregation (RemoteOK, Greenhouse, Lever)
│   ├── match_service.py     # Skill overlap + semantic score calculations
│   ├── application_service.py # Apply, view applicants, rank by AI score
│   ├── embedding_service.py # Sentence Transformer model + cosine similarity
│   ├── ai_service.py        # Groq LLM integration (resume parsing, chat)
│   └── notification_service.py # Simulated email notifications
│
├── repositories/            # Database access layer
│   ├── user_repo.py         # Create/find users
│   ├── candidate_repo.py    # Create/find/search candidates
│   ├── job_repo.py          # Create/find/search/recommend jobs (pgvector)
│   └── application_repo.py  # Create/find applications
│
└── frontend/                # Static SPA served by FastAPI
    ├── index.html           # Main HTML with templates
    ├── styles.css           # Glassmorphism dark-theme styles
    └── app.js               # SPA logic, API calls, Chart.js dashboards
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **PostgreSQL** with the [`pgvector`](https://github.com/pgvector/pgvector) extension installed
- **Groq API Key** — Get one free at [console.groq.com](https://console.groq.com)

### 1. Clone the Repository

```bash
git clone https://github.com/Honey-Singh716/AI-Resume-Matching-Job-Aggregation-Platform.git
cd AI
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL

Create a database and enable pgvector:

```sql
CREATE DATABASE ai_resume_matcher;
\c ai_resume_matcher
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/ai_resume_matcher
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=your-random-secret-key-at-least-32-chars
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
REDIS_URL=redis://localhost:6379/0
```

> **💡 Tip:** Generate a strong secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`

### 6. Start Redis (Job Recommendation Caching)

Redis caches `/recommended-jobs` results for faster responses. The app falls back to the database if Redis is unavailable, but you should run Redis for full functionality.

**Option A — Docker (recommended):**

```bash
docker compose up -d redis
```

**Option B — Windows (Memurai, Redis-compatible):**

Install [Memurai Developer](https://www.memurai.com/) and ensure it listens on port `6379`.

**Option C — PowerShell helper script:**

```powershell
.\scripts\start-redis.ps1
```

### 7. Run the Server

```bash
uvicorn main:app --reload
```

The app will be available at:
- **Frontend Dashboard**: http://127.0.0.1:8000
- **Swagger API Docs**: http://127.0.0.1:8000/docs

---

## 🔐 API Endpoints

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| `POST` | `/users/register` | ❌ | — | Register a new user |
| `POST` | `/auth/login` | ❌ | — | Login and get JWT token |
| `POST` | `/upload_resume` | ✅ | candidate | Upload PDF resume for AI parsing |
| `POST` | `/parse_resume` | ✅ | candidate | Parse raw resume text with AI |
| `GET` | `/my-profile` | ✅ | candidate | View extracted AI profile |
| `POST` | `/jobs` | ✅ | recruiter | Create a new job listing |
| `GET` | `/jobs` | ❌ | — | List all jobs (with search & pagination) |
| `GET` | `/recommended-jobs` | ✅ | candidate | AI-recommended jobs for your profile |
| `GET` | `/match/{cid}/{jid}` | ❌ | — | Match score between candidate and job |
| `GET` | `/recommend/{cid}` | ❌ | — | Top 5 jobs for a candidate |
| `POST` | `/apply/{job_id}` | ✅ | candidate | Apply to a job |
| `GET` | `/my-applications` | ✅ | candidate | View your applications |
| `GET` | `/jobs/{job_id}/applicants` | ✅ | recruiter | View ranked applicants |
| `GET` | `/candidates/search?query=` | ✅ | recruiter | Search candidates by skills |
| `POST` | `/chat` | ❌ | — | Chat with AI career advisor |

---

## 🧠 How the AI Matching Works

### Step 1: Embedding Generation
When a resume is uploaded or a job is created, the text is converted into a **384-dimensional vector** using the `all-MiniLM-L6-v2` sentence transformer model. This vector captures the *semantic meaning* of the text.

### Step 2: Storage in pgvector
The embedding vector is stored alongside the record in PostgreSQL using the `pgvector` extension, enabling efficient similarity searches directly in SQL.

### Step 3: Cosine Similarity Matching
When comparing a candidate to a job:
- **Exact Match Score**: Counts how many of the job's required skills appear in the candidate's skill list (percentage).
- **Semantic Score**: Calculates the cosine similarity between the candidate's embedding vector and the job's embedding vector (0.0 to 1.0). This captures meaning beyond exact keywords — e.g., "React" and "Frontend Development" are semantically related even though the words differ.

### Step 4: Ranking
Results are sorted by semantic score (highest first), so the most relevant matches always appear at the top.

---

## 🔄 Job Aggregation Pipeline

A background scheduler (`APScheduler`) runs every **6 hours** and:

1. **Fetches** job listings from RemoteOK, Greenhouse, and Lever public APIs
2. **Normalizes** different JSON structures into a unified schema
3. **Deduplicates** by checking `(source, external_job_id)` uniqueness
4. **Generates embeddings** for each new job using Sentence Transformers
5. **Stores** everything in the database ready for matching

If any external API is unreachable, the system gracefully falls back to mock data.

---

## 🛡️ Security

- **Password Hashing**: All passwords are hashed with bcrypt via `passlib` before storage
- **JWT Authentication**: Stateless token-based auth using `python-jose` (HS256 algorithm)
- **Role-Based Access Control**: Endpoints enforce `candidate` or `recruiter` roles
- **Input Validation**: Pydantic schemas validate all input; role registration is restricted to `candidate` or `recruiter` only
- **CORS Protection**: Allowed origins are configurable via environment variable
- **Environment Variables**: All secrets (DB URL, API keys, JWT secret) are loaded from `.env`

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | FastAPI |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| AI/ML | Sentence Transformers, Scikit-Learn |
| LLM | Groq API (Llama 3.3 70B) |
| PDF Parsing | PyPDF2 |
| Scheduler | APScheduler |
| Cache | Redis |
| Frontend | Vanilla HTML/CSS/JS + Chart.js |

---

## 📄 License

This project was built for educational and internship purposes.

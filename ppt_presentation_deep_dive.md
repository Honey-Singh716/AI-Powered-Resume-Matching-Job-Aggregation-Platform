# 🚀 RecruitAI: Comprehensive Interview & Presentation Guide

*This document is the ultimate, expanded guide for your interview presentation. It covers every component, every route, and the exact logic behind every user interaction in the platform. You can adapt these sections directly into your presentation slides.*

---

## 🎯 SLIDE 1: Project Overview & Vision
**Concept**: A next-generation recruitment platform that moves beyond rigid keyword searches.
**The Problem**: Traditional applicant tracking systems rely on exact keyword matches, missing great candidates whose resumes use synonyms (e.g., "Frontend Developer" vs. "React Engineer").
**The Solution**: We built an AI-powered system that uses **Natural Language Processing (NLP)** and **Mathematical Vector Embeddings** to understand the *meaning* of a resume and match it mathematically to job descriptions.
**Core Features**: 
1. Real-time Job Aggregation (from external APIs).
2. LLM-powered PDF Resume Parsing.
3. Semantic Similarity Job Matching (AI Ranking).
4. Automated AI Career Advisor.

---

## 🛠️ SLIDE 2: Complete Tech Stack Justification
*Why did we choose these technologies?*

*   **Backend (FastAPI - Python)**: Chosen for async capabilities. Since we make heavy external API calls to Groq and Job Boards, FastAPI's `async/await` ensures the server never blocks.
*   **Database (PostgreSQL + pgvector)**: PostgreSQL ensures ACID compliance for user data, while the `pgvector` extension allows us to store 384-dimensional arrays and perform native vector math directly in SQL queries.
*   **AI Models**:
    *   **Sentence Transformers (`all-MiniLM-L6-v2`)**: A lightweight, fast, local model perfect for converting sentences into dense vector arrays.
    *   **Groq API (Llama 3.3 70B)**: Chosen over OpenAI for extreme speed (LPU inference). It rapidly structures chaotic PDF text into strict JSON.
*   **Frontend (Vanilla JS / CSS)**: Built without React/Vue to demonstrate raw DOM manipulation, state management, and lightweight SPA routing.

---

## 🗄️ SLIDE 3: Database Schema & Architecture
Our data layer is built on SQLAlchemy ORM.
*   `User` Table: Handles authentication. Stores email, bcrypt hashed password, and `role` (candidate vs recruiter).
*   `CandidateProfile` Table: Linked 1:1 with User. Stores the parsed `skills` (string), `experience` (text), and the all-important `embedding` (Vector column).
*   `Job` Table: Stores job `title`, `company`, `location`, `skills_required`, `source` (remoteok/internal), and its own `embedding` (Vector).
*   `Application` Table: A mapping table linking `user_id` and `job_id`, tracking application status.

---

## 🔄 SLIDE 4: The Job Aggregation Engine (Backend)
**How do jobs get into the system?**
*   **The Scheduler (`scheduler.py`)**: On FastAPI startup (`@app.on_event("startup")`), we initialize `APScheduler`. It triggers `process_and_normalize_jobs()` immediately and then every 6 hours asynchronously.
*   **The Logic (`services/job_fetch_service.py`)**:
    1.  **Fetch**: Makes asynchronous HTTP requests to `RemoteOK`, `Greenhouse`, and `Lever` public APIs.
    2.  **Normalize**: Different APIs have different JSON structures (e.g., `item["position"]` vs `item["title"]`). We map them to our internal `norm_job` dictionary.
    3.  **Deduplicate**: The logic calls `get_job_by_source_and_external_id(db, "remoteok", ext_id)`. If it exists, we skip it.
    4.  **Embed**: The normalized job text is passed to `generate_embedding()`, converted to a vector, and saved to the PostgreSQL `Job` table.

---

## 🧠 SLIDE 5: The AI Resume Parsing Pipeline
**What happens when a user clicks "Upload Resume"?**
*   **Frontend Action**: The `<input type="file" onchange="handleLandingUpload(event)">` triggers. The JS validates the `.pdf` extension and sends a `FormData` POST request to `/upload_resume`.
*   **Backend Route (`route/resume_routes.py`)**:
    1.  **PDF Reading**: `PyPDF2.PdfReader` parses the raw, unstructured text from the PDF buffer.
    2.  **LLM Structuring**: The text is sent to the `ai_service.py`. We use a strict System Prompt telling the Groq API (Llama 3.3): *"Extract only a JSON object with keys 'skills' and 'experience' from this text."*
    3.  **Vectorization**: The returned skills and experience are concatenated and passed into `generate_embedding()`.
    4.  **Database Storage**: The profile, along with its new mathematical vector, is saved to `CandidateProfile`.
*   **Frontend Update**: The UI receives the structured data and displays the AI Analysis preview widget, showing a simulated ATS health score and extracted tags.

---

## ⚡ SLIDE 6: Semantic Matching Engine (The Secret Sauce)
**What happens when the user views "Recommended Jobs"?**
*   **Frontend Action**: The SPA router calls `initRecommendedJobs()`, which fetches `/recommended-jobs?limit=9&skip=0`.
*   **Backend Logic (`services/job_service.py` & `repositories/job_repo.py`)**:
    *   The backend retrieves the Candidate's embedding from the database.
    *   **The SQL Query**: We don't use Python for the math. We use the database index.
        ```python
        similarity_score = 1.0 - Job.embedding.cosine_distance(candidate_embedding)
        ```
    *   The database orders every job by this `similarity_score` in descending order.
    *   Jobs with a score `>= 0.30` are returned to the frontend.
*   **Why this matters**: A candidate with "JavaScript, Node.js" will mathematically match a job looking for a "MERN Stack Developer" because the AI understands the semantic proximity of those concepts, even without keyword overlap.

---

## 🖱️ SLIDE 7: Frontend Routing & State Management
**How does the UI work without React?**
*   **State Object**: In `app.js`, we maintain a global `state` dictionary (`token`, `role`, `email`, `currentJobSkip`, `jobLimit`).
*   **The Router (`navigateTo(viewId)`)**: 
    *   Instead of multiple HTML pages, `index.html` holds multiple `<template id="view-...">` tags.
    *   When you click a sidebar link, `navigateTo()` clears `document.getElementById('main-content').innerHTML`.
    *   It clones the requested template content and appends it to the DOM.
    *   It then dynamically calls an init function (e.g., `initCandidateDashboard()`).

---

## 📊 SLIDE 8: Candidate Dashboard Breakdown
*   **Trigger**: Router loads `view-candidate-dashboard`.
*   **Stats API**: Calls `/my-applications` to count apps, reads `state.savedJobs.length`, and calculates a profile completion percentage.
*   **Skills Gap Logic**: It compares the candidate's extracted skills against a hardcoded array of `trendingSkills` (React, TypeScript, AWS). It dynamically renders "Missing Skills" tags and "Matched Skills" tags.
*   **Recent Activity**: Maps over the `applicationsCache` array to generate a timeline UI of where the candidate applied.

---

## 💼 SLIDE 9: Applying for Jobs & Pagination
*   **Pagination Logic**: 
    *   On the Recommended Jobs page, we have "Next" and "Prev" buttons. 
    *   Clicking Next triggers `nextJobPage()`, which does `state.currentJobSkip += state.jobLimit` and re-fetches the API with the new offset.
*   **Apply Logic**: 
    *   User clicks the job card, opening the Right Drawer. User clicks **"Apply Now"**.
    *   JS triggers `apiCall('/apply/{jobId}', 'POST')`.
    *   Backend `application_routes.py` creates a new `Application` row with status "applied". The UI button changes to a green "✓ Applied".

---

## 👔 SLIDE 10: The Recruiter Experience
*   **Job Posting Logic**: 
    *   Recruiter fills out the HTML form. `handleCreateJob(event)` intercepts the submit.
    *   Backend `/jobs` route receives the payload. It passes the text through the `sentence-transformers` model to generate an embedding for this manual job, saving it as `source="internal"`.
*   **Applicant Ranking Logic**:
    *   Recruiter clicks on their posted job to view applicants.
    *   Backend `/jobs/{id}/applicants` is hit.
    *   The database dynamically runs the cosine similarity math between the Job's embedding and EVERY Applicant's embedding, returning a list of candidates *ranked mathematically from best fit to worst fit*.

---

## 💬 SLIDE 11: AI Career Assistant (Chat Widget)
*   **Frontend Logic**: The floating chat widget is globally draggable (`makeDraggable()`). 
*   **Message Flow**: When the user types and hits enter, `handleChatEnter()` is fired. The message is appended locally to the DOM, and a POST request is sent to `/chat`.
*   **Backend Logic (`route/ai_routes.py`)**: 
    *   The message goes to the Groq API. We inject a System Prompt: *"You are an AI career assistant..."*
    *   The Groq LLM evaluates the user's question, generates career advice, and returns the string to the frontend to be appended to the chat window.

---

## 🔐 SLIDE 12: Security & Authentication Design
*   **Hashing**: Passwords are never logged or stored. We use `passlib` with `bcrypt` algorithms.
*   **Stateless JWT**: Upon login, the `/auth/login` endpoint yields a JWT token. The server does not store active sessions. 
*   **Route Protection**: FastAPI `Depends(current_user)` middleware intercepts protected routes. It decodes the JWT signature, verifies the expiration timestamp, and extracts the `user_id`. If invalid, it throws an HTTP 401 Unauthorized.
*   **Role Protection**: Specific endpoints check `if user.role != "candidate": raise HTTPException(403)`.

---

## 📝 SUMMARY: Why this project stands out
*   **It solves a real business problem**: Keyword-based ATS systems are broken. Semantic matching fixes this.
*   **It uses modern database features**: pgvector is cutting-edge for Postgres.
*   **It implements robust background processes**: The multi-source API aggregation scheduler shows production-level data engineering.
*   **It requires no heavy frontend frameworks**: Demonstrates deep understanding of core web technologies, DOM manipulation, and state management.

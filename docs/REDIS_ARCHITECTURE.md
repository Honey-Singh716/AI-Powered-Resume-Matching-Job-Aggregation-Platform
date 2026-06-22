# Redis Architecture & Process Documentation
## AI Resume Matcher — Interview Preparation Guide

This document explains **every Redis-related process** in the project: why Redis exists, how it fits into the architecture, the full request lifecycle, cache invalidation, failure handling, and common interview questions with answers.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Why Redis in This Project?](#2-why-redis-in-this-project)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Redis Layer Design](#4-redis-layer-design)
5. [All Processes That Use Redis](#5-all-processes-that-use-redis)
6. [End-to-End Request Flows](#6-end-to-end-request-flows)
7. [Cache Key Design & TTL Strategy](#7-cache-key-design--ttl-strategy)
8. [Cache Invalidation Strategy](#8-cache-invalidation-strategy)
9. [Graceful Degradation (Redis Down)](#9-graceful-degradation-redis-down)
10. [Configuration & Deployment](#10-configuration--deployment)
11. [What Does NOT Use Redis](#11-what-does-not-use-redis)
12. [Known Gaps & Future Improvements](#12-known-gaps--future-improvements)
13. [Interview Q&A Cheat Sheet](#13-interview-qa-cheat-sheet)
14. [File Reference Map](#14-file-reference-map)

---

## 1. Executive Summary

| Question | Answer |
|----------|--------|
| **What does Redis cache?** | Job recommendation results for `GET /recommended-jobs` |
| **Why not cache in PostgreSQL?** | pgvector similarity search is expensive; Redis gives sub-millisecond reads for repeated requests |
| **Is Redis mandatory?** | **No.** The app falls back to PostgreSQL if Redis is unavailable |
| **How many features use Redis?** | **One** — candidate job recommendations |
| **Cache TTL** | 600 seconds (10 minutes) |
| **Invalidation trigger** | When a candidate uploads or updates their resume/profile |

**One-line interview answer:**
> "We use Redis as a read-through cache in front of an expensive pgvector cosine similarity query for personalized job recommendations, with TTL-based expiry and event-driven invalidation when the candidate profile changes."

---

## 2. Why Redis in This Project?

### The Problem

When a candidate opens **Recommended Jobs**, the backend must:

1. Load the candidate's 384-dimensional embedding vector from PostgreSQL
2. Run a **pgvector cosine distance** query across all jobs
3. Filter results with similarity score ≥ 0.30
4. Return paginated results

This query hits the database on **every page load, pagination click, and dashboard refresh**. As the job table grows (especially with the 6-hour external job aggregation pipeline), this becomes a performance bottleneck.

### The Solution

Redis stores the **serialized JSON result** of that query keyed by `(user_id, limit, skip)`. Subsequent identical requests skip the database entirely.

### Why Redis Specifically?

| Requirement | Redis fit |
|-------------|-----------|
| Fast in-memory reads | Sub-millisecond GET |
| TTL / auto-expiry | Built-in `SETEX` |
| Simple key-value | JSON string storage |
| Pattern-based delete | `KEYS` + `DELETE` for invalidation |
| Optional / non-critical | App works without it |

**Alternatives considered (good to mention in interviews):**

| Alternative | Why not used here |
|-------------|-------------------|
| PostgreSQL materialized views | Still disk-bound; harder to invalidate per-user |
| In-process Python dict cache | Lost on restart; not shared across multiple app instances |
| Memcached | No pattern delete; less flexible data structures |
| CDN / HTTP cache headers | Per-user personalized data; not suitable for shared CDN cache |

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (SPA)                                   │
│   app.js → GET /recommended-jobs?limit=9&skip=0                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ JWT Bearer Token
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FastAPI — route/job_routes.py                       │
│   get_recommended_jobs_endpoint() → recommend_jobs_for_candidate()       │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      services/job_service.py                             │
│                                                                          │
│   ┌──────────────┐    MISS     ┌──────────────────────────────────┐   │
│   │ Redis Cache  │────────────►│ PostgreSQL + pgvector              │   │
│   │   (READ)     │             │ get_recommended_jobs()             │   │
│   └──────┬───────┘             └──────────────────┬───────────────┘   │
│          │ HIT                                   │                     │
│          │                          ┌────────────▼───────────────┐   │
│          │                          │ Redis Cache (WRITE / SETEX) │   │
│          │                          └────────────────────────────┘   │
│          ▼                                                             │
│   Return JSON list of recommended jobs                                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│              INVALIDATION PATH (profile change)                          │
│                                                                          │
│   POST /upload_resume  ──►  save_candidate()  ──►  invalidate cache     │
│   POST /parse_resume   ──►  save_candidate()  ──►  invalidate cache     │
│   update_candidate()   ──►  candidate_repo     ──►  invalidate cache     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack (Redis Context)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   FastAPI   │────►│    Redis    │     │  PostgreSQL         │
│  (Python)   │     │  (Cache)    │     │  + pgvector (SoT)   │
└─────────────┘     └─────────────┘     └─────────────────────┘
      │                                         ▲
      └─────────────────────────────────────────┘
              Source of Truth for all data
```

**Key principle:** PostgreSQL is always the **source of truth**. Redis is a **performance layer** only.

---

## 4. Redis Layer Design

### File: `services/redis_service.py`

This is the **single abstraction layer** for all Redis operations. No other file talks to the Redis client directly.

#### Connection Management

```python
# Singleton lazy client with retry cooldown
_redis_client: Optional[redis.Redis] = None
_redis_last_attempt: float = 0.0
RETRY_COOLDOWN_SECONDS = 30
```

| Function | Purpose | When called |
|----------|---------|-------------|
| `get_redis_client(force=False)` | Returns connected client or `None` | Every cache operation |
| `init_redis()` | Eager connect on startup (`force=True`) | App startup |
| `close_redis()` | Close connection cleanly | App shutdown |

**Connection settings:**

```python
redis.Redis.from_url(
    REDIS_URL,
    socket_timeout=2.0,           # Don't block requests too long
    socket_connect_timeout=2.0,
    decode_responses=True,        # Return str, not bytes (for JSON)
)
```

**Retry cooldown logic:**
- If Redis fails, don't retry on every request (would add 2s latency each time)
- Wait 30 seconds before attempting reconnection
- Startup always forces a connection attempt via `init_redis(force=True)`

#### Public Cache API

| Function | Redis Command | Description |
|----------|---------------|-------------|
| `get_cached_recommendations(user_id, limit, skip)` | `GET` | Read cached job list |
| `set_cached_recommendations(user_id, limit, skip, data, expire_seconds=600)` | `SETEX` | Write cache with 10-min TTL |
| `invalidate_candidate_recommendations(user_id)` | `KEYS` + `DELETE` | Remove all cache entries for a user |

---

## 5. All Processes That Use Redis

Redis is involved in exactly **3 processes**:

### Process 1 — Cache Read (Recommendation Fetch)

**Trigger:** Candidate requests recommended jobs  
**Endpoint:** `GET /recommended-jobs?limit={n}&skip={n}`  
**Entry point:** `route/job_routes.py` → `services/job_service.py`

```
Step 1: Authenticate JWT → get user.id
Step 2: Call get_cached_recommendations(user_id, limit, skip)
Step 3a: CACHE HIT  → return JSON immediately (no DB query)
Step 3b: CACHE MISS → query PostgreSQL pgvector → filter → cache → return
```

**Code path:**

```
job_routes.get_recommended_jobs_endpoint()
  └── job_service.recommend_jobs_for_candidate()
        ├── redis_service.get_cached_recommendations()   ← READ
        ├── candidate_repo.get_candidate_by_user_id()      ← DB (on miss)
        ├── job_repo.get_recommended_jobs()                ← DB pgvector (on miss)
        └── redis_service.set_cached_recommendations()     ← WRITE (on miss)
```

---

### Process 2 — Cache Write (After DB Query)

**Trigger:** Cache miss on recommendation fetch  
**When:** First request, after TTL expiry, or after invalidation

```
Step 1: Run pgvector similarity search
Step 2: Build list of jobs with similarity_score >= 0.30
Step 3: Serialize to JSON
Step 4: SETEX recommendations:{user_id}:{limit}:{skip} 600 {json}
```

**Cached payload example:**

```json
[
  {
    "id": 42,
    "title": "Senior Python Developer",
    "company": "TechCorp",
    "location": "Remote",
    "source": "remoteok",
    "job_url": "https://...",
    "similarity_score": 0.7842
  }
]
```

---

### Process 3 — Cache Invalidation (Profile Change)

**Trigger:** Candidate profile data changes (embedding/skills/experience updated)

| Trigger endpoint | Service function | Invalidation call |
|-----------------|------------------|-------------------|
| `POST /upload_resume` | `save_candidate()` | `invalidate_candidate_recommendations(user_id)` |
| `POST /parse_resume` | `save_candidate()` | `invalidate_candidate_recommendations(user_id)` |
| `update_candidate()` (repo) | `candidate_repo.update_candidate()` | `invalidate_candidate_recommendations(user_id)` |

**Invalidation logic:**

```python
pattern = f"recommendations:{user_id}:*"
keys = client.keys(pattern)   # Find all pagination variants
client.delete(*keys)          # Delete all at once
```

This clears cache for **all pagination combinations** (e.g., `limit=9&skip=0`, `limit=9&skip=9`, etc.) for that user.

**Why invalidate on profile change?**
The recommendation result depends on the candidate's **embedding vector**. If skills/experience change, the embedding changes, so cached results would be **stale and incorrect**.

---

## 6. End-to-End Request Flows

### Flow A — First Visit (Cold Cache)

```
Candidate Browser          FastAPI              Redis           PostgreSQL
      │                      │                   │                  │
      │ GET /recommended-jobs│                   │                  │
      │─────────────────────►│                   │                  │
      │                      │ GET recommendations:5:9:0            │
      │                      │──────────────────►│                  │
      │                      │      (nil) MISS   │                  │
      │                      │◄──────────────────│                  │
      │                      │                   │  pgvector query  │
      │                      │─────────────────────────────────────►│
      │                      │         [(job, score), ...]          │
      │                      │◄─────────────────────────────────────│
      │                      │ SETEX key 600 json                   │
      │                      │──────────────────►│                  │
      │   [{jobs...}]        │                   │                  │
      │◄─────────────────────│                   │                  │
```

### Flow B — Repeat Visit (Warm Cache)

```
Candidate Browser          FastAPI              Redis
      │                      │                   │
      │ GET /recommended-jobs│                   │
      │─────────────────────►│                   │
      │                      │ GET recommendations:5:9:0
      │                      │──────────────────►│
      │                      │   JSON data HIT   │
      │                      │◄──────────────────│
      │   [{jobs...}]        │  (no DB query)    │
      │◄─────────────────────│                   │
```

**Latency comparison (typical):**

| Path | Approximate latency |
|------|---------------------|
| Cache HIT | ~1–5 ms |
| Cache MISS (pgvector) | ~50–500 ms (depends on job count) |

### Flow C — Resume Upload (Invalidation)

```
Candidate Browser          FastAPI              Redis           PostgreSQL
      │                      │                   │                  │
      │ POST /upload_resume  │                   │                  │
      │─────────────────────►│                   │                  │
      │                      │ Groq AI parse     │                  │
      │                      │ generate embedding│                  │
      │                      │─────────────────────────────────────►│
      │                      │         UPDATE candidate             │
      │                      │◄─────────────────────────────────────│
      │                      │ KEYS recommendations:5:*             │
      │                      │──────────────────►│                  │
      │                      │ DELETE [keys...]  │                  │
      │                      │──────────────────►│                  │
      │  {profile data}      │                   │                  │
      │◄─────────────────────│                   │                  │
      │                      │                   │                  │
      │ GET /recommended-jobs│                   │                  │
      │─────────────────────►│  → CACHE MISS → fresh DB query       │
```

### Flow D — App Startup / Shutdown

**Startup (`main.py` → `on_startup`):**

```
1. load_dotenv()                    # Load REDIS_URL from .env
2. start_scheduler()                # Job aggregation (no Redis)
3. init_redis()                     # Ping Redis, log success/failure
   ├── Success → "Redis caching enabled for job recommendations."
   └── Failure → "Redis not available. Job recommendations will use database only."
```

**Shutdown (`main.py` → `on_shutdown`):**

```
1. stop_scheduler()
2. close_redis()                    # Clean connection close
```

---

## 7. Cache Key Design & TTL Strategy

### Key Naming Convention

```
recommendations:{user_id}:{limit}:{skip}
```

**Examples:**

| Key | Meaning |
|-----|---------|
| `recommendations:5:10:0` | User 5, first 10 jobs |
| `recommendations:5:10:10` | User 5, next 10 jobs (pagination) |
| `recommendations:5:9:0` | User 5, first 9 jobs (frontend default) |

### Why include `limit` and `skip` in the key?

Pagination parameters affect the query result. Caching only by `user_id` would return wrong data when the user paginates.

### TTL: 600 seconds (10 minutes)

```python
client.setex(key, expire_seconds, json.dumps(data))  # default expire_seconds=600
```

| TTL choice | Rationale |
|------------|-----------|
| **Too short** (< 60s) | Cache hit rate drops; DB load stays high |
| **10 minutes** | Balance: good hit rate for active users; acceptable staleness window |
| **Too long** (> 1 hour) | New jobs added by scheduler won't appear until TTL expires |

**Interview note:** TTL is a **safety net**. Primary freshness guarantee is **invalidation on profile change**. TTL handles cases where new jobs are added but cache wasn't explicitly invalidated.

---

## 8. Cache Invalidation Strategy

This project uses a **hybrid invalidation model**:

| Strategy | Used for | Implementation |
|----------|----------|----------------|
| **Event-driven (write-through invalidation)** | Profile changes | `invalidate_candidate_recommendations()` after resume save |
| **Time-based (TTL expiry)** | Everything else | `SETEX` with 600s |

### Invalidation scope

```
recommendations:{user_id}:*
```

Deletes **all paginated cache entries** for one user without affecting other users.

### What triggers invalidation today

| Event | Invalidated? |
|-------|-------------|
| Candidate uploads resume | ✅ Yes |
| Candidate parses resume text | ✅ Yes |
| Candidate profile updated via repo | ✅ Yes |
| Recruiter creates new job | ❌ No (relies on TTL) |
| Scheduler adds external jobs (every 6h) | ❌ No (relies on TTL) |
| Candidate applies to a job | ❌ No (doesn't change recommendations) |

---

## 9. Graceful Degradation (Redis Down)

The system is designed to **never fail** because Redis is unavailable.

```
get_redis_client() returns None
        │
        ▼
get_cached_recommendations() → returns None  (treated as MISS)
set_cached_recommendations() → no-op
invalidate_candidate_recommendations() → no-op
        │
        ▼
recommend_jobs_for_candidate() → always hits PostgreSQL
```

### Failure handling layers

| Layer | Behavior |
|-------|----------|
| Connection failure | Log warning, return `None`, 30s retry cooldown |
| GET error | Log error, return `None` (fallback to DB) |
| SET error | Log error, still return DB result to user |
| DELETE error | Log error, stale cache expires via TTL |

**Interview answer:**
> "Redis is an optimization, not a dependency. We follow the cache-aside pattern with graceful degradation — if Redis is down, every request becomes a cache miss and the pgvector query runs normally. Users still get correct results, just slower."

---

## 10. Configuration & Deployment

### Environment Variable

```env
REDIS_URL=redis://localhost:6379/0
```

| Component | Default if unset |
|-----------|-------------------|
| `REDIS_URL` | `redis://localhost:6379/0` |

### Docker Compose (local dev)

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes   # AOF persistence
```

**AOF (Append Only File):** Redis persists cache to disk. If Redis restarts, cached data survives (until TTL expires). This is optional for a cache layer but good for dev continuity.

### Python dependency

```
redis==5.0.8
```

### Startup verification

```powershell
docker compose up -d redis
uvicorn main:app --reload
# Look for: "Redis caching enabled for job recommendations."
```

Or use the helper script:

```powershell
.\scripts\start-redis.ps1
```

---

## 11. What Does NOT Use Redis

Important for interviews — know the boundaries:

| Feature | Storage | Why no Redis |
|---------|---------|--------------|
| User auth / JWT | Stateless JWT | No server-side session to store |
| Resume parsing (Groq) | N/A | External API call each time |
| AI chat | Groq API | Dynamic, personalized, not repeated |
| Job listing `GET /jobs` | PostgreSQL | Generic list, not per-user expensive query |
| Applications | PostgreSQL | CRUD, not cache-heavy |
| Match score `/match/{cid}/{jid}` | PostgreSQL | Single pair lookup, fast enough |
| Legacy recommend `/recommend/{cid}` | PostgreSQL | Separate code path, no cache added |
| Job aggregation scheduler | PostgreSQL | Background write, not read cache |
| Frontend saved jobs | Browser localStorage | Client-side only |

---

## 12. Known Gaps & Future Improvements

Good talking points to show architectural thinking:

### Gap 1 — New jobs don't invalidate cache

When the scheduler adds 100 new jobs or a recruiter posts a job, existing recommendation caches remain until TTL (10 min).

**Fix:** Add global or per-user invalidation in `save_job()` and `job_fetch_service`:

```python
# Future: invalidate all recommendation caches when job catalog changes
def invalidate_all_recommendations():
    client.delete(*client.keys("recommendations:*"))
```

### Gap 2 — `KEYS` command in production

`KEYS recommendations:{user_id}:*` scans all keys — **O(N)** and blocks Redis on large datasets.

**Production fix:** Use `SCAN` iterator or Redis Hash per user:

```
HSET user:5:recommendations "10:0" {json}
HDEL user:5:recommendations  # invalidate all fields for user
```

### Gap 3 — `/recommend/{candidate_id}` not cached

The older match route loops all jobs in Python. Could share the same Redis layer.

### Gap 4 — No cache warming

Could pre-compute recommendations after resume upload instead of waiting for first GET.

### Gap 5 — Multi-instance deployments

Current singleton client works per process. For horizontal scaling, all instances share one Redis — which is correct. No sticky sessions needed.

---

## 13. Interview Q&A Cheat Sheet

### Q1: Why did you add Redis to this project?

> The `/recommended-jobs` endpoint runs a pgvector cosine similarity search across all jobs for every request. As the job table grows, this becomes expensive. Redis caches the computed result per user and pagination params, reducing DB load and response time from hundreds of milliseconds to single-digit milliseconds on cache hits.

---

### Q2: What caching pattern did you use?

> **Cache-aside (lazy loading).** The application checks Redis first. On miss, it reads from PostgreSQL, populates the cache, and returns the result. The application owns cache consistency — not the database.

---

### Q3: How do you keep the cache fresh?

> Two mechanisms: **event-driven invalidation** when the candidate profile changes (resume upload updates the embedding), and **TTL expiry** (10 minutes) as a fallback for when new jobs are added without explicit invalidation.

---

### Q4: What happens if Redis goes down?

> Graceful degradation. `get_redis_client()` returns `None`, cache functions become no-ops, and every request falls through to PostgreSQL. Users get correct data with higher latency. The app logs a warning at startup but does not crash.

---

### Q5: Why cache JSON strings instead of storing embeddings in Redis?

> We cache the **final API response** (filtered, formatted job list), not raw vectors. The expensive part is the pgvector ORDER BY similarity query plus application-layer filtering. Caching the end result avoids re-running the query and re-serializing on every hit.

---

### Q6: Why is the key `recommendations:{user_id}:{limit}:{skip}`?

> Recommendations are **per-user** (based on their embedding), and **pagination-aware** (limit/skip change the SQL OFFSET/LIMIT). Including all three dimensions prevents serving wrong paginated data from cache.

---

### Q7: Is Redis the source of truth?

> **No.** PostgreSQL is the source of truth for candidates, jobs, and embeddings. Redis is ephemeral cache data. If Redis is flushed, the app rebuilds cache from PostgreSQL on the next request.

---

### Q8: How would you scale this in production?

> - Replace `KEYS` with `SCAN` or Redis Hashes for invalidation  
> - Use Redis Cluster or managed Redis (ElastiCache, Upstash) for HA  
> - Add cache invalidation when jobs are created/updated  
> - Monitor hit rate, memory usage, and eviction policy  
> - Consider shorter TTL + proactive cache warming after profile updates  
> - All app instances share one Redis — no per-instance cache needed

---

### Q9: What's the difference between `/recommended-jobs` and `/recommend/{candidate_id}`?

> `/recommended-jobs` is the authenticated production endpoint using pgvector SQL ordering with Redis caching. `/recommend/{candidate_id}` is a legacy route that loads all jobs and scores them in Python — no Redis, no pagination, less efficient.

---

### Q10: Why 10-minute TTL?

> Long enough to benefit repeat dashboard visits and pagination within a session. Short enough that new jobs from the aggregation scheduler appear within a reasonable window even without explicit invalidation. Combined with profile-change invalidation, this balances performance and freshness.

---

## 14. File Reference Map

| File | Redis role |
|------|------------|
| `services/redis_service.py` | **Core** — connection, get, set, invalidate |
| `services/job_service.py` | **Consumer** — read-through cache in `recommend_jobs_for_candidate()` |
| `services/candidate_service.py` | **Invalidator** — clears cache after `save_candidate()` |
| `repositories/candidate_repo.py` | **Invalidator** — clears cache after `update_candidate()` |
| `route/job_routes.py` | **HTTP entry** — `GET /recommended-jobs` |
| `route/resume_routes.py` | **Indirect trigger** — upload/parse → save_candidate → invalidate |
| `repositories/job_repo.py` | **DB layer** — pgvector query (runs on cache miss only) |
| `main.py` | **Lifecycle** — `init_redis()` on startup, `close_redis()` on shutdown |
| `docker-compose.yml` | **Infrastructure** — Redis 7 container |
| `.env` / `.env.example` | **Config** — `REDIS_URL` |
| `requirements.txt` | **Dependency** — `redis==5.0.8` |
| `scripts/start-redis.ps1` | **Dev tooling** — start Redis + verify connection |
| `frontend/app.js` | **Client** — calls `/recommended-jobs?limit=&skip=` |

---

## Quick Reference — Redis Operations Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    REDIS OPERATIONS MAP                          │
├──────────────────┬──────────────────┬───────────────────────────┤
│ Operation        │ Redis Command    │ Trigger                   │
├──────────────────┼──────────────────┼───────────────────────────┤
│ Cache Read       │ GET              │ GET /recommended-jobs     │
│ Cache Write      │ SETEX (600s)     │ Cache miss after DB query │
│ Cache Invalidate │ KEYS + DELETE    │ Resume upload/update      │
│ Health Check     │ PING             │ App startup (init_redis)  │
│ Connection Close │ CLOSE            │ App shutdown              │
└──────────────────┴──────────────────┴───────────────────────────┘
```

---

*Document version: aligned with codebase as of June 2026. Redis scope: job recommendation caching only.*

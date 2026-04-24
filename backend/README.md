# HistoryLive — Backend API

Production-grade FastAPI backend for the **HistoryLive** platform (CUNY AI Innovation Challenge 2026). It turns a speech selection into a fully rendered historical documentary video through a multi-agent AI pipeline with human-in-the-loop review gates.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Quick Start (Local Dev)](#quick-start-local-dev)
5. [Environment Variables](#environment-variables)
6. [Running the Server](#running-the-server)
7. [Running the Worker](#running-the-worker)
8. [Database Migrations](#database-migrations)
9. [API Reference](#api-reference)
10. [AI Pipeline](#ai-pipeline)
11. [Authentication](#authentication)
12. [Access Tiers & Cost Caps](#access-tiers--cost-caps)
13. [Real-Time Events (SSE)](#real-time-events-sse)
14. [Receipts](#receipts)
15. [Deployment](#deployment)

---

## Architecture Overview

```
Browser / Frontend
       │
       ▼
  FastAPI API  ──── Redis pub/sub ────► SSE /events stream
       │
       ▼
   RQ Worker
       │
       ▼
  LangGraph Pipeline
  ┌────────────────────────────────────────────────┐
  │  Research → Script → Seed → Storyboard        │
  │     ↕ (human review gates)                    │
  │  Voice → Video → Receipt                      │
  └────────────────────────────────────────────────┘
       │
       ▼
  PostgreSQL (state)  +  MinIO/S3 (assets)
```

Each pipeline stage is an **agent** that calls one or more AI providers, stores results in Postgres with confidence tags (`verified` / `approximated` / `speculative`), and emits a real-time SSE event to the browser.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI 0.115+ |
| Data validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 + RQ |
| Orchestration | LangGraph |
| Auth | JWT (python-jose) + httpOnly cookies |
| Object storage | MinIO (dev) / S3 or Cloudflare R2 (prod) |
| AI — research & script | Anthropic Claude 3.5 Sonnet |
| AI — image generation | Google Imagen 3 |
| AI — video generation | HiggsField (Veo fallback) |
| AI — voice synthesis | ElevenLabs v3 |
| Observability | structlog + OpenTelemetry |

---

## Project Structure

```
backend/
├── alembic/                  # Database migrations
│   ├── env.py                # Async Alembic environment
│   ├── script.py.mako        # Migration file template
│   └── versions/             # Generated migration files
├── alembic.ini               # Alembic configuration
├── app/
│   ├── main.py               # FastAPI app factory + lifespan
│   ├── config.py             # Pydantic-settings (all env vars)
│   ├── db.py                 # Async SQLAlchemy engine + session
│   ├── redis_client.py       # Redis pool + pub/sub helpers
│   ├── ids.py                # ULID prefixed ID generator
│   ├── adapters/             # Thin AI provider clients
│   │   ├── anthropic.py      # Anthropic Messages API
│   │   ├── google.py         # Google Imagen 3
│   │   ├── elevenlabs.py     # ElevenLabs TTS v3
│   │   ├── higgsfield.py     # HiggsField video generation
│   │   └── storage.py        # MinIO / S3 object storage
│   ├── agents/               # AI pipeline agents
│   │   ├── base.py           # BaseAgent (audit logging, cost caps)
│   │   ├── research.py       # Historical research agent
│   │   ├── script.py         # Scripting / shot-list agent
│   │   ├── seed_image.py     # Reference image generator
│   │   ├── storyboard.py     # Per-shot frame generator
│   │   ├── voice.py          # Narration synthesis agent
│   │   └── video.py          # Video clip generation agent
│   ├── api/                  # FastAPI routers
│   │   ├── auth.py           # Register, login, logout, me
│   │   ├── sessions.py       # Create / get sessions
│   │   ├── research.py       # Research stage endpoints
│   │   ├── script.py         # Script stage endpoints
│   │   ├── seed.py           # Seed image endpoints
│   │   ├── storyboard.py     # Storyboard endpoints
│   │   ├── media.py          # Voice + video endpoints
│   │   ├── artifacts.py      # Artifacts + receipt download
│   │   ├── events.py         # SSE event stream
│   │   ├── speeches.py       # Speech catalog
│   │   └── admin.py          # Admin controls
│   ├── middleware/
│   │   ├── auth.py           # Request ID injection
│   │   └── rate_limit.py     # slowapi limiter
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── base.py           # DeclarativeBase + TimestampMixin
│   │   ├── user.py           # UserAccount
│   │   ├── session.py        # ProjectSession (state machine)
│   │   ├── research.py       # ResearchForm
│   │   ├── script.py         # ScriptPackage
│   │   ├── seed.py           # SeedImage (versioned)
│   │   ├── storyboard.py     # Storyboard
│   │   ├── voice.py          # VoiceTrack
│   │   ├── video.py          # VideoRender
│   │   ├── audit.py          # AgentRun (cost + token audit)
│   │   └── moderation.py     # ContentModerationLog
│   ├── orchestrator/
│   │   ├── state.py          # LangGraph SessionState TypedDict
│   │   ├── graph.py          # StateGraph definition
│   │   └── nodes.py          # Node functions + routing logic
│   ├── queue/
│   │   ├── jobs.py           # enqueue_agent() helper
│   │   ├── jobs_impl.py      # Async agent dispatch
│   │   └── worker.py         # RQ worker entry point
│   ├── receipts/
│   │   └── generator.py      # Receipt builder + Markdown renderer
│   ├── schemas/              # Pydantic v2 request/response models
│   │   ├── common.py         # ConfidenceField, UXChoices, ErrorResponse
│   │   ├── session.py        # SessionCreate, SessionOut, CostProjection
│   │   ├── research.py       # ResearchFormOut, ResearchRevise
│   │   ├── script.py         # ScriptPackageOut, ScriptRevise
│   │   ├── seed.py           # SeedImageOut, SeedRevise
│   │   ├── storyboard.py     # StoryboardOut, StoryboardRevise
│   │   ├── receipt.py        # Receipt, ReceiptRunDetail, ConfidenceSummary
│   │   └── auth.py           # RegisterRequest, LoginRequest, TokenOut
│   └── speeches/
│       └── catalog.py        # Curated speech catalog + get_speech_by_id()
├── .env.example              # All environment variables documented
├── docker-compose.yml        # API, worker, Postgres, Redis, MinIO
├── Dockerfile                # Production image
└── pyproject.toml            # Dependencies (hatch)
```

---

## Quick Start (Local Dev)

### Prerequisites

- Python 3.12+
- Docker Desktop (for Postgres, Redis, MinIO)

### 1. Clone and install

```bash
cd backend
pip install -e ".[dev]"
```

### 2. Start infrastructure

```bash
docker compose up db redis minio -d
```

This starts:
- **PostgreSQL 16** on port `5432`
- **Redis 7** on port `6379`
- **MinIO** on port `9000` (console on `9001`)

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Start the RQ worker (separate terminal)

```bash
python -m app.queue.worker
```

The API is now at **http://localhost:8000** and the interactive docs at **http://localhost:8000/docs**.

---

## Environment Variables

All variables are documented in [`.env.example`](.env.example). Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `APP_SECRET_KEY` | JWT signing secret (min 32 chars) | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `ANTHROPIC_API_KEY` | Used by Research + Script agents | Yes |
| `GOOGLE_API_KEY` | Used by Seed Image + Storyboard agents | Yes |
| `ELEVENLABS_API_KEY` | Used by Voice agent | Yes |
| `HIGGSFIELD_API_KEY` | Used by Video agent | Yes |
| `STORAGE_ENDPOINT` | MinIO URL (dev) or omit for AWS S3 | Yes |
| `STORAGE_ACCESS_KEY` | MinIO / AWS access key | Yes |
| `STORAGE_SECRET_KEY` | MinIO / AWS secret key | Yes |
| `APP_CORS_ORIGINS` | Comma-separated allowed origins | Yes |
| `APP_ENV` | `development` / `staging` / `production` | No |

---

## Running the Server

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --port 8000

# Production (via Docker)
docker compose up api
```

Health check: `GET /health` → `{"status": "ok", "version": "1.0.0"}`

Interactive API docs (dev only): `http://localhost:8000/docs`

---

## Running the Worker

The RQ worker processes all AI agent jobs from the `pipeline` queue:

```bash
# Direct
python -m app.queue.worker

# Via Docker
docker compose up worker
```

Each agent job is idempotent — safe to retry on failure.

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Rollback one step
alembic downgrade -1
```

---

## API Reference

All endpoints are under the `/api/v1` prefix.

> Full interactive documentation is available at `http://localhost:8000/docs` when running in development mode.

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/register` | Create a new account |
| `POST` | `/api/v1/auth/login` | Obtain JWT token + set cookie |
| `POST` | `/api/v1/auth/logout` | Clear auth cookie |
| `GET` | `/api/v1/auth/me` | Get current user profile |

### Speeches

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/speeches` | List all available speeches (public) |

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sessions` | Create a new production session |
| `GET` | `/api/v1/sessions/{id}` | Get session state |
| `GET` | `/api/v1/sessions/{id}/cost_projection` | Estimated cost for remaining stages |

### Research Stage

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sessions/{id}/research/start` | Enqueue Research Agent (→ 202) |
| `GET` | `/api/v1/sessions/{id}/research` | Get completed research form |
| `POST` | `/api/v1/sessions/{id}/research/approve` | Approve → advances to Scripting |
| `POST` | `/api/v1/sessions/{id}/research/revise` | Re-run with editor notes |

### Script Stage

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sessions/{id}/script/start` | Enqueue Scripting Agent |
| `GET` | `/api/v1/sessions/{id}/script` | Get completed script package |
| `POST` | `/api/v1/sessions/{id}/script/approve` | Approve → advances to Seed Image |
| `POST` | `/api/v1/sessions/{id}/script/revise` | Re-run with targeted changes |

### Seed Image Stage

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sessions/{id}/seed/generate` | Generate reference hero image |
| `GET` | `/api/v1/sessions/{id}/seed` | Get current seed image |
| `GET` | `/api/v1/sessions/{id}/seed/versions` | List all seed image versions |
| `POST` | `/api/v1/sessions/{id}/seed/approve` | Approve → advances to Storyboard |
| `POST` | `/api/v1/sessions/{id}/seed/revise` | Regenerate with notes |

### Storyboard Stage

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sessions/{id}/storyboard/generate` | Generate all storyboard frames |
| `GET` | `/api/v1/sessions/{id}/storyboard` | Get full storyboard |
| `GET` | `/api/v1/sessions/{id}/storyboard/frames/{idx}` | Get a single frame |
| `POST` | `/api/v1/sessions/{id}/storyboard/approve` | Approve → triggers Voice generation |
| `POST` | `/api/v1/sessions/{id}/storyboard/revise` | Regenerate with shot-level notes |

### Media (Voice & Video)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/sessions/{id}/voice` | Get generated voice track |
| `GET` | `/api/v1/sessions/{id}/video` | Get final rendered video |
| `GET` | `/api/v1/sessions/{id}/video/clips` | List all video clips |
| `GET` | `/api/v1/sessions/{id}/video/clips/{idx}` | Get a specific clip |

### Artifacts & Receipt

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/sessions/{id}/artifacts` | List all produced artifacts with URLs |
| `GET` | `/api/v1/sessions/{id}/research/report` | Research report (Markdown) |
| `GET` | `/api/v1/sessions/{id}/script/report` | Script package report (Markdown) |
| `GET` | `/api/v1/sessions/{id}/receipt` | Full production receipt (Markdown default, `?format=json`) |

### Events (SSE)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/sessions/{id}/events` | Real-time pipeline progress stream |

### Admin *(requires admin role)*

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/admin/submissions/{id}/approve` | Approve a pending session |
| `POST` | `/api/v1/admin/submissions/{id}/reject` | Reject with reason |
| `POST` | `/api/v1/admin/users/{id}/freeze` | Freeze a user account |
| `POST` | `/api/v1/admin/kill_switch` | Pause/resume all job processing |

---

## AI Pipeline

The pipeline runs as a **LangGraph state machine** (`app/orchestrator/graph.py`). Each stage is a node; human review gates are implemented as `END` checkpoints — the graph resumes from the next queue job after the user approves via the API.

```
[created]
    │
    ▼
[researching] ──► Research Agent (Anthropic) ──► [research_review] ←── human gate
    │
    ▼
[scripting] ──► Scripting Agent (Anthropic) ──► [scripting_review] ←── human gate
    │
    ▼
[seed_generating] ──► Seed Image Agent (Google Imagen 3) ──► [seed_review] ←── human gate
    │
    ▼
[storyboard_generating] ──► Storyboard Agent (Google Imagen 3, per shot) ──► [storyboard_review] ←── human gate
    │
    ▼
[voice_generating] ──► Voice Agent (ElevenLabs v3) ──── automatic
    │
    ▼
[video_generating] ──► Video Agent (HiggsField / Veo) ──── automatic
    │
    ▼
[rendered]
```

Every agent records cost (in cents), token usage, and model version to the `agent_runs` table for full auditability.

### Confidence Tags

Every AI-generated field is tagged with one of three confidence levels:

| Tag | Meaning |
|-----|---------|
| `verified` | Sourced from a primary historical record |
| `approximated` | Based on strong secondary evidence |
| `speculative` | Plausible but not directly evidenced |

The worst tag across all fields propagates to the final video render.

---

## Authentication

The API uses **JWT** tokens with two delivery mechanisms:

1. **httpOnly cookie** (`access_token`) — set on login, cleared on logout. Used by browser clients.
2. **Bearer token** in `Authorization` header — for programmatic/API access.

`get_current_user` in `app/api/deps.py` checks the Bearer header first, then falls back to the cookie.

Tokens expire after 60 minutes by default. Passwords require a minimum of 10 characters.

---

## Access Tiers & Cost Caps

| Tier | Daily cap | Weekly cap | Auto-generate |
|------|-----------|------------|---------------|
| `public` | 1 session | — | No (admin approval required) |
| `whitelisted` | 2 sessions | 10 sessions | Yes |
| `admin` | Unlimited | Unlimited | Yes |

Global cost guard rails (configurable via env):

- `MAX_COST_CENTS_PER_REQUEST` — per-session ceiling (default 2000¢ = $20)
- `MAX_COST_CENTS_PER_USER_DAY` — per-user daily ceiling (default 5000¢ = $50)
- `MAX_COST_CENTS_GLOBAL_DAY` — platform-wide daily ceiling (default 50000¢ = $500)

---

## Real-Time Events (SSE)

Connect to `GET /api/v1/sessions/{id}/events` to receive a server-sent events stream.

```javascript
const es = new EventSource('/api/v1/sessions/sess_01.../events', {
  withCredentials: true,
});

es.addEventListener('research_complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Research done, state:', data.state);
});

es.addEventListener('rendered', (e) => {
  const { video_url } = JSON.parse(e.data);
  console.log('Video ready:', video_url);
  es.close();
});
```

### Event types

| Event | Fired when |
|-------|-----------|
| `connected` | Stream opens |
| `heartbeat` | Every ~25 s (keep-alive) |
| `research_complete` | Research agent finishes |
| `scripting_complete` | Scripting agent finishes |
| `seed_complete` | Seed image generated |
| `storyboard_complete` | All storyboard frames generated |
| `voice_complete` | Narration synthesized |
| `rendered` | Final video ready |
| `failed` | Any agent encountered a fatal error |

---

## Receipts

After a session reaches `rendered`, download a full production receipt:

```bash
# Markdown (default)
GET /api/v1/sessions/{id}/receipt

# JSON
GET /api/v1/sessions/{id}/receipt?format=json
```

The receipt includes:
- All agent runs with model, token counts, and cost in cents
- All artifact URLs (research form, script, seed image, storyboard frames, voice, video)
- Confidence summary (verified / approximated / speculative counts)
- Total cost breakdown

---

## Deployment

### Docker Compose (staging / single server)

```bash
docker compose up --build
```

Runs: `api` + `worker` + `db` + `redis` + `minio`

To run one-off migrations:

```bash
docker compose run --rm migrate
```

### Production checklist

- [ ] Set `APP_ENV=production` (disables `/docs` and `/redoc`)
- [ ] Set a strong random `APP_SECRET_KEY` (64+ hex chars)
- [ ] Point `DATABASE_URL` to a managed PostgreSQL instance
- [ ] Point `REDIS_URL` to a managed Redis instance
- [ ] Replace MinIO with `STORAGE_ENDPOINT` pointing to Cloudflare R2 or AWS S3
- [ ] Set `APP_CORS_ORIGINS` to your actual frontend domain(s)
- [ ] Configure `OTEL_EXPORTER_OTLP_ENDPOINT` for distributed tracing
- [ ] Run `alembic upgrade head` before deploying new containers

---

## Speech Catalog

Six speeches are available out of the box:

| ID | Figure | Title | Year |
|----|--------|-------|------|
| `kennedy-inaugural-1961-01-20` | John F. Kennedy | Inaugural Address | 1961 |
| `gettysburg-1863` | Abraham Lincoln | Gettysburg Address | 1863 |
| `ihaveadream-1963` | Martin Luther King Jr. | I Have a Dream | 1963 |
| `fdr-infamy-1941` | Franklin D. Roosevelt | Day of Infamy Speech | 1941 |
| `sojourner-truth-aint-i-a-woman-1851` | Sojourner Truth | Ain't I a Woman? | 1851 |
| `lincoln-second-inaugural-1865` | Abraham Lincoln | Second Inaugural Address | 1865 |

To add more speeches, extend `SPEECH_CATALOG` in `app/speeches/catalog.py`.

# Fineas — TODO

## Phase 1: Generic Core
- [x] DB schema: `assets` + `asset_snapshots` models (SQLAlchemy 2.0)
- [x] Async DB engine + session factory (`database.py`)
- [x] Python dependencies (`requirements.txt`)
- [x] Pydantic schemas (request/response validation)
- [x] FastAPI routers: CRUD for assets and snapshots
- [x] Alembic migrations (generate from models)
- [x] Docker Compose setup (PostgreSQL + API)

## Phase 2: The Math
- [x] Deterministic projection engine (pure Python, no LLM)
- [x] Soft-delete / `is_archived` flag on `assets` (auditability)
- [x] FIRE target calculator (time-to-retirement given savings rate + return)
- [x] Portfolio projection endpoint (`GET /portfolio/projection`)

## Phase 3: Smart Ingestion
- [x] LLM-powered parser: free-text / CSV → structured JSON
- [x] Upsert endpoint using `ON CONFLICT (asset_id, snapshot_date) DO UPDATE`
- [x] Validation node in LangGraph pipeline
- [x] LangGraph parse→validate graph
- [x] Multi-LLM support (Anthropic / OpenRouter / Groq via LangChain)
- [x] 130+ tests passing

## Phase 4: The Agent
- [ ] LangGraph state machine for portfolio update workflow
- [ ] Human-in-the-loop (HITL) confirmation step
- [ ] Frontend chat UI wired to agent

## Phase 5: Frontend (Next.js)
- [x] Scaffold Next.js 14 + Tailwind CSS + design system tokens
- [x] API client layer (types, fetch wrappers, React Query)
- [x] Shared components (Navbar, KpiCard, GlassModal, charts)
- [x] Dashboard page (KPIs, projection chart, allocation donut)
- [x] Assets page (table, filter pills, add modal)
- [x] Asset Detail page (chart, snapshot table, add snapshot modal)
- [x] FIRE Calculator page (parameter panel, scenario chart)
- [x] Smart Import page (parse → review → confirm pipeline)
- [x] Docker Compose integration + frontend Dockerfile

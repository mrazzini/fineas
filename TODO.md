# Fineas — TODO

## Phase 1: Generic Core
- [x] DB schema: `assets` + `asset_snapshots` models (SQLAlchemy 2.0)
- [x] Async DB engine + session factory (`database.py`)
- [x] Python dependencies (`requirements.txt`)
- [ ] Pydantic schemas (request/response validation)
- [ ] FastAPI routers: CRUD for assets and snapshots
- [ ] Alembic migrations (generate from models)
- [ ] Docker Compose setup (PostgreSQL + API)

## Phase 2: The Math
- [ ] Deterministic projection engine (pure Python, no LLM)
- [ ] Soft-delete / `is_archived` flag on `assets` (auditability)
- [ ] FIRE target calculator (time-to-retirement given savings rate + return)

## Phase 3: Smart Ingestion
- [ ] LLM-powered parser: free-text / CSV → structured JSON
- [ ] Upsert endpoint using `ON CONFLICT (asset_id, snapshot_date) DO UPDATE`

## Phase 4: The Agent
- [ ] LangGraph state machine for portfolio update workflow
- [ ] Human-in-the-loop (HITL) confirmation step
- [ ] Frontend chat UI wired to agent

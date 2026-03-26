# CLAUDE.md — Fineas: An Agentic FIRE Copilot

## Project Vision
Fineas is an educational project exploring the implementation of **Agentic Workflows** within a personal finance context. It tracks assets, calculates FIRE (Financial Independence, Retire Early) trajectories, and uses LLMs to lower the friction of data entry.

## Educational Goals (The "Why")
1. **Agentic Patterns:** Implementing "Human-in-the-loop" (HITL) using LangGraph.
2. **Deterministic vs. Probabilistic:** Separation of pure math (Python) from reasoning (LLM).
3. **Structured Ingestion:** Using LLMs as a replacement for rigid CSV/Excel parsers.
4. **Full-Stack Async:** Mastering Python's `asyncio`, FastAPI, and Next.js Server Components.

## Core Tech Stack
- **Backend:** FastAPI (Async), SQLAlchemy 2.0, Alembic, PostgreSQL.
- **Orchestration:** LangGraph (State management for the AI agent).
- **Intelligence:** Multi-LLM via LangChain — Anthropic (Claude Sonnet), OpenRouter, Groq. Configurable via `LLM_PROVIDER` / `LLM_MODEL` env vars.
- **Frontend:** Next.js 14 (App Router), Tailwind CSS, Recharts, React Query.
- **Infrastructure:** Docker Compose, PostgreSQL 16.

## Repository Structure
```
fineas/
├── apps/
│   ├── backend/
│   │   ├── agent/           # LangGraph ingestion pipeline (Phase 3)
│   │   ├── alembic/         # DB migrations
│   │   ├── routers/         # FastAPI route modules
│   │   ├── tests/           # 130+ pytest tests
│   │   ├── main.py          # App entrypoint
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── projection.py    # Deterministic FIRE projection engine
│   │   ├── database.py      # Async engine + session factory
│   │   └── Dockerfile
│   └── frontend/            # Next.js 14 app (Phase 5)
├── data/                    # Seed data (CSV, Excel)
├── scripts/                 # Utility scripts (CSV import, DB init)
├── docker-compose.yml
├── CLAUDE.md
└── TODO.md
```

## Development Status (Iterative Phases)
- [x] **Phase 1: Generic Core** — DB schema, async CRUD routers, Alembic migrations, Docker Compose.
- [x] **Phase 2: The Math** — Deterministic projection engine, FIRE target calculator, soft-delete.
- [x] **Phase 3: Smart Ingestion** — LangGraph parse→validate pipeline, multi-LLM support, snapshot upsert endpoint.
- [ ] **Phase 4: The Agent** — LangGraph state machine for full portfolio update workflow + HITL.
- [ ] **Phase 5: Frontend** — Next.js dashboard, asset management, FIRE calculator, smart import UI.

## API Endpoints

### Assets (`/assets`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/assets` | Create asset (409 if name exists) |
| GET | `/assets` | List assets (`?include_archived=false`) |
| GET | `/assets/{asset_id}` | Get single asset |
| PATCH | `/assets/{asset_id}` | Partial update |
| DELETE | `/assets/{asset_id}` | Hard delete |

### Snapshots (`/assets/{asset_id}/snapshots`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/assets/{asset_id}/snapshots` | Create snapshot (409 on duplicate date) |
| GET | `/assets/{asset_id}/snapshots` | List snapshots (ordered by date asc) |
| POST | `/assets/{asset_id}/snapshots/upsert` | Idempotent upsert (`ON CONFLICT DO UPDATE`) |

### Portfolio (`/portfolio`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/portfolio/projection` | Run projection (`?months=120&monthly_contribution=0&annual_expenses=&safe_withdrawal_rate=0.04`) |

### Ingestion (`/ingest`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Parse free-text/CSV via LLM (parse-only, no DB writes) |

## Environment Variables
See `.env.example` for all options:
- `DATABASE_URL` — PostgreSQL connection string (asyncpg)
- `LLM_PROVIDER` — `anthropic` | `openrouter` | `groq` (default: `anthropic`)
- `LLM_MODEL` — Model override (blank = provider default)
- `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY` / `GROQ_API_KEY` — API keys
- `APP_ENV` — `development` | `production`
- `LOG_LEVEL` — `DEBUG` | `INFO` | `WARNING`
- `CORS_ORIGINS` — Allowed frontend origins

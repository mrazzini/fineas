# Fineas - An Agentic FIRE Copilot
[**LIVE DEMO**](https://3.69.248.127.nip.io/)

A full-stack personal finance tracker that calculates FIRE (Financial Independence, Retire Early) trajectories and uses LLMs to lower the friction of data entry.

Built as an educational project exploring **Agentic Workflows**: human-in-the-loop AI pipelines, deterministic math separated from LLM reasoning, and structured data ingestion via natural language.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (async), SQLAlchemy 2.0, Alembic, PostgreSQL 16 |
| **Orchestration** | LangGraph (state machine for AI agent pipeline) |
| **Intelligence** | Multi-LLM via LangChain: Anthropic, OpenRouter, Groq |
| **Frontend** | Next.js 14 (App Router), Tailwind CSS, Recharts, React Query |
| **Infrastructure** | Docker Compose, EC2 + Caddy (production) |

## Features

- **Asset Tracking** - CRUD for financial assets with type classification (stocks, bonds, cash, real estate, pension, crypto)
- **Snapshot History** - Time-series balance tracking with idempotent upsert
- **FIRE Projection** - Deterministic projection engine: compound growth, monthly contributions, time-to-retirement calculation
- **Smart Import** - Paste free-text or CSV, LLM parses it into structured asset snapshots (parse > validate > confirm)
- **Dashboard** - KPI cards, projection chart, allocation donut, net worth history
- **Multi-LLM** - Switch between Anthropic Claude, OpenRouter, or Groq with an env var

## Quick Start

```bash
# Clone and start all services
git clone https://github.com/Misterazzo/fineas.git
cd fineas
cp .env.example .env  # edit with your API keys

docker compose up --build
```

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

### Seed demo data

```bash
docker compose exec api python /app/../scripts/seed.py
# or from the host:
DATABASE_URL=postgresql+asyncpg://fineas:fineas@localhost:5432/fineas python scripts/seed.py
```

## API Endpoints

### Assets `/assets`
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/assets` | Create asset (409 if name exists) |
| `GET` | `/assets` | List assets (`?include_archived=false`) |
| `GET` | `/assets/{id}` | Get single asset |
| `PATCH` | `/assets/{id}` | Partial update |
| `DELETE` | `/assets/{id}` | Hard delete |

### Snapshots `/assets/{id}/snapshots`
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/assets/{id}/snapshots` | Create snapshot (409 on duplicate date) |
| `GET` | `/assets/{id}/snapshots` | List snapshots (ordered by date) |
| `POST` | `/assets/{id}/snapshots/upsert` | Idempotent upsert |

### Portfolio `/portfolio`
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/portfolio/projection` | FIRE projection (`?months=120&monthly_contribution=0&annual_expenses=&safe_withdrawal_rate=0.04`) |

### Ingestion `/ingest`
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest` | Parse free-text/CSV via LLM (parse-only, no DB writes) |

## Project Structure

```
fineas/
├── apps/
│   ├── backend/
│   │   ├── agent/           # LangGraph ingestion pipeline
│   │   ├── alembic/         # DB migrations
│   │   ├── routers/         # FastAPI route modules
│   │   ├── tests/           # 130+ pytest tests
│   │   ├── main.py          # App entrypoint
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── projection.py    # Deterministic FIRE projection engine
│   │   └── database.py      # Async engine + session factory
│   └── frontend/            # Next.js 14 app
│       └── app/
│           ├── page.tsx          # Dashboard
│           ├── assets/           # Asset management
│           ├── fire-calculator/  # FIRE scenario planner
│           └── import/           # Smart import UI
├── data/
│   ├── example_assets.csv       # Demo seed data (tracked)
│   └── example_snapshots.csv    # Demo seed data (tracked)
├── scripts/
│   └── seed.py              # DB seeder (reads example CSVs by default)
├── docker-compose.yml
└── .env.example
```

## Development Phases

- [x] **Phase 1 - Core API:** DB schema, async CRUD, Alembic migrations, Docker Compose
- [x] **Phase 2 - The Math:** Projection engine, FIRE calculator, soft-delete
- [x] **Phase 3 - Smart Ingestion:** LangGraph parse-validate pipeline, multi-LLM support
- [x] **Phase 5 - Frontend:** Next.js dashboard, asset management, FIRE calculator, smart import
- [ ] **Phase 4 - The Agent:** LangGraph state machine for full portfolio update workflow + HITL

## Environment Variables

See [`.env.example`](.env.example) for all options. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `LLM_PROVIDER` | `anthropic` \| `openrouter` \| `groq` |
| `LLM_MODEL` | Model override (blank = provider default) |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `CORS_ORIGINS` | Allowed frontend origins |

## License

MIT

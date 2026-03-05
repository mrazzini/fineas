# CLAUDE.md — Fineas: Your Agentic FIRE Copilot

> **"Fineas — your FIRE copilot."**

## What is Fineas?

Fineas is a personal financial copilot built around one question: **"When am I free?"**

The name: **Fin**ance + Ph**ineas**. Fineas is the AI agent persona — friendly, sharp, always watching your numbers. Users don't "use the app," they "ask Fineas."

It replaces a manually-maintained Excel spreadsheet with an agentic web app. The user opens it once a month, speaks in natural language to update their portfolio, and the system recalculates their FIRE trajectory in real time.

**Primary user (v1):** Milan-based professional tracking investments across Scalable Capital (ETFs, bonds), money market funds (Xtrackers, Lyxor SMART), P2P lending (Esketit, Estateguru), and a pension fund (Fonchim).

**This is NOT:** a budget tracker, robo-advisor, bank aggregator, or trading platform.

---

## Detailed Specs — Read Before Working on Each Area

All detailed specifications live in `docs/`. **Read the relevant file before starting work in that area.**

| File | Read when working on... |
|------|------------------------|
| `docs/DATA_MODEL.md` | Database schema, migrations, seed data, SQLAlchemy models |
| `docs/AGENTS.md` | Agent logic, LangGraph workflows, tools, orchestrator |
| `docs/PROJECTION_ENGINE.md` | FIRE math, Monte Carlo, compound growth, scenarios |
| `docs/API_CONTRACT.md` | REST endpoints, WebSocket protocol, shared TypeScript/Pydantic types |
| `docs/MIGRATION.md` | Excel → PostgreSQL one-time migration script |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14+ (App Router), Tailwind CSS + shadcn/ui, Recharts/Plotly |
| Backend | FastAPI (async), Pydantic v2, SQLAlchemy 2.0 (async), Alembic |
| Agents | LangGraph, Claude API (claude-sonnet-4-5-20250929) |
| Database | PostgreSQL 16 + pgvector |
| Deployment | Docker Compose (local) → AWS ECS Fargate + RDS (prod) |

---

## Repository Structure

```
fineas/
├── CLAUDE.md                    # THIS FILE
├── docs/                        # Detailed specs (read per-area)
│   ├── DATA_MODEL.md
│   ├── AGENTS.md
│   ├── PROJECTION_ENGINE.md
│   ├── API_CONTRACT.md
│   └── MIGRATION.md
├── docker-compose.yml
├── .env.example
├── packages/
│   └── shared/                  # Shared types and contracts
│       ├── schema.ts            # TypeScript types (derived from Pydantic)
│       └── constants.ts
├── apps/
│   ├── frontend/                # Next.js app
│   │   ├── app/
│   │   │   ├── page.tsx         # Dashboard (main view)
│   │   │   ├── chat/page.tsx    # Chat interface
│   │   │   └── projections/page.tsx
│   │   ├── components/
│   │   │   ├── dashboard/       # NetWorthChart, AllocationBreakdown, ProjectionCurve
│   │   │   ├── chat/            # ChatPanel, MessageBubble, ConfirmationCard
│   │   │   └── projections/     # FireTimeline, MonteCarloFan, ScenarioCompare
│   │   └── lib/
│   │       ├── api.ts
│   │       └── hooks/
│   └── api/                     # FastAPI app
│       ├── pyproject.toml
│       ├── alembic/
│       ├── app/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── models/          # SQLAlchemy ORM (asset, snapshot, goal, projection, conversation)
│       │   ├── schemas/         # Pydantic schemas
│       │   ├── routers/         # API routes
│       │   ├── agents/          # LangGraph agents (orchestrator, update, projection, monitor, ingestion)
│       │   ├── tools/           # Agent tools (portfolio, projection, goals, monitoring, ingestion)
│       │   └── services/        # Business logic (portfolio, projection, monitoring)
│       └── tests/
├── scripts/
│   ├── migrate_excel.py
│   └── seed_data.py
└── data/
    └── CA_HFLOW.xlsx            # Original Excel (reference only)
```

---

## Build Phases

| Phase | Ships | Key Pattern | Spec File |
|-------|-------|-------------|-----------|
| **0** | Data model + Excel migration + Next.js dashboard | Foundation | `DATA_MODEL.md`, `MIGRATION.md` |
| **1** | NL Update Agent via chat | Tool-use, ReAct, human-in-the-loop | `AGENTS.md` §5.2 |
| **2** | FIRE Projection Agent (Monte Carlo, scenarios, goals) | Computational reasoning, NL goals | `AGENTS.md` §5.3, `PROJECTION_ENGINE.md` |
| **3** | Monitoring Agent (drift, pace, milestones) | Autonomous agent, scheduled execution | `AGENTS.md` §5.4 |
| **4** | Document Ingestion Agent (CSV/PDF/screenshots) | Multimodal, batch operations | `AGENTS.md` §5.5 |

**Current focus: Phase 0 → Phase 1 (MVP)**

---

## Development Conventions

### Backend (FastAPI / Python 3.12+)
- Async everywhere — async SQLAlchemy, async httpx for Claude API
- Pydantic v2 for all schemas; Alembic for all migrations
- Environment config via `pydantic-settings`
- Structured JSON logging via `structlog`
- Custom exception classes with global FastAPI handler

### Frontend (Next.js)
- App Router — Server Components by default, Client Components only for interactive elements
- Data fetching: Server Components call API; Client Components use `useSWR` or `react-query`
- Tailwind CSS + shadcn/ui only — no custom CSS files
- Recharts for charts; Plotly only if Monte Carlo fan charts demand it

### Agents (LangGraph)
- Each agent = one `StateGraph` in its own file under `app/agents/`
- Tools = plain functions with `@tool` decorator in `app/tools/`, grouped by domain
- System prompts include full asset list + current portfolio (fetched fresh per conversation)
- **Human-in-the-loop is non-negotiable** — no DB writes without user confirmation
- Log every tool call and result for debugging
- Agent prompts live in code, versioned with the agent

### Database
- UUIDs for all PKs (`gen_random_uuid()`)
- All timestamps `TIMESTAMPTZ`
- Soft deletes via `is_active` where applicable
- JSONB for flexible schemas (projection params, metadata)
- Composite indexes on query hot paths (`(asset_id, date)` on snapshots)

### General
- Type everything — no `Any`, no `unknown` in hot paths
- Test agent tools independently with unit tests against test DB
- Streaming responses via WebSocket — don't buffer full agent responses

---

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://fineas:fineas@localhost:5432/fineas
ANTHROPIC_API_KEY=sk-ant-...
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
DEFAULT_INFLATION_RATE=0.02
DEFAULT_MONTE_CARLO_SIMULATIONS=10000
DEFAULT_MONTHLY_CONTRIBUTION=750
```

---

## Open Questions (decide before building)

1. **Fonchim:** Is it part of monthly snapshot flow or a separate annual update? (Not liquid until retirement/home purchase under Italian law)
2. **Authentication:** v1 is single-user, no auth. Add NextAuth.js for multi-user later.
3. **P2P sunset:** Robocash is at €0. Mark inactive and exclude from projections. Handle "I closed my account" in Update Agent.
4. **Currency:** EUR only for v1.
5. **Data export:** Should the app export back to Excel for backup?
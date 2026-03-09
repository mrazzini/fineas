# CLAUDE.md — Fineas: An Agentic FIRE Copilot

## Project Vision
Fineas is an educational project exploring the implementation of **Agentic Workflows** within a personal finance context. It tracks assets, calculates FIRE (Financial Independence, Retire Early) trajectories, and uses LLMs to lower the friction of data entry.

## Educational Goals (The "Why")
1. **Agentic Patterns:** Implementing "Human-in-the-loop" (HITL) using LangGraph.
2. **Deterministic vs. Probabilistic:** Separation of pure math (Python) from reasoning (LLM).
3. **Structured Ingestion:** Using LLMs as a replacement for rigid CSV/Excel parsers.
4. **Full-Stack Async:** Mastering Python's `asyncio`, FastAPI, and Next.js Server Components.

## Core Tech Stack
- **Backend:** FastAPI (Async), SQLAlchemy 2.0, PostgreSQL.
- **Orchestration:** LangGraph (State management for the AI agent).
- **Intelligence:** Claude 3.5 Sonnet (Parsing & Reasoning).
- **Frontend:** Next.js 14 (App Router), Tailwind CSS, Recharts.

## Development Status (Iterative Phases)
- [ ] **Phase 1: Generic Core** (Clean DB Schema + Manual CRUD)
- [ ] **Phase 2: The Math** (Deterministic Projection Engine)
- [ ] **Phase 3: Smart Ingestion** (LLM-powered text-to-JSON parsing)
- [ ] **Phase 4: The Agent** (LangGraph state machine for portfolio updates)
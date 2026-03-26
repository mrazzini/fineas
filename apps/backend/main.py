"""
FastAPI application entrypoint.

The lifespan context manager handles startup/shutdown.
We do NOT call create_all here — Alembic handles schema migrations.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from routers import assets, ingest, portfolio, snapshots


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Fineas API",
    description="FIRE Copilot — asset tracking and projection API",
    version="0.1.0",
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router)
app.include_router(snapshots.router)
app.include_router(portfolio.router)
app.include_router(ingest.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
"""
FastAPI application entrypoint.

The lifespan context manager handles startup/shutdown.
We do NOT call create_all here — Alembic handles schema migrations.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine
from routers import assets, portfolio, snapshots


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

app.include_router(assets.router)
app.include_router(snapshots.router)
app.include_router(portfolio.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
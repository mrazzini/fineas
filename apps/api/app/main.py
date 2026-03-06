import asyncio
from contextlib import asynccontextmanager
from functools import partial

import structlog
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine
from app.routers import assets, chat, goals, projections, snapshots

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations in a thread so Alembic's asyncio.run() can create its own
    # event loop — calling asyncio.run() inside uvicorn's already-running loop crashes.
    alembic_cfg = Config("/app/alembic.ini")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(command.upgrade, alembic_cfg, "head"))
    log.info("startup", env=settings.APP_ENV)
    yield
    await engine.dispose()
    log.info("shutdown")


app = FastAPI(
    title="Fineas API",
    description="FIRE copilot backend — natural language portfolio management",
    version="0.1.0",
    lifespan=lifespan,
)

cors_origins = ["*"] if settings.APP_ENV != "production" else settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,  # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(snapshots.router, prefix="/api/snapshots", tags=["snapshots"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(projections.router, prefix="/api/projections", tags=["projections"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}

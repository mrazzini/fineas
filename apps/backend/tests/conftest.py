"""
Async test fixtures for Fineas.

Isolation strategy:
  - `test_engine` (session-scoped): creates all tables once for the test session,
    drops them on teardown.  Uses NullPool to avoid asyncpg cross-task issues.
  - `client` (function-scoped): httpx.AsyncClient wired to the FastAPI app with
    `get_db` overridden to inject a test session factory.  Each request gets its
    own session (avoiding asyncpg's Task-identity check).  All data is deleted
    between tests for isolation.

Why not transaction rollback?
  httpx.ASGITransport spawns a new asyncio Task for the ASGI app.  asyncpg
  binds connections to the Task that created them, so sharing a single
  connection across fixtures and ASGI handlers triggers RuntimeError.
  Per-request sessions with table cleanup avoids this entirely.
"""
import os

# Test auth secrets — must be set BEFORE importing config / auth.
TEST_PASSWORD = "test-password"
os.environ.setdefault("FINEAS_SESSION_SECRET", "test-session-secret-not-for-production")
os.environ.setdefault("FINEAS_OWNER_PASSWORD", TEST_PASSWORD)

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import config  # noqa: F401 — trigger env read
from database import get_db
from main import app
from models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://fineas:fineas@localhost:5432/fineas_test"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    """Create the test schema once per pytest session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def anon_client(test_engine):
    """Anonymous httpx.AsyncClient — no session cookie."""
    TestingSession = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False,
    )

    async def override_get_db():
        async with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

    # Clean up: delete all data after each test for isolation
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture(loop_scope="session")
async def client(anon_client):
    """Default client is authenticated as the owner.

    Most existing tests exercise write endpoints; after the auth layer was
    added those all require a valid session cookie. Logging in once at the
    top of the fixture keeps the existing test suite working while making
    the auth layer itself exercisable via `anon_client`.
    """
    res = await anon_client.post("/auth/login", json={"password": TEST_PASSWORD})
    assert res.status_code == 200, f"test login failed: {res.text}"
    yield anon_client

"""
Async test fixtures for Fineas.

Isolation strategy:
  - `test_engine` (session-scoped): creates all tables once for the test session,
    drops them on teardown.
  - `db_session` (function-scoped): each test runs inside a transaction that is
    rolled back after the test completes — zero DB state leaks between tests.
  - `client` (function-scoped): httpx.AsyncClient wired to the FastAPI app with
    `get_db` overridden to inject the test session.

Why transaction rollback instead of table truncation?
  Rollback is ~10x faster than TRUNCATE and guarantees the DB returns to the
  exact same state, including sequence counters and constraints.
"""
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from database import get_db
from main import app
from models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://fineas:fineas@localhost:5432/fineas_test"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    """Create the test schema once per pytest session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Each test gets a fresh transaction that is rolled back on completion.
    Uses SQLAlchemy's 'join external transaction' pattern.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """httpx.AsyncClient with the FastAPI app and test DB injected."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
"""
Async database engine and session factory for Fineas.

Uses SQLAlchemy 2.0's async extension with asyncpg as the PostgreSQL driver.
The session is provided as a FastAPI dependency via get_db().
"""
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://fineas:fineas@localhost:5432/fineas",
)

# echo=False in production; set to True locally to log all SQL statements.
engine = create_async_engine(DATABASE_URL, echo=False)

# expire_on_commit=False keeps loaded objects accessible after commit —
# important in async contexts where lazy loading is not available.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a database session and closes it on exit."""
    async with AsyncSessionLocal() as session:
        yield session

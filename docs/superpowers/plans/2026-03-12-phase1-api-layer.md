# Phase 1 API Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full HTTP API surface for Phase 1 — Pydantic schemas, FastAPI CRUD routers, test infrastructure, Alembic migrations, and Docker Compose.

**Architecture:** Thin routers (no business logic) delegate to SQLAlchemy sessions; Pydantic schemas act as the strict contract layer between HTTP and the ORM. Tests run against a real PostgreSQL test database using per-test transaction rollback for isolation.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.0 async, pytest-asyncio, httpx, Alembic, Docker Compose.

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `apps/backend/models.py` | ✅ exists | ORM models |
| `apps/backend/database.py` | ✅ exists | Async engine + `get_db()` |
| `apps/backend/requirements.txt` | ✅ exists | Production dependencies |
| `apps/backend/requirements-dev.txt` | CREATE | Test/dev dependencies |
| `apps/backend/schemas.py` | CREATE | Pydantic request/response contracts |
| `apps/backend/main.py` | CREATE | FastAPI app entrypoint + lifespan |
| `apps/backend/routers/__init__.py` | CREATE | Package marker |
| `apps/backend/routers/deps.py` | CREATE | Shared router dependencies (e.g. `_get_asset_or_404`) |
| `apps/backend/routers/assets.py` | CREATE | CRUD endpoints for assets |
| `apps/backend/routers/snapshots.py` | CREATE | CRUD endpoints for snapshots (nested under assets) |
| `apps/backend/tests/__init__.py` | CREATE | Package marker |
| `apps/backend/tests/conftest.py` | CREATE | Async fixtures: test engine, session, httpx client |
| `apps/backend/tests/pytest.ini` | CREATE | asyncio_mode = auto |
| `apps/backend/tests/test_assets.py` | CREATE | Integration tests for asset endpoints |
| `apps/backend/tests/test_snapshots.py` | CREATE | Integration tests for snapshot endpoints |
| `apps/backend/alembic.ini` | CREATE | Alembic config (script_location = alembic/) |
| `apps/backend/alembic/env.py` | CREATE | Async Alembic environment |
| `apps/backend/alembic/versions/` | CREATE (dir) | Migration files (auto-generated) |
| `docker-compose.yml` | CREATE | PostgreSQL service (primary + test DB) |

---

## Chunk 1: Schemas + Test Infrastructure

### Task 1: Dev requirements + pytest config

**Files:**
- Create: `apps/backend/requirements-dev.txt`
- Create: `apps/backend/pytest.ini`

- [x] **Step 1.1: Create dev requirements**

```
# apps/backend/requirements-dev.txt
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.1
```

- [x] **Step 1.2: Install dev requirements**

```bash
cd /workspaces/fineas/apps/backend
pip install -r requirements.txt -r requirements-dev.txt -q
```
Expected: no errors.

- [x] **Step 1.3: Create pytest.ini**

```ini
# apps/backend/pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
testpaths = tests
```
`asyncio_mode = auto` means every `async def test_*` function is automatically treated as an async test — no `@pytest.mark.asyncio` decorator needed on each test. `asyncio_default_fixture_loop_scope = session` is required by pytest-asyncio 0.24+ to tell it all async fixtures share one event loop — without it, the session-scoped `test_engine` fixture and function-scoped fixtures run in different loops, causing `RuntimeError: Task attached to different loop`.

- [x] **Step 1.4: Verify pytest discovers tests (zero tests is fine)**

```bash
cd /workspaces/fineas/apps/backend && pytest --collect-only -q
```
Expected: `no tests ran` or `0 items`.

- [x] **Step 1.5: Commit**
```bash
git add apps/backend/requirements-dev.txt apps/backend/pytest.ini
git commit -m "test: add dev requirements and pytest config"
```

---

### Task 2: Pydantic schemas

**Files:**
- Create: `apps/backend/schemas.py`

- [ ] **Step 2.1: Write the schemas**

```python
# apps/backend/schemas.py
"""
Pydantic v2 schemas — the HTTP contract layer between FastAPI and the ORM.

Three schema families:
  - AssetCreate / AssetUpdate / AssetRead
  - SnapshotCreate / SnapshotRead

The *Read schemas use `model_config = ConfigDict(from_attributes=True)` which
tells Pydantic to read values from ORM object attributes (not just dicts).
This is the Pydantic v2 replacement for orm_mode = True.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from models import AssetType


class AssetCreate(BaseModel):
    name: str
    asset_type: AssetType
    annualized_return_pct: Optional[Decimal] = None
    ticker: Optional[str] = None


class AssetUpdate(BaseModel):
    """All fields optional — supports partial PATCH updates."""
    name: Optional[str] = None
    asset_type: Optional[AssetType] = None
    annualized_return_pct: Optional[Decimal] = None
    ticker: Optional[str] = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    asset_type: AssetType
    annualized_return_pct: Optional[Decimal] = None
    ticker: Optional[str] = None
    created_at: datetime


class SnapshotCreate(BaseModel):
    snapshot_date: date
    balance: Decimal


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    snapshot_date: date
    balance: Decimal
    created_at: datetime
```

- [ ] **Step 2.2: Verify schemas import cleanly**

```bash
cd /workspaces/fineas/apps/backend && python -c "from schemas import AssetCreate, AssetRead, SnapshotCreate, SnapshotRead; print('OK')"
```
Expected: `OK`

- [ ] **Step 2.3: Commit**
```bash
git add apps/backend/schemas.py
git commit -m "feat: add Pydantic v2 request/response schemas"
```

---

### Task 3: Test conftest (async fixtures)

**Files:**
- Create: `apps/backend/tests/__init__.py`
- Create: `apps/backend/tests/conftest.py`

- [ ] **Step 3.1: Create package marker**

```python
# apps/backend/tests/__init__.py
```
(empty file)

- [ ] **Step 3.2: Create conftest.py**

```python
# apps/backend/tests/conftest.py
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
```

- [ ] **Step 3.3: Commit**
```bash
git add apps/backend/tests/__init__.py apps/backend/tests/conftest.py
git commit -m "test: add async conftest with transaction-rollback isolation"
```

---

## Chunk 2: FastAPI App + Assets Router + Tests

### Task 4: FastAPI app entrypoint

**Files:**
- Create: `apps/backend/main.py`

- [ ] **Step 4.1: Write main.py**

```python
# apps/backend/main.py
"""
FastAPI application entrypoint.

The lifespan context manager handles startup/shutdown.
We do NOT call create_all here — Alembic handles schema migrations.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine
from routers import assets, snapshots


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


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4.2: Create routers package and shared deps**

```python
# apps/backend/routers/__init__.py
```
(empty file)

```python
# apps/backend/routers/deps.py
"""Shared FastAPI dependencies used by multiple routers."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Asset


async def get_asset_or_404(asset_id: uuid.UUID, db: AsyncSession) -> Asset:
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset
```

- [ ] **Step 4.3: Verify app imports cleanly**
```bash
cd /workspaces/fineas/apps/backend && python -c "from main import app; print('App OK:', app.title)"
```
Expected: `App OK: Fineas API`

---

### Task 5: Write failing tests for Assets router

**Files:**
- Create: `apps/backend/tests/test_assets.py`

*Write all tests first — they will all fail until the router is implemented in Task 6.*

- [ ] **Step 5.1: Write test_assets.py**

```python
# apps/backend/tests/test_assets.py
"""
Integration tests for /assets endpoints.
Each test runs in its own rolled-back transaction via the `client` fixture.
No @pytest.mark.asyncio needed — asyncio_mode = auto in pytest.ini covers all async tests.
"""
from httpx import AsyncClient


async def test_create_asset(client: AsyncClient):
    response = await client.post("/assets", json={
        "name": "Vanguard FTSE All-World",
        "asset_type": "STOCKS",
        "annualized_return_pct": "0.0850",
        "ticker": "VWCE.DE",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Vanguard FTSE All-World"
    assert data["asset_type"] == "STOCKS"
    assert data["ticker"] == "VWCE.DE"
    assert "id" in data
    assert "created_at" in data


async def test_create_asset_minimal(client: AsyncClient):
    """Only required fields — optional fields default to None."""
    response = await client.post("/assets", json={
        "name": "Emergency Fund",
        "asset_type": "CASH",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["annualized_return_pct"] is None
    assert data["ticker"] is None


async def test_create_asset_duplicate_name_fails(client: AsyncClient):
    """The UNIQUE constraint on name must be enforced at the API layer."""
    payload = {"name": "iShares MSCI EM", "asset_type": "STOCKS"}
    await client.post("/assets", json=payload)
    response = await client.post("/assets", json=payload)
    assert response.status_code == 409


async def test_list_assets(client: AsyncClient):
    await client.post("/assets", json={"name": "Asset A", "asset_type": "CASH"})
    await client.post("/assets", json={"name": "Asset B", "asset_type": "BONDS"})
    response = await client.get("/assets")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_asset(client: AsyncClient):
    create = await client.post("/assets", json={"name": "Pension", "asset_type": "PENSION_FUND"})
    asset_id = create.json()["id"]
    response = await client.get(f"/assets/{asset_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Pension"


async def test_get_asset_not_found(client: AsyncClient):
    response = await client.get("/assets/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_update_asset(client: AsyncClient):
    create = await client.post("/assets", json={"name": "Old Name", "asset_type": "CASH"})
    asset_id = create.json()["id"]
    response = await client.patch(f"/assets/{asset_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    # asset_type unchanged
    assert response.json()["asset_type"] == "CASH"


async def test_delete_asset(client: AsyncClient):
    create = await client.post("/assets", json={"name": "To Delete", "asset_type": "CRYPTO"})
    asset_id = create.json()["id"]
    delete = await client.delete(f"/assets/{asset_id}")
    assert delete.status_code == 204
    get = await client.get(f"/assets/{asset_id}")
    assert get.status_code == 404
```

- [ ] **Step 5.2: Run tests — expect ALL to fail**

```bash
cd /workspaces/fineas/apps/backend && pytest tests/test_assets.py -v
```
Expected: all fail with `ImportError` or `404` — routers don't exist yet.

---

### Task 6: Implement Assets router

**Files:**
- Create: `apps/backend/routers/assets.py`

- [ ] **Step 6.1: Write the assets router**

```python
# apps/backend/routers/assets.py
"""
CRUD endpoints for the Asset resource.

Route summary:
  POST   /assets            → 201 AssetRead
  GET    /assets            → 200 list[AssetRead]
  GET    /assets/{id}       → 200 AssetRead  | 404
  PATCH  /assets/{id}       → 200 AssetRead  | 404
  DELETE /assets/{id}       → 204            | 404
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Asset
from routers.deps import get_asset_or_404
from schemas import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(payload: AssetCreate, db: AsyncSession = Depends(get_db)):
    asset = Asset(**payload.model_dump())
    db.add(asset)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset with that name already exists.",
        )
    await db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetRead])
async def list_assets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).order_by(Asset.created_at))
    return result.scalars().all()


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_asset_or_404(asset_id, db)


@router.patch("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: uuid.UUID, payload: AssetUpdate, db: AsyncSession = Depends(get_db)
):
    asset = await get_asset_or_404(asset_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    asset = await get_asset_or_404(asset_id, db)
    await db.delete(asset)
    await db.commit()
```

- [ ] **Step 6.2: Run tests — expect ALL to pass**

```bash
cd /workspaces/fineas/apps/backend && pytest tests/test_assets.py -v
```
Expected: `8 passed`.

- [ ] **Step 6.3: Commit**
```bash
git add apps/backend/main.py apps/backend/routers/__init__.py apps/backend/routers/assets.py apps/backend/tests/test_assets.py
git commit -m "feat: assets CRUD router with integration tests"
```

---

## Chunk 3: Snapshots Router + Alembic + Docker Compose

### Task 7: Write failing tests for Snapshots router

**Files:**
- Create: `apps/backend/tests/test_snapshots.py`

- [ ] **Step 7.1: Write test_snapshots.py**

```python
# apps/backend/tests/test_snapshots.py
"""
Integration tests for /assets/{id}/snapshots endpoints.
No @pytest.mark.asyncio needed — asyncio_mode = auto in pytest.ini covers all async tests.
"""
from httpx import AsyncClient


async def _make_asset(client: AsyncClient, name: str = "Test Asset") -> str:
    """Helper: create an asset and return its id."""
    r = await client.post("/assets", json={"name": name, "asset_type": "STOCKS"})
    return r.json()["id"]


async def test_create_snapshot(client: AsyncClient):
    asset_id = await _make_asset(client)
    response = await client.post(f"/assets/{asset_id}/snapshots", json={
        "snapshot_date": "2025-12-31",
        "balance": "12345.67",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["asset_id"] == asset_id
    assert data["snapshot_date"] == "2025-12-31"
    assert float(data["balance"]) == 12345.67


async def test_create_snapshot_asset_not_found(client: AsyncClient):
    response = await client.post(
        "/assets/00000000-0000-0000-0000-000000000000/snapshots",
        json={"snapshot_date": "2025-01-01", "balance": "1000.00"},
    )
    assert response.status_code == 404


async def test_duplicate_snapshot_date_fails(client: AsyncClient):
    """UNIQUE(asset_id, snapshot_date) must be enforced."""
    asset_id = await _make_asset(client, "Unique Date Test")
    payload = {"snapshot_date": "2025-06-15", "balance": "500.00"}
    await client.post(f"/assets/{asset_id}/snapshots", json=payload)
    response = await client.post(f"/assets/{asset_id}/snapshots", json=payload)
    assert response.status_code == 409


async def test_list_snapshots(client: AsyncClient):
    asset_id = await _make_asset(client, "Historical Asset")
    await client.post(f"/assets/{asset_id}/snapshots", json={"snapshot_date": "2025-01-31", "balance": "1000"})
    await client.post(f"/assets/{asset_id}/snapshots", json={"snapshot_date": "2025-02-28", "balance": "1100"})
    response = await client.get(f"/assets/{asset_id}/snapshots")
    assert response.status_code == 200
    snapshots = response.json()
    assert len(snapshots) == 2
    # Should be ordered by date ascending
    assert snapshots[0]["snapshot_date"] < snapshots[1]["snapshot_date"]


async def test_list_snapshots_asset_not_found(client: AsyncClient):
    response = await client.get("/assets/00000000-0000-0000-0000-000000000000/snapshots")
    assert response.status_code == 404
```

- [ ] **Step 7.2: Run tests — expect ALL to fail**

```bash
cd /workspaces/fineas/apps/backend && pytest tests/test_snapshots.py -v
```
Expected: all fail.

---

### Task 8: Implement Snapshots router

**Files:**
- Create: `apps/backend/routers/snapshots.py`

- [ ] **Step 8.1: Write the snapshots router**

```python
# apps/backend/routers/snapshots.py
"""
CRUD endpoints for AssetSnapshot, nested under /assets/{asset_id}.

Route summary:
  POST  /assets/{id}/snapshots  → 201 SnapshotRead | 404 | 409
  GET   /assets/{id}/snapshots  → 200 list[SnapshotRead] | 404
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AssetSnapshot
from routers.deps import get_asset_or_404
from schemas import SnapshotCreate, SnapshotRead

router = APIRouter(prefix="/assets/{asset_id}/snapshots", tags=["snapshots"])


@router.post("", response_model=SnapshotRead, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    asset_id: uuid.UUID,
    payload: SnapshotCreate,
    db: AsyncSession = Depends(get_db),
):
    await get_asset_or_404(asset_id, db)
    snapshot = AssetSnapshot(asset_id=asset_id, **payload.model_dump())
    db.add(snapshot)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A snapshot for this asset on that date already exists.",
        )
    await db.refresh(snapshot)
    return snapshot


@router.get("", response_model=list[SnapshotRead])
async def list_snapshots(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await get_asset_or_404(asset_id, db)
    result = await db.execute(
        select(AssetSnapshot)
        .where(AssetSnapshot.asset_id == asset_id)
        .order_by(AssetSnapshot.snapshot_date)
    )
    return result.scalars().all()
```

- [ ] **Step 8.2: Run all tests — expect ALL to pass**

```bash
cd /workspaces/fineas/apps/backend && pytest -v
```
Expected: `13 passed`.

- [ ] **Step 8.3: Commit**
```bash
git add apps/backend/routers/snapshots.py apps/backend/tests/test_snapshots.py
git commit -m "feat: snapshots CRUD router with integration tests"
```

---

### Task 9: Alembic migrations

**Files:**
- Create: `apps/backend/alembic.ini`
- Create: `apps/backend/alembic/env.py`
- Create (dir): `apps/backend/alembic/versions/`

- [ ] **Step 9.1: Install alembic**
```bash
pip install alembic -q
```

- [ ] **Step 9.2: Initialise Alembic in async mode**
```bash
cd /workspaces/fineas/apps/backend && alembic init -t async alembic
```
Expected: creates `alembic.ini` and `alembic/` directory.

- [ ] **Step 9.3: Update alembic/env.py for async + our models**

Replace the generated `alembic/env.py` with:

```python
# apps/backend/alembic/env.py
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our models so it can detect schema changes (autogenerate).
target_metadata = Base.metadata

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://fineas:fineas@localhost:5432/fineas",
)


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 9.4: Autogenerate the first migration**
```bash
cd /workspaces/fineas/apps/backend && alembic revision --autogenerate -m "create assets and asset_snapshots"
```
Expected: a new file in `alembic/versions/` with `op.create_table("assets", ...)` and `op.create_table("asset_snapshots", ...)`.

- [ ] **Step 9.5: Inspect the generated migration**

Open the generated file in `alembic/versions/`. Verify it contains:
- `op.create_table("assets", ...)` with all columns
- `op.create_table("asset_snapshots", ...)` with FK + UNIQUE constraint
- `op.create_index(...)` for `uq_snapshot_asset_date`

- [ ] **Step 9.6: Commit**
```bash
git add apps/backend/alembic.ini apps/backend/alembic/
git commit -m "feat: Alembic async config + initial migration for assets and snapshots"
```

---

### Task 10: Docker Compose

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 10.1: Write docker-compose.yml**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: fineas
      POSTGRES_PASSWORD: fineas
      POSTGRES_DB: fineas
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      # Creates the test DB automatically on first start.
      - ./scripts/init-test-db.sql:/docker-entrypoint-initdb.d/init-test-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fineas"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: apps/backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://fineas:fineas@db:5432/fineas
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 10.2: Write the test DB init script**
```bash
mkdir -p /workspaces/fineas/scripts
```

```sql
-- scripts/init-test-db.sql
-- Runs on first postgres container start, creates the test database.
CREATE DATABASE fineas_test;
```

- [ ] **Step 10.3: Write Dockerfile for the API**

```dockerfile
# apps/backend/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 10.4: Commit**
```bash
git add docker-compose.yml scripts/init-test-db.sql apps/backend/Dockerfile
git commit -m "feat: Docker Compose with Postgres service and test DB init"
```

---

## Final Verification Checklist

After all tasks are complete:

- [ ] `pytest -v` from `apps/backend/` → **13 passed, 0 failed**
- [ ] `docker compose up -d db` starts postgres
- [ ] `cd apps/backend && DATABASE_URL=postgresql+asyncpg://fineas:fineas@localhost:5432/fineas alembic upgrade head` runs without error
- [ ] `uvicorn main:app --reload` starts the API
- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] `curl http://localhost:8000/docs` → Swagger UI loads
- [ ] Update `TODO.md` to check off completed Phase 1 items

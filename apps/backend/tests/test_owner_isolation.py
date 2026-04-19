"""Demo-vs-real owner scoping on read endpoints."""
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models import Asset, AssetSnapshot, AssetType
from tests.conftest import TEST_PASSWORD


async def _seed(test_engine, **assets):
    """Insert one asset per kwarg: name=owner ('demo' or 'real')."""
    Session = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        for name, owner in assets.items():
            session.add(
                Asset(name=name, owner=owner, asset_type=AssetType.CASH)
            )
        await session.commit()


@pytest.mark.asyncio
async def test_anonymous_sees_only_demo(anon_client, test_engine):
    await _seed(test_engine, DemoCash="demo", RealCash="real")
    res = await anon_client.get("/assets")
    names = {a["name"] for a in res.json()}
    assert names == {"DemoCash"}


@pytest.mark.asyncio
async def test_authed_sees_only_real(anon_client, test_engine):
    await _seed(test_engine, DemoCash="demo", RealCash="real")
    await anon_client.post("/auth/login", json={"password": TEST_PASSWORD})
    res = await anon_client.get("/assets")
    names = {a["name"] for a in res.json()}
    assert names == {"RealCash"}


@pytest.mark.asyncio
async def test_cross_scope_get_returns_404(anon_client, test_engine):
    Session = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        real = Asset(name="RealOnly", owner="real", asset_type=AssetType.CASH)
        session.add(real)
        await session.commit()
        real_id = str(real.id)

    # Anonymous caller asking for a real-owned id should get 404.
    res = await anon_client.get(f"/assets/{real_id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_write_requires_auth(anon_client):
    res = await anon_client.post(
        "/assets",
        json={"name": "NoAuth", "asset_type": "CASH"},
    )
    assert res.status_code == 401

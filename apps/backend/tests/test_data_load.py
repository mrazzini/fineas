"""/data/load endpoint — CSV upload, auth-gated, owner='real'."""
import pytest

from tests.conftest import TEST_PASSWORD

ASSETS_CSV = (
    "name,asset_type,annualized_return_pct\n"
    "RealStocks,STOCKS,0.085\n"
    "RealCash,CASH,0.02\n"
)
SNAPSHOTS_CSV = (
    "asset_name,snapshot_date,balance\n"
    "RealStocks,15/01/2026,10000.00\n"
    "RealCash,15/01/2026,5000.00\n"
)


@pytest.mark.asyncio
async def test_load_requires_auth(anon_client):
    files = {
        "assets": ("assets.csv", ASSETS_CSV, "text/csv"),
        "snapshots": ("snapshots.csv", SNAPSHOTS_CSV, "text/csv"),
    }
    res = await anon_client.post("/data/load", files=files)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_load_success(client):
    files = {
        "assets": ("assets.csv", ASSETS_CSV, "text/csv"),
        "snapshots": ("snapshots.csv", SNAPSHOTS_CSV, "text/csv"),
    }
    res = await client.post("/data/load", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["assets_loaded"] == 2
    assert body["snapshots_loaded"] == 2
    assert body["skipped"] == []

    # And the loaded rows show up for the authed caller.
    assets = (await client.get("/assets")).json()
    assert {a["name"] for a in assets} == {"RealStocks", "RealCash"}


@pytest.mark.asyncio
async def test_load_rejects_bad_csv(client):
    files = {
        "assets": ("assets.csv", "name,asset_type\nBroken,NOT_A_TYPE\n", "text/csv"),
        "snapshots": ("snapshots.csv", SNAPSHOTS_CSV, "text/csv"),
    }
    res = await client.post("/data/load", files=files)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_load_skips_unknown_snapshot_asset(client):
    snapshots = (
        "asset_name,snapshot_date,balance\n"
        "UnknownAsset,15/01/2026,100.00\n"
    )
    files = {
        "assets": ("assets.csv", ASSETS_CSV, "text/csv"),
        "snapshots": ("snapshots.csv", snapshots, "text/csv"),
    }
    res = await client.post("/data/load", files=files)
    assert res.status_code == 200
    assert res.json()["snapshots_loaded"] == 0
    assert len(res.json()["skipped"]) == 1

"""/data/load endpoint — JSON payload (UI-mapped), auth-gated, owner='real'."""
import pytest

ASSETS_PAYLOAD = [
    {
        "original_name": "RealStocks",
        "name": "RealStocks",
        "asset_type": "STOCKS",
        "annualized_return_pct": "0.085",
    },
    {
        "original_name": "RealCash",
        "name": "RealCash",
        "asset_type": "CASH",
        "annualized_return_pct": "0.02",
    },
]
SNAPSHOTS_PAYLOAD = [
    {"asset_name": "RealStocks", "snapshot_date": "15/01/2026", "balance": "10000.00"},
    {"asset_name": "RealCash", "snapshot_date": "15/01/2026", "balance": "5000.00"},
]


@pytest.mark.asyncio
async def test_load_requires_auth(anon_client):
    res = await anon_client.post(
        "/data/load",
        json={"assets": ASSETS_PAYLOAD, "snapshots": SNAPSHOTS_PAYLOAD},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_load_success(client):
    res = await client.post(
        "/data/load",
        json={"assets": ASSETS_PAYLOAD, "snapshots": SNAPSHOTS_PAYLOAD},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["assets_loaded"] == 2
    assert body["snapshots_loaded"] == 2
    assert body["skipped"] == []

    assets = (await client.get("/assets")).json()
    assert {a["name"] for a in assets} == {"RealStocks", "RealCash"}


@pytest.mark.asyncio
async def test_load_rejects_invalid_asset_type(client):
    bad = [{**ASSETS_PAYLOAD[0], "asset_type": "NOT_A_TYPE"}]
    res = await client.post("/data/load", json={"assets": bad, "snapshots": []})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_load_skips_unknown_snapshot_asset(client):
    snapshots = [
        {"asset_name": "UnknownAsset", "snapshot_date": "15/01/2026", "balance": "100.00"}
    ]
    res = await client.post(
        "/data/load", json={"assets": ASSETS_PAYLOAD, "snapshots": snapshots}
    )
    assert res.status_code == 200
    assert res.json()["snapshots_loaded"] == 0
    assert len(res.json()["skipped"]) == 1


@pytest.mark.asyncio
async def test_load_rewrites_asset_name_when_renamed(client):
    """User edits an asset name in the UI — snapshots keyed on original_name
    still land against the renamed asset."""
    assets = [
        {
            "original_name": "Cash",
            "name": "isyBank Liquidity",
            "asset_type": "CASH",
            "annualized_return_pct": "0.03",
        }
    ]
    snapshots = [
        {"asset_name": "Cash", "snapshot_date": "15/01/2026", "balance": "500.00"}
    ]
    res = await client.post("/data/load", json={"assets": assets, "snapshots": snapshots})
    assert res.status_code == 200
    assert res.json()["snapshots_loaded"] == 1
    assert res.json()["skipped"] == []
    assets_list = (await client.get("/assets")).json()
    assert {a["name"] for a in assets_list} == {"isyBank Liquidity"}

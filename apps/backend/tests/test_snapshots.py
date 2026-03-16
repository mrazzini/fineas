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

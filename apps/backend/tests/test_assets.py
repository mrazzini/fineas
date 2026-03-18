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
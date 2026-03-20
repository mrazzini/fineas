"""
Integration tests for GET /portfolio/projection.

Uses the standard `client` fixture (per-test DB isolation via table cleanup).
"""
from decimal import Decimal

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_asset(
    client: AsyncClient,
    name: str = "Test Asset",
    asset_type: str = "STOCKS",
    annualized_return_pct: str = "0.08",
) -> str:
    r = await client.post(
        "/assets",
        json={
            "name": name,
            "asset_type": asset_type,
            "annualized_return_pct": annualized_return_pct,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _add_snapshot(client: AsyncClient, asset_id: str, balance: str, snapshot_date: str = "2026-02-01") -> None:
    r = await client.post(
        f"/assets/{asset_id}/snapshots",
        json={"snapshot_date": snapshot_date, "balance": balance},
    )
    assert r.status_code == 201, r.text


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------

async def test_projection_empty_portfolio(client: AsyncClient):
    """No assets → current_total is 0, monthly totals are 0."""
    r = await client.get("/portfolio/projection?months=3")
    assert r.status_code == 200
    data = r.json()
    assert Decimal(data["current_total"]) == Decimal("0.00")
    assert data["asset_summaries"] == []
    assert len(data["monthly"]) == 3
    for m in data["monthly"]:
        assert Decimal(m["portfolio_total"]) == Decimal("0.00")


async def test_projection_no_snapshots(client: AsyncClient):
    """Asset exists but has no snapshots → treated as zero balance."""
    await _make_asset(client, "Ghost Asset", annualized_return_pct="0.10")
    r = await client.get("/portfolio/projection?months=6")
    assert r.status_code == 200
    data = r.json()
    assert Decimal(data["current_total"]) == Decimal("0.00")


async def test_projection_grows_with_positive_return(client: AsyncClient):
    """An asset with a positive return rate should show a growing balance."""
    asset_id = await _make_asset(client, "Stocks", annualized_return_pct="0.12")
    await _add_snapshot(client, asset_id, "10000.00")

    r = await client.get("/portfolio/projection?months=12")
    assert r.status_code == 200
    data = r.json()

    first_month = Decimal(data["monthly"][0]["portfolio_total"])
    last_month = Decimal(data["monthly"][11]["portfolio_total"])
    assert last_month > first_month


async def test_projection_multiple_assets(client: AsyncClient):
    """Multiple assets: current_total = sum of latest balances."""
    id1 = await _make_asset(client, "Asset 1", annualized_return_pct="0.06")
    id2 = await _make_asset(client, "Asset 2", annualized_return_pct="0.04")
    await _add_snapshot(client, id1, "10000.00")
    await _add_snapshot(client, id2, "5000.00")

    r = await client.get("/portfolio/projection?months=1")
    assert r.status_code == 200
    data = r.json()
    assert Decimal(data["current_total"]) == Decimal("15000.00")
    assert len(data["asset_summaries"]) == 2


async def test_projection_uses_latest_snapshot(client: AsyncClient):
    """When an asset has multiple snapshots, only the latest balance is used."""
    asset_id = await _make_asset(client, "Multi-snap", annualized_return_pct="0.0")
    await _add_snapshot(client, asset_id, "1000.00", "2025-01-01")
    await _add_snapshot(client, asset_id, "9999.00", "2025-12-31")

    r = await client.get("/portfolio/projection?months=1")
    assert r.status_code == 200
    data = r.json()
    assert Decimal(data["current_total"]) == Decimal("9999.00")


# ---------------------------------------------------------------------------
# FIRE calculator
# ---------------------------------------------------------------------------

async def test_fire_fields_null_without_expenses(client: AsyncClient):
    """Omitting annual_expenses → all FIRE fields are null."""
    asset_id = await _make_asset(client, "Savings")
    await _add_snapshot(client, asset_id, "50000.00")

    r = await client.get("/portfolio/projection?months=12")
    assert r.status_code == 200
    data = r.json()
    assert data["fire_target"] is None
    assert data["fire_date"] is None
    assert data["months_to_fire"] is None


async def test_fire_target_returned_with_expenses(client: AsyncClient):
    """With annual_expenses supplied, fire_target = expenses / swr."""
    r = await client.get(
        "/portfolio/projection?months=12&annual_expenses=40000&safe_withdrawal_rate=0.04"
    )
    assert r.status_code == 200
    data = r.json()
    assert Decimal(data["fire_target"]) == Decimal("1000000.00")


async def test_fire_date_found(client: AsyncClient):
    """Large balance + positive return → fire_date is populated within window."""
    asset_id = await _make_asset(client, "Big Portfolio", annualized_return_pct="0.10")
    await _add_snapshot(client, asset_id, "950000.00")

    r = await client.get(
        "/portfolio/projection?months=120&annual_expenses=40000&safe_withdrawal_rate=0.04"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fire_date"] is not None
    assert data["months_to_fire"] is not None
    assert 1 <= data["months_to_fire"] <= 120


async def test_fire_date_null_not_reached(client: AsyncClient):
    """Small balance, short window → fire_date should be None."""
    asset_id = await _make_asset(client, "Tiny", annualized_return_pct="0.03")
    await _add_snapshot(client, asset_id, "100.00")

    r = await client.get(
        "/portfolio/projection?months=12&annual_expenses=40000&safe_withdrawal_rate=0.04"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fire_date"] is None


# ---------------------------------------------------------------------------
# is_archived filtering
# ---------------------------------------------------------------------------

async def test_archived_assets_excluded_from_projection(client: AsyncClient):
    """Archived assets must not be included in the projection."""
    active_id = await _make_asset(client, "Active", annualized_return_pct="0.06")
    archived_id = await _make_asset(client, "Archived", annualized_return_pct="0.06")
    await _add_snapshot(client, active_id, "10000.00")
    await _add_snapshot(client, archived_id, "5000.00")

    # Archive the second asset
    await client.patch(f"/assets/{archived_id}", json={"is_archived": True})

    r = await client.get("/portfolio/projection?months=1")
    assert r.status_code == 200
    data = r.json()
    # Only the active asset's balance should be counted
    assert Decimal(data["current_total"]) == Decimal("10000.00")
    assert len(data["asset_summaries"]) == 1
    assert data["asset_summaries"][0]["name"] == "Active"

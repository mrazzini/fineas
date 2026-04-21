"""Integration tests for POST /projection/compute — stateless, no auth."""
from decimal import Decimal

import pytest

PAYLOAD = {
    "assets": [
        {
            "asset_id": "11111111-1111-1111-1111-111111111111",
            "name": "Stocks",
            "current_balance": "10000.00",
            "annualized_return_pct": "0.08",
        },
        {
            "asset_id": "22222222-2222-2222-2222-222222222222",
            "name": "Cash",
            "current_balance": "5000.00",
            "annualized_return_pct": "0.02",
        },
    ],
    "months": 12,
    "monthly_contribution": "0",
    "annual_expenses": "40000",
    "safe_withdrawal_rate": 0.04,
}


@pytest.mark.asyncio
async def test_compute_accessible_without_auth(anon_client):
    """Anonymous caller can hit the stateless compute endpoint."""
    res = await anon_client.post("/projection/compute", json=PAYLOAD)
    assert res.status_code == 200
    data = res.json()
    assert Decimal(data["current_total"]) == Decimal("15000.00")
    assert Decimal(data["fire_target"]) == Decimal("1000000.00")
    assert len(data["monthly"]) == 12


@pytest.mark.asyncio
async def test_compute_empty_assets(anon_client):
    res = await anon_client.post(
        "/projection/compute",
        json={**PAYLOAD, "assets": []},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(data["current_total"]) == Decimal("0.00")
    for m in data["monthly"]:
        assert Decimal(m["portfolio_total"]) == Decimal("0.00")

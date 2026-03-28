"""
Tests for the Phase 4 apply node and POST /ingest/apply endpoint.

No LLM mocking needed — the apply path is pure Python + DB.
Uses the standard `client` fixture from conftest.py for integration tests.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.llm_schemas import ParsedAsset, ParsedPortfolioUpdate, ParsedSnapshot


# ── Helpers ────────────────────────────────────────────────────────────────

def _apply_payload(assets: list[dict] | None = None, snapshots: list[dict] | None = None) -> dict:
    return {
        "validated_assets": assets or [],
        "validated_snapshots": snapshots or [],
    }


def _make_llm_mock(parsed: ParsedPortfolioUpdate) -> MagicMock:
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=parsed)
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


# ── Apply: asset creation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_creates_new_asset(client):
    """A new asset name should be created in the DB."""
    resp = await client.post("/ingest/apply", json=_apply_payload(
        assets=[{"name": "Apply Test ETF", "asset_type": "STOCKS", "ticker": "TEST.DE"}],
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["applied_assets"]) == 1
    assert body["applied_assets"][0]["status"] == "created"
    assert body["applied_assets"][0]["name"] == "Apply Test ETF"

    # Verify it's actually in the DB
    assets_resp = await client.get("/assets")
    names = [a["name"] for a in assets_resp.json()]
    assert "Apply Test ETF" in names


@pytest.mark.asyncio
async def test_apply_matches_existing_asset(client):
    """An existing asset name should be matched, not duplicated."""
    # Pre-create the asset
    create_resp = await client.post("/assets", json={
        "name": "Existing Asset",
        "asset_type": "CASH",
    })
    assert create_resp.status_code == 201
    existing_id = create_resp.json()["id"]

    # Apply with the same name
    resp = await client.post("/ingest/apply", json=_apply_payload(
        assets=[{"name": "Existing Asset", "asset_type": "CASH"}],
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["applied_assets"]) == 1
    assert body["applied_assets"][0]["status"] == "matched"
    assert body["applied_assets"][0]["asset_id"] == existing_id

    # Should still be only one asset with this name
    assets_resp = await client.get("/assets")
    matches = [a for a in assets_resp.json() if a["name"] == "Existing Asset"]
    assert len(matches) == 1


# ── Apply: snapshot upsert ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_upserts_snapshot(client):
    """Snapshots should be created, and re-applying the same date should update."""
    # Create via apply
    resp = await client.post("/ingest/apply", json=_apply_payload(
        assets=[{"name": "Snap Asset", "asset_type": "STOCKS"}],
        snapshots=[{"asset_name": "Snap Asset", "snapshot_date": "2026-03-01", "balance": 5000.0}],
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["applied_snapshots"]) == 1
    assert body["applied_snapshots"][0]["status"] == "upserted"

    asset_id = body["applied_assets"][0]["asset_id"]

    # Verify snapshot exists
    snaps_resp = await client.get(f"/assets/{asset_id}/snapshots")
    snaps = snaps_resp.json()
    assert len(snaps) == 1
    assert float(snaps[0]["balance"]) == 5000.0

    # Upsert with updated balance
    resp2 = await client.post("/ingest/apply", json=_apply_payload(
        assets=[{"name": "Snap Asset", "asset_type": "STOCKS"}],
        snapshots=[{"asset_name": "Snap Asset", "snapshot_date": "2026-03-01", "balance": 7500.0}],
    ))
    assert resp2.status_code == 200
    assert resp2.json()["success"] is True

    # Should still be one snapshot, with updated balance
    snaps_resp2 = await client.get(f"/assets/{asset_id}/snapshots")
    snaps2 = snaps_resp2.json()
    assert len(snaps2) == 1
    assert float(snaps2[0]["balance"]) == 7500.0


# ── Apply: error cases ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_snapshot_without_matching_asset(client):
    """A snapshot referencing a non-existent asset name goes to apply_errors."""
    resp = await client.post("/ingest/apply", json=_apply_payload(
        snapshots=[{"asset_name": "Ghost Asset", "snapshot_date": "2026-01-01", "balance": 100.0}],
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["apply_errors"]) > 0
    assert "Ghost Asset" in body["apply_errors"][0]
    assert body["applied_snapshots"] == []


@pytest.mark.asyncio
async def test_apply_empty_input(client):
    """Empty arrays should produce empty results with no errors."""
    resp = await client.post("/ingest/apply", json=_apply_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["applied_assets"] == []
    assert body["applied_snapshots"] == []
    assert body["apply_errors"] == []


# ── Endpoint integration ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_endpoint_happy_path(client):
    """POST /ingest/apply returns 200 with success: true for valid input."""
    resp = await client.post("/ingest/apply", json=_apply_payload(
        assets=[
            {"name": "E2E ETF", "asset_type": "STOCKS"},
            {"name": "E2E Cash", "asset_type": "CASH"},
        ],
        snapshots=[
            {"asset_name": "E2E ETF", "snapshot_date": "2026-02-01", "balance": 12000.0},
            {"asset_name": "E2E Cash", "snapshot_date": "2026-02-01", "balance": 5000.0},
        ],
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["applied_assets"]) == 2
    assert len(body["applied_snapshots"]) == 2


@pytest.mark.asyncio
async def test_apply_endpoint_creates_and_upserts(client):
    """Verify DB state via GET /assets after apply."""
    await client.post("/ingest/apply", json=_apply_payload(
        assets=[{"name": "Verify Asset", "asset_type": "BONDS"}],
        snapshots=[{"asset_name": "Verify Asset", "snapshot_date": "2026-01-15", "balance": 3000.0}],
    ))

    assets_resp = await client.get("/assets")
    asset = next(a for a in assets_resp.json() if a["name"] == "Verify Asset")
    assert asset["asset_type"] == "BONDS"

    snaps_resp = await client.get(f"/assets/{asset['id']}/snapshots")
    assert len(snaps_resp.json()) == 1
    assert float(snaps_resp.json()[0]["balance"]) == 3000.0


# ── Full HITL flow ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_hitl_flow(client):
    """
    End-to-end: POST /ingest (mocked LLM) -> POST /ingest/apply -> GET /assets.

    Simulates the full HITL workflow: parse, review, then apply.
    """
    parsed = ParsedPortfolioUpdate(
        assets=[ParsedAsset(name="HITL Fund", asset_type="STOCKS", ticker="HITL.DE")],
        snapshots=[ParsedSnapshot(asset_name="HITL Fund", snapshot_date="2026-03-15", balance=25000.0)],
    )
    mock_llm = _make_llm_mock(parsed)

    # Step 1: Parse
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        parse_resp = await client.post("/ingest", json={"text": "HITL Fund 25k"})
    assert parse_resp.status_code == 200
    parse_body = parse_resp.json()
    assert parse_body["is_valid"] is True

    # Step 2: Human reviews (simulated — just pass through)
    # Step 3: Apply
    apply_resp = await client.post("/ingest/apply", json={
        "validated_assets": parse_body["validated_assets"],
        "validated_snapshots": parse_body["validated_snapshots"],
    })
    assert apply_resp.status_code == 200
    apply_body = apply_resp.json()
    assert apply_body["success"] is True
    assert apply_body["applied_assets"][0]["name"] == "HITL Fund"

    # Step 4: Verify in DB
    assets_resp = await client.get("/assets")
    names = [a["name"] for a in assets_resp.json()]
    assert "HITL Fund" in names

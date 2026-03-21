"""
Tests for the Phase 4 HITL session endpoints.

  POST /ingest/sessions              — start a run
  GET  /ingest/sessions/{id}         — poll state
  POST /ingest/sessions/{id}/resume  — approve / correct / reject

Strategy:
  - LLM is mocked (same helper as test_ingest.py).
  - apply() node is mocked via patch("agent.nodes.AsyncSessionLocal") to avoid
    real DB writes.  We verify the HITL *flow* (routing, state transitions,
    interrupt/resume mechanics) — not the SQL queries inside apply.
  - apply() DB logic is covered separately in test_nodes.py.

All tests use the shared `client` fixture from conftest.py (real test DB for
the FastAPI layer, though apply is mocked so no rows are actually written).
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.llm_schemas import ParsedAsset, ParsedPortfolioUpdate, ParsedSnapshot


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_llm_mock(parsed: ParsedPortfolioUpdate) -> MagicMock:
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=parsed)
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


def _valid_response() -> ParsedPortfolioUpdate:
    return ParsedPortfolioUpdate(
        assets=[ParsedAsset(name="Vanguard ETF", asset_type="STOCKS", ticker="VWCE.DE")],
        snapshots=[ParsedSnapshot(asset_name="Vanguard ETF", snapshot_date="2026-02-01", balance=12578.0)],
    )


def _invalid_response() -> ParsedPortfolioUpdate:
    """Returns an asset with an unknown type to trigger a validation error."""
    return ParsedPortfolioUpdate(
        assets=[ParsedAsset(name="Mystery Fund", asset_type="spaceship")],
        snapshots=[ParsedSnapshot(asset_name="Mystery Fund", snapshot_date="2026-02-01", balance=5000.0)],
    )


def _mock_apply_session():
    """
    Return a context-manager mock for AsyncSessionLocal that does nothing.
    Avoids real DB connections in HITL flow tests.
    """
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    @asynccontextmanager
    async def _factory():
        yield mock_session

    mock_session_local = MagicMock(return_value=_factory())
    mock_session_local.side_effect = lambda: _factory()
    return mock_session_local


# ── POST /ingest/sessions ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_session_valid_input_completes(client):
    """
    Valid input → graph runs parse → validate → apply without interruption.
    Response status should be 'complete'.
    """
    mock_llm = _make_llm_mock(_valid_response())
    with (
        patch("agent.nodes.get_llm", return_value=mock_llm),
        patch("agent.nodes.AsyncSessionLocal", side_effect=_mock_apply_session().side_effect),
    ):
        resp = await client.post("/ingest/sessions", json={"text": "My ETF is worth €12,578"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "complete"
    assert "session_id" in body
    assert body["validation_errors"] == []
    assert len(body["validated_assets"]) == 1


@pytest.mark.asyncio
async def test_start_session_invalid_input_pauses(client):
    """
    Invalid input → graph pauses at human_review.
    Response status should be 'pending_review' with errors present.
    """
    mock_llm = _make_llm_mock(_invalid_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        resp = await client.post("/ingest/sessions", json={"text": "some bad data"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending_review"
    assert len(body["validation_errors"]) > 0
    assert body["session_id"] != ""


# ── GET /ingest/sessions/{id} ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_session_returns_current_state(client):
    """GET on a paused session returns the same state as the start response."""
    mock_llm = _make_llm_mock(_invalid_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        start_resp = await client.post("/ingest/sessions", json={"text": "bad input"})

    session_id = start_resp.json()["session_id"]

    get_resp = await client.get(f"/ingest/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "pending_review"
    assert get_resp.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_session_unknown_id_returns_404(client):
    resp = await client.get("/ingest/sessions/does-not-exist")
    assert resp.status_code == 404


# ── POST /ingest/sessions/{id}/resume — approve ────────────────────────────

@pytest.mark.asyncio
async def test_resume_approve_applies_valid_items(client):
    """
    After approval, graph routes to apply with the items that already passed.
    Status should be 'complete'.
    """
    mock_llm = _make_llm_mock(_invalid_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        start_resp = await client.post("/ingest/sessions", json={"text": "bad input"})

    session_id = start_resp.json()["session_id"]

    with patch("agent.nodes.AsyncSessionLocal", side_effect=_mock_apply_session().side_effect):
        resume_resp = await client.post(
            f"/ingest/sessions/{session_id}/resume",
            json={"action": "approve"},
        )

    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "complete"


# ── POST /ingest/sessions/{id}/resume — reject ─────────────────────────────

@pytest.mark.asyncio
async def test_resume_reject_discards_run(client):
    """
    Reject → graph routes to END without writing to DB.
    Status should be 'rejected'.
    """
    mock_llm = _make_llm_mock(_invalid_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        start_resp = await client.post("/ingest/sessions", json={"text": "bad input"})

    session_id = start_resp.json()["session_id"]

    resume_resp = await client.post(
        f"/ingest/sessions/{session_id}/resume",
        json={"action": "reject"},
    )

    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "rejected"


# ── POST /ingest/sessions/{id}/resume — correct ────────────────────────────

@pytest.mark.asyncio
async def test_resume_correct_revalidates_and_applies(client):
    """
    Correct → user provides fixed data → graph re-validates → applies.
    Status should be 'complete' when corrected data passes validation.
    """
    mock_llm = _make_llm_mock(_invalid_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        start_resp = await client.post("/ingest/sessions", json={"text": "bad input"})

    session_id = start_resp.json()["session_id"]

    corrections = {
        "assets": [{"name": "Mystery Fund", "asset_type": "STOCKS"}],
        "snapshots": [{"asset_name": "Mystery Fund", "snapshot_date": "2026-02-01", "balance": 5000.0}],
    }

    with patch("agent.nodes.AsyncSessionLocal", side_effect=_mock_apply_session().side_effect):
        resume_resp = await client.post(
            f"/ingest/sessions/{session_id}/resume",
            json={"action": "correct", "corrections": corrections},
        )

    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "complete"
    assert resume_resp.json()["validation_errors"] == []


# ── Edge cases ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resume_on_completed_session_returns_409(client):
    """Resuming an already-completed session should return 409 Conflict."""
    mock_llm = _make_llm_mock(_valid_response())
    with (
        patch("agent.nodes.get_llm", return_value=mock_llm),
        patch("agent.nodes.AsyncSessionLocal", side_effect=_mock_apply_session().side_effect),
    ):
        start_resp = await client.post("/ingest/sessions", json={"text": "good input"})

    session_id = start_resp.json()["session_id"]
    assert start_resp.json()["status"] == "complete"

    resume_resp = await client.post(
        f"/ingest/sessions/{session_id}/resume",
        json={"action": "approve"},
    )
    assert resume_resp.status_code == 409

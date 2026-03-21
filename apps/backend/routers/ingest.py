"""
Ingestion endpoints — run free-form text through the LangGraph pipeline.

Two endpoint families:

1. Legacy parse-only (Phase 3):
     POST /ingest          — returns parsed + validated JSON, no DB writes

2. HITL session-based (Phase 4):
     POST /ingest/sessions         — start a new run; auto-applies when valid,
                                     pauses for review when validation fails
     GET  /ingest/sessions/{id}    — poll the current state of a session
     POST /ingest/sessions/{id}/resume — approve / correct / reject a paused run

HITL concepts:
  - Each run has a unique thread_id (= session_id) used as the LangGraph
    checkpointer key.  MemorySaver keeps state in-process; the session_id
    is the only handle the client needs.
  - When the graph hits interrupt() in the human_review node, ainvoke()
    returns and aget_state().next is non-empty (graph is suspended).
  - Resuming sends Command(resume={action, corrections}) on the same thread_id.
"""
import uuid

from fastapi import APIRouter, HTTPException, status

from agent import ingest_graph, parse_graph
from schemas import (
    IngestRequest,
    IngestResponse,
    ResumeRequest,
    SessionResponse,
    StartSessionRequest,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ── Helpers ────────────────────────────────────────────────────────────────

_EMPTY_INITIAL_STATE = {
    "parsed_assets": [],
    "parsed_snapshots": [],
    "validated_assets": [],
    "validated_snapshots": [],
    "validation_errors": [],
    "human_decision": "",
    "human_corrections": {},
    "applied_assets_count": 0,
    "applied_snapshots_count": 0,
}


async def _state_to_response(session_id: str) -> SessionResponse:
    """Read the current graph state and map it to SessionResponse."""
    config = {"configurable": {"thread_id": session_id}}
    snapshot = await ingest_graph.aget_state(config)

    if snapshot is None or not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    values = snapshot.values

    # Determine status:
    #   - snapshot.next is non-empty → graph is suspended at human_review
    #   - human_decision == "reject" → run was discarded
    #   - otherwise → graph completed normally
    if snapshot.next:
        run_status = "pending_review"
    elif values.get("human_decision") == "reject":
        run_status = "rejected"
    else:
        run_status = "complete"

    return SessionResponse(
        session_id=session_id,
        status=run_status,
        validation_errors=values.get("validation_errors", []),
        parsed_assets=values.get("parsed_assets", []),
        parsed_snapshots=values.get("parsed_snapshots", []),
        validated_assets=values.get("validated_assets", []),
        validated_snapshots=values.get("validated_snapshots", []),
        applied_assets_count=values.get("applied_assets_count", 0),
        applied_snapshots_count=values.get("applied_snapshots_count", 0),
    )


# ── Legacy endpoint (Phase 3 — parse-only) ────────────────────────────────

@router.post("", response_model=IngestResponse)
async def ingest(payload: IngestRequest) -> IngestResponse:
    """
    Parse free-form text into structured asset + snapshot data.

    Parse-only — does NOT write to the database.  Use POST /ingest/sessions
    for the full HITL flow that also persists the result.
    """
    try:
        final_state = await parse_graph.ainvoke(
            {**_EMPTY_INITIAL_STATE, "raw_text": payload.text},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion pipeline error: {exc}",
        ) from exc

    return IngestResponse(
        parsed_assets=final_state.get("parsed_assets", []),
        parsed_snapshots=final_state.get("parsed_snapshots", []),
        validated_assets=final_state.get("validated_assets", []),
        validated_snapshots=final_state.get("validated_snapshots", []),
        validation_errors=final_state.get("validation_errors", []),
        is_valid=len(final_state.get("validation_errors", [])) == 0,
    )


# ── HITL session endpoints (Phase 4) ──────────────────────────────────────

@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(payload: StartSessionRequest) -> SessionResponse:
    """
    Start a new ingestion session.

    The graph runs parse → validate and then:
      - If the input is valid: continues to apply and writes to the DB.
        Returns status="complete".
      - If validation fails: pauses at human_review (interrupt()).
        Returns status="pending_review" with the errors and parsed data so
        the client can display them for human correction.

    The returned session_id is required for all subsequent calls on this run.
    """
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    try:
        await ingest_graph.ainvoke(
            {**_EMPTY_INITIAL_STATE, "raw_text": payload.text},
            config=config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion pipeline error: {exc}",
        ) from exc

    return await _state_to_response(session_id)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Return the current state of an ingestion session."""
    return await _state_to_response(session_id)


@router.post("/sessions/{session_id}/resume", response_model=SessionResponse)
async def resume_session(
    session_id: str,
    payload: ResumeRequest,
) -> SessionResponse:
    """
    Resume a paused ingestion session with a human decision.

    - approve:  apply the items that already passed validation as-is.
    - correct:  provide corrected assets/snapshots; graph re-validates then applies.
    - reject:   discard the run; nothing is written to the database.

    Returns the updated SessionResponse.  For approve/correct the status
    will be "complete" on success; for reject it will be "rejected".
    """
    config = {"configurable": {"thread_id": session_id}}

    # Verify the session exists and is actually paused.
    snapshot = await ingest_graph.aget_state(config)
    if snapshot is None or not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    if not snapshot.next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is not paused — nothing to resume.",
        )

    from langgraph.types import Command  # local import mirrors nodes.py pattern

    try:
        await ingest_graph.ainvoke(
            Command(resume={
                "action": payload.action,
                "corrections": payload.corrections,
            }),
            config=config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume error: {exc}",
        ) from exc

    return await _state_to_response(session_id)

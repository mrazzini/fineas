"""
POST /ingest — run free-form text through the LangGraph ingestion pipeline.
POST /ingest/apply — write human-approved data to the database (Phase 4 HITL).

Route summary:
  POST /ingest        → 200 IngestResponse | 422 (FastAPI validation) | 500
  POST /ingest/apply  → 200 ApplyResponse  | 422 | 500
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent import build_apply_graph, ingest_graph
from database import get_db
from schemas import ApplyRequest, ApplyResponse, IngestRequest, IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest(payload: IngestRequest) -> IngestResponse:
    """
    Parse free-form text into structured asset + snapshot data.

    The request body is a single `text` field — anything from a sentence like
    "My Vanguard ETF is worth €12,578 as of February 2026" to a pasted CSV.

    The LangGraph pipeline (parse → validate) runs and the full state is
    returned.  `is_valid: true` means everything parsed cleanly and is ready
    to be applied via the upsert endpoint.
    """
    try:
        # ainvoke() runs the graph asynchronously from START to END.
        # We pass the initial state as a dict — only the keys that exist at
        # the start need to be provided; the rest default to empty lists.
        final_state = await ingest_graph.ainvoke({
            "raw_text": payload.text,
            "parsed_assets": [],
            "parsed_snapshots": [],
            "validated_assets": [],
            "validated_snapshots": [],
            "validation_errors": [],
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion pipeline error: {exc}",
        ) from exc

    return IngestResponse(
        parsed_assets=final_state["parsed_assets"],
        parsed_snapshots=final_state["parsed_snapshots"],
        validated_assets=final_state["validated_assets"],
        validated_snapshots=final_state["validated_snapshots"],
        validation_errors=final_state["validation_errors"],
        is_valid=len(final_state["validation_errors"]) == 0,
    )


@router.post("/apply", response_model=ApplyResponse)
async def apply_ingest(
    payload: ApplyRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplyResponse:
    """
    Write human-approved validated data to the database.

    This is the second step of the HITL flow:
      1. POST /ingest → parse + validate (no DB writes)
      2. Human reviews and curates the result
      3. POST /ingest/apply → find-or-create assets, upsert snapshots
    """
    try:
        graph = build_apply_graph(db)
        final_state = await graph.ainvoke({
            "raw_text": "",
            "parsed_assets": [],
            "parsed_snapshots": [],
            "validated_assets": payload.validated_assets,
            "validated_snapshots": payload.validated_snapshots,
            "validation_errors": [],
            "applied_assets": [],
            "applied_snapshots": [],
            "apply_errors": [],
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Apply pipeline error: {exc}",
        ) from exc

    errors = final_state.get("apply_errors", [])
    return ApplyResponse(
        applied_assets=final_state.get("applied_assets", []),
        applied_snapshots=final_state.get("applied_snapshots", []),
        apply_errors=errors,
        success=len(errors) == 0,
    )

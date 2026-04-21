"""
POST /ingest        — parse free-form text via LangGraph (stateless, no auth).
POST /ingest/apply  — write human-approved data to the DB (auth required).

Routes:
  POST /ingest        -> 200 IngestResponse | 422 | 500
  POST /ingest/apply  -> 200 ApplyResponse  | 401 | 422 | 500
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent import build_apply_graph, ingest_graph_with_context
from auth import require_owner
from database import get_db
from schemas import ApplyRequest, ApplyResponse, IngestRequest, IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest(payload: IngestRequest) -> IngestResponse:
    """Parse free-form text into structured asset + snapshot data.

    Stateless: any existing-asset context for LLM deduplication must be
    supplied inline via `existing_assets`. No DB read, no auth — usable by
    anonymous demo visitors and the authed owner alike.
    """
    try:
        existing = [a.model_dump() for a in payload.existing_assets]
        final_state = await ingest_graph_with_context.ainvoke({
            "raw_text": payload.text,
            "existing_assets": existing,
            "parsed_assets": [],
            "parsed_snapshots": [],
            "validated_assets": [],
            "validated_snapshots": [],
            "validation_errors": [],
            "ambiguous_assets": [],
            "resolved_names": {},
            "applied_assets": [],
            "applied_snapshots": [],
            "apply_errors": [],
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
        ambiguous_assets=final_state.get("ambiguous_assets", []),
    )


@router.post("/apply", response_model=ApplyResponse)
async def apply_ingest(
    payload: ApplyRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_owner),
) -> ApplyResponse:
    """Write human-approved validated data to the database."""
    try:
        graph = build_apply_graph(db)
        final_state = await graph.ainvoke({
            "raw_text": "",
            "existing_assets": [],
            "parsed_assets": [],
            "parsed_snapshots": [],
            "validated_assets": payload.validated_assets,
            "validated_snapshots": payload.validated_snapshots,
            "validation_errors": [],
            "ambiguous_assets": [],
            "resolved_names": payload.resolved_names,
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

"""
POST /ingest — run free-form text through the LangGraph ingestion pipeline.

This endpoint is intentionally parse-only: it returns structured, validated
JSON but does NOT write anything to the database.  The caller (or the Phase 4
HITL agent) decides what to do with the result.

Route summary:
  POST /ingest  → 200 IngestResponse | 422 (FastAPI validation) | 500
"""
from fastapi import APIRouter, HTTPException, status

from agent import ingest_graph
from schemas import IngestRequest, IngestResponse

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

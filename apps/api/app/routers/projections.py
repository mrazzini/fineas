import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.projection import Projection
from app.schemas.projection import CompoundParams, CompoundResult, ProjectionResponse
from app.services.projection import run_compound_projection

router = APIRouter()


@router.post("/run", response_model=CompoundResult)
async def run_projection(
    params: CompoundParams,
    session: AsyncSession = Depends(get_session),
) -> CompoundResult:
    result = await run_compound_projection(params, session)

    # Persist the projection result
    proj = Projection(
        method="compound",
        params=params.model_dump(),
        results=result.model_dump(),
        computed_at=datetime.now(timezone.utc),
    )
    session.add(proj)
    await session.commit()

    return result


@router.get("/{goal_id}", response_model=list[ProjectionResponse])
async def get_projections_for_goal(
    goal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> list[Projection]:
    stmt = (
        select(Projection)
        .where(Projection.goal_id == goal_id)
        .order_by(Projection.computed_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

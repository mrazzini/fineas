import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate

router = APIRouter()


@router.get("/", response_model=list[GoalResponse])
async def list_goals(
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[Goal]:
    stmt = select(Goal)
    if not include_inactive:
        stmt = stmt.where(Goal.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=GoalResponse, status_code=201)
async def create_goal(
    payload: GoalCreate,
    session: AsyncSession = Depends(get_session),
) -> Goal:
    goal = Goal(**payload.model_dump())
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    payload: GoalUpdate,
    session: AsyncSession = Depends(get_session),
) -> Goal:
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    await session.commit()
    await session.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal.is_active = False
    await session.commit()

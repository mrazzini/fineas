import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProjectionCreate(BaseModel):
    goal_id: uuid.UUID | None = None
    method: str  # "compound" | "monte_carlo" | "scenario"
    params: dict[str, Any]


class ProjectionResponse(BaseModel):
    id: uuid.UUID
    goal_id: uuid.UUID | None
    computed_at: datetime
    method: str
    params: dict[str, Any]
    results: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class CompoundParams(BaseModel):
    monthly_contribution: float
    horizon_years: int = 20
    target_amount: float | None = None


class CompoundYearlyPoint(BaseModel):
    year: int
    projected_value: float
    cumulative_contributions: float
    cumulative_returns: float


class CompoundResult(BaseModel):
    yearly_trajectory: list[CompoundYearlyPoint]
    target_hit_year: int | None
    final_value_at_horizon: float
    weighted_return: float

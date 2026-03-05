import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class GoalBase(BaseModel):
    name: str
    description: str | None = None
    target_amount: float
    target_date: date | None = None
    goal_type: str
    asset_scope: Any = "all"
    is_active: bool = True


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_amount: float | None = None
    target_date: date | None = None
    goal_type: str | None = None
    asset_scope: Any | None = None
    is_active: bool | None = None


class GoalResponse(GoalBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    goal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_scope: Mapped[dict | str] = mapped_column(
        JSONB, default="all", server_default=text("'\"all\"'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    projections: Mapped[list["Projection"]] = relationship(  # noqa: F821
        "Projection", back_populates="goal", cascade="all, delete-orphan"
    )

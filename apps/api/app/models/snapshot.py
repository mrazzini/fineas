import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Snapshot(Base):
    __tablename__ = "snapshots"

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_snapshot_asset_date"),
        Index("ix_snapshot_asset_date", "asset_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", server_default=text("'manual'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="snapshots")  # noqa: F821

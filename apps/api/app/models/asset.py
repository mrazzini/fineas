import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expected_annual_return: Mapped[float | None] = mapped_column(Numeric(8, 5), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    snapshots: Mapped[list["Snapshot"]] = relationship(  # noqa: F821
        "Snapshot", back_populates="asset", cascade="all, delete-orphan"
    )

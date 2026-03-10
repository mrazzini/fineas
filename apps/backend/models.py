"""
SQLAlchemy 2.0 ORM models for Fineas.

Two-table design:
  - Asset:          defines WHAT an asset is (static, definitional)
  - AssetSnapshot:  records WHAT an asset is worth at a given date (time-series)
"""
import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AssetType(str, enum.Enum):
    CASH = "CASH"
    STOCKS = "STOCKS"
    BONDS = "BONDS"
    REAL_ESTATE = "REAL_ESTATE"
    CRYPTO = "CRYPTO"
    PENSION_FUND = "PENSION_FUND"
    OTHER = "OTHER"


class Asset(Base):
    """
    Represents a financial asset (e.g., 'Vanguard FTSE All-World').
    Stores definitional, rarely-changing data about the asset.
    """
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type_enum"), nullable=False
    )
    # Expected nominal annual return as a decimal (e.g., 0.085 = 8.5%).
    # Nullable — cash accounts or pension funds may not have a fixed rate.
    annualized_return_pct: Mapped[float | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    # Optional market ticker for future live-price lookups (e.g., "VWCE.DE").
    # Not UNIQUE: the same ETF can be held at multiple brokers as separate assets.
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    snapshots: Mapped[list["AssetSnapshot"]] = relationship(
        "AssetSnapshot", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} name={self.name!r} type={self.asset_type}>"


class AssetSnapshot(Base):
    """
    Records the balance of an asset on a specific date.
    One row per (asset, date) — append-only time-series log.
    The UNIQUE constraint on (asset_id, snapshot_date) enables safe upserts.
    """
    __tablename__ = "asset_snapshots"

    __table_args__ = (
        UniqueConstraint("asset_id", "snapshot_date", name="uq_snapshot_asset_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Exact decimal — never use Float for monetary values.
    balance: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="snapshots")

    def __repr__(self) -> str:
        return (
            f"<AssetSnapshot asset_id={self.asset_id} "
            f"date={self.snapshot_date} balance={self.balance}>"
        )

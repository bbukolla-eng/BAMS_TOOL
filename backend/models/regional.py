"""Regional cost multipliers and labor-rate tables."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class RegionalMultiplier(Base):
    """Per-region cost multiplier applied to raw (material + labor + equipment).

    `code` is the canonical key used by Project.region_code. Either a state code
    ("NY", "CA") or a metro override ("NY_METRO", "MA_BOSTON").
    """

    __tablename__ = "regional_multipliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)

    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str | None] = mapped_column(String(2), index=True)  # "NY", "CA"
    is_metro: Mapped[bool] = mapped_column(Boolean, default=False)

    # Core multiplier applied to raw direct costs
    material_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    labor_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    equipment_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    # Aggregate multiplier — what bids actually apply to total line cost
    total_multiplier: Mapped[float] = mapped_column(Float, default=1.0)

    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LaborRate(Base):
    """Labor rate by region × trade category.

    `trade_category` is one of: sheet_metal, steamfitter, plumber, electrician,
    laborer. These are not the same as Trades (MECH/ELEC/PLMB) — one MECH trade
    has both sheet_metal and steamfitter categories.
    """

    __tablename__ = "labor_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)

    region_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    trade_category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)  # $/hr fully burdened
    foreman_rate: Mapped[float | None] = mapped_column(Float)
    is_union: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(100))  # "Local 638 CBA 2024"
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PriceBookItem(Base):
    __tablename__ = "price_book_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), index=True)

    # Identification
    csi_code: Mapped[str | None] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[str | None] = mapped_column(String(100))  # "12x8", "6\"", "1/2\""
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # "LF", "EA", "SF"

    # Pricing
    material_unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    labor_hours_per_unit: Mapped[float] = mapped_column(Float, default=0.0)
    labor_rate: Mapped[float | None] = mapped_column(Float)  # $/hr, falls back to trade rate if null

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LaborAssembly(Base):
    __tablename__ = "labor_assemblies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    hours_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

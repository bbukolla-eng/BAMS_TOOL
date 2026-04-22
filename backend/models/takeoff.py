from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class TakeoffItem(Base):
    __tablename__ = "takeoff_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    drawing_page_id: Mapped[int | None] = mapped_column(ForeignKey("drawing_pages.id"), index=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"))
    price_book_item_id: Mapped[int | None] = mapped_column(ForeignKey("price_book_items.id"))

    # Classification
    category: Mapped[str] = mapped_column(String(100), index=True)
    # "duct", "duct_fitting", "pipe", "pipe_fitting", "insulation", "equipment", "diffuser", "damper", "valve"
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    csi_code: Mapped[str | None] = mapped_column(String(20))  # "23 31 13.16"
    system: Mapped[str | None] = mapped_column(String(100))   # "Supply Air", "Chilled Water"

    # Quantity
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # "LF", "EA", "SF", "LB", "TON"
    waste_factor: Mapped[float] = mapped_column(Float, default=0.05)
    adjusted_quantity: Mapped[float] = mapped_column(Float, nullable=False)  # qty * (1 + waste)

    # Pricing (filled in by bidding engine)
    unit_material_cost: Mapped[float | None] = mapped_column(Float)
    unit_labor_hours: Mapped[float | None] = mapped_column(Float)
    material_total: Mapped[float | None] = mapped_column(Float)
    labor_total: Mapped[float | None] = mapped_column(Float)
    total_cost: Mapped[float | None] = mapped_column(Float)

    # Source references
    source_symbol_ids: Mapped[list | None] = mapped_column(JSON)
    source_run_ids: Mapped[list | None] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="takeoff_items")  # type: ignore[name-defined]

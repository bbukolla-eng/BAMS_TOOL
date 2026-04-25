from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class BidStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    won = "won"
    lost = "lost"
    no_bid = "no_bid"


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    overhead_config_id: Mapped[int | None] = mapped_column(ForeignKey("overhead_configs.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Bid v1")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default=BidStatus.draft, index=True)

    # Totals (computed and cached)
    total_material_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_labor_hours: Mapped[float] = mapped_column(Float, default=0.0)
    total_labor_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_burden: Mapped[float] = mapped_column(Float, default=0.0)
    total_overhead: Mapped[float] = mapped_column(Float, default=0.0)
    total_material_markup: Mapped[float] = mapped_column(Float, default=0.0)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    contingency: Mapped[float] = mapped_column(Float, default=0.0)
    bond: Mapped[float] = mapped_column(Float, default=0.0)
    permit: Mapped[float] = mapped_column(Float, default=0.0)
    profit: Mapped[float] = mapped_column(Float, default=0.0)
    total_equipment_cost: Mapped[float] = mapped_column(Float, default=0.0)
    grand_total: Mapped[float] = mapped_column(Float, default=0.0)

    # Regional cost factor snapshot (1.0 = no adjustment). Captured at calculate time
    # from the project's region_code so past bids remain stable if the lookup table changes.
    regional_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    region_code: Mapped[str | None] = mapped_column(String(40))

    notes: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="bids")  # type: ignore[name-defined]
    line_items: Mapped[list["BidLineItem"]] = relationship("BidLineItem", back_populates="bid", cascade="all, delete-orphan")
    summary_sections: Mapped[list["BidSummarySection"]] = relationship("BidSummarySection", back_populates="bid", cascade="all, delete-orphan")
    assumptions: Mapped[list["BidAssumption"]] = relationship("BidAssumption", back_populates="bid", cascade="all, delete-orphan")  # type: ignore[name-defined]
    exclusions: Mapped[list["BidExclusion"]] = relationship("BidExclusion", back_populates="bid", cascade="all, delete-orphan")  # type: ignore[name-defined]
    alternates: Mapped[list["BidAlternate"]] = relationship("BidAlternate", back_populates="bid", cascade="all, delete-orphan")  # type: ignore[name-defined]
    proposals: Mapped[list["Proposal"]] = relationship("Proposal", back_populates="bid")  # type: ignore[name-defined]


class BidLineItem(Base):
    __tablename__ = "bid_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id"), nullable=False, index=True)
    takeoff_item_id: Mapped[int | None] = mapped_column(ForeignKey("takeoff_items.id"))
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    system: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    unit_material_cost: Mapped[float] = mapped_column(Float, default=0.0)
    unit_labor_hours: Mapped[float] = mapped_column(Float, default=0.0)
    labor_rate: Mapped[float] = mapped_column(Float, default=0.0)
    unit_equipment_cost: Mapped[float] = mapped_column(Float, default=0.0)

    material_total: Mapped[float] = mapped_column(Float, default=0.0)
    labor_total: Mapped[float] = mapped_column(Float, default=0.0)
    equipment_total: Mapped[float] = mapped_column(Float, default=0.0)
    line_total: Mapped[float] = mapped_column(Float, default=0.0)  # includes regional multiplier

    notes: Mapped[str | None] = mapped_column(Text)

    bid: Mapped[Bid] = relationship("Bid", back_populates="line_items")


class BidSummarySection(Base):
    __tablename__ = "bid_summary_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    group_by: Mapped[str] = mapped_column(String(50))  # "trade", "system", "phase", "category"
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    material_subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    labor_subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    section_total: Mapped[float] = mapped_column(Float, default=0.0)

    bid: Mapped[Bid] = relationship("Bid", back_populates="summary_sections")

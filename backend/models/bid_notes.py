"""Assumptions, Exclusions, and Alternates attached to a bid."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class BidAssumption(Base):
    __tablename__ = "bid_assumptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str | None] = mapped_column(String(100))  # e.g. "Schedule", "Scope", "Pricing"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bid: Mapped["Bid"] = relationship("Bid", back_populates="assumptions")  # type: ignore[name-defined]


class BidExclusion(Base):
    __tablename__ = "bid_exclusions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str | None] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bid: Mapped["Bid"] = relationship("Bid", back_populates="exclusions")  # type: ignore[name-defined]


class BidAlternate(Base):
    __tablename__ = "bid_alternates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bid_id: Mapped[int] = mapped_column(ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_add: Mapped[bool] = mapped_column(default=True)  # True = add, False = deduct
    cost_impact: Mapped[float] = mapped_column(Float, default=0.0)  # signed: +add, +deduct (sign carried by is_add)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bid: Mapped["Bid"] = relationship("Bid", back_populates="alternates")  # type: ignore[name-defined]

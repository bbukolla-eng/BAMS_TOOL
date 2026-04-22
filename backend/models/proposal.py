from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class ProposalStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    bid_id: Mapped[int | None] = mapped_column(ForeignKey("bids.id"))
    status: Mapped[str] = mapped_column(String(50), default=ProposalStatus.draft)

    proposal_number: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(255))
    client_address: Mapped[str | None] = mapped_column(String(500))
    attention_to: Mapped[str | None] = mapped_column(String(255))
    project_description: Mapped[str | None] = mapped_column(Text)
    scope_of_work: Mapped[str | None] = mapped_column(Text)
    inclusions: Mapped[str | None] = mapped_column(Text)
    exclusions: Mapped[str | None] = mapped_column(Text)
    clarifications: Mapped[str | None] = mapped_column(Text)
    terms_conditions: Mapped[str | None] = mapped_column(Text)
    validity_days: Mapped[int] = mapped_column(Integer, default=30)
    expiry_date: Mapped[date | None] = mapped_column(Date)

    file_path: Mapped[str | None] = mapped_column(String(1000))  # generated PDF path

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bid: Mapped["Bid"] = relationship("Bid", back_populates="proposals")  # type: ignore[name-defined]

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class SubmittalStatus(str, Enum):
    not_submitted = "not_submitted"
    submitted = "submitted"
    under_review = "under_review"
    approved = "approved"
    approved_as_noted = "approved_as_noted"
    revise_resubmit = "revise_resubmit"
    rejected = "rejected"


class Submittal(Base):
    __tablename__ = "submittals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    spec_section_id: Mapped[int | None] = mapped_column(ForeignKey("spec_sections.id"))
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id"))

    submittal_number: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    spec_section_ref: Mapped[str | None] = mapped_column(String(50))  # "23 74 13"
    status: Mapped[str] = mapped_column(String(50), default=SubmittalStatus.not_submitted, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=0)

    submitted_date: Mapped[date | None] = mapped_column(Date)
    required_date: Mapped[date | None] = mapped_column(Date)
    returned_date: Mapped[date | None] = mapped_column(Date)

    file_path: Mapped[str | None] = mapped_column(String(1000))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    submitter_notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="submittals")  # type: ignore[name-defined]
    items: Mapped[list["SubmittalItem"]] = relationship("SubmittalItem", back_populates="submittal", cascade="all, delete-orphan")


class SubmittalItem(Base):
    __tablename__ = "submittal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submittal_id: Mapped[int] = mapped_column(ForeignKey("submittals.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    submittal: Mapped[Submittal] = relationship("Submittal", back_populates="items")

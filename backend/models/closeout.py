from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class CloseoutDocType(str, Enum):
    om_manual = "om_manual"
    warranty = "warranty"
    as_built = "as_built"
    punch_list = "punch_list"
    attic_stock = "attic_stock"
    training_record = "training_record"
    test_balance_report = "test_balance_report"
    commissioning_report = "commissioning_report"
    certificate_completion = "certificate_completion"
    lien_waiver = "lien_waiver"
    other = "other"


class CloseoutDocument(Base):
    __tablename__ = "closeout_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id"))

    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # For warranties
    warranty_duration_months: Mapped[int | None] = mapped_column(Integer)
    warranty_start_date: Mapped[date | None] = mapped_column(Date)
    warranty_expiry_date: Mapped[date | None] = mapped_column(Date)
    warranty_provider: Mapped[str | None] = mapped_column(String(255))

    is_received: Mapped[bool] = mapped_column(Boolean, default=False)
    received_date: Mapped[date | None] = mapped_column(Date)
    file_path: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="closeout_docs")  # type: ignore[name-defined]

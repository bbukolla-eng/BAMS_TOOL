from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"))
    spec_section_id: Mapped[int | None] = mapped_column(ForeignKey("spec_sections.id"))
    submittal_id: Mapped[int | None] = mapped_column(ForeignKey("submittals.id"))

    # Identity
    tag: Mapped[str | None] = mapped_column(String(100), index=True)  # "AHU-1", "FCU-101"
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # "ahu", "fcu", "vav", "diffuser", "fan", "pump", "boiler", "chiller", "cooling_tower", "vrf"
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    csi_code: Mapped[str | None] = mapped_column(String(20))

    # Product info
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(255))
    serial_number: Mapped[str | None] = mapped_column(String(255))

    # Technical specs (flexible JSON)
    specifications: Mapped[dict | None] = mapped_column(JSON)
    # For HVAC: {"cfm": 5000, "cooling_tons": 15, "heating_kw": 30, "static_pressure_in_wg": 2.0}

    # Location
    location_description: Mapped[str | None] = mapped_column(String(500))
    floor: Mapped[str | None] = mapped_column(String(50))
    room: Mapped[str | None] = mapped_column(String(100))
    drawing_id: Mapped[int | None] = mapped_column(ForeignKey("drawings.id"))
    drawing_coordinates: Mapped[dict | None] = mapped_column(JSON)  # {x, y, page}

    # Status
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_installed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="equipment")  # type: ignore[name-defined]

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Specification(Base):
    __tablename__ = "specifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    division: Mapped[str | None] = mapped_column(String(10), index=True)  # "23", "26", "22"
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="specifications")  # type: ignore[name-defined]
    sections: Mapped[list["SpecSection"]] = relationship("SpecSection", back_populates="specification", cascade="all, delete-orphan")


class SpecSection(Base):
    __tablename__ = "spec_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    specification_id: Mapped[int] = mapped_column(ForeignKey("specifications.id"), nullable=False, index=True)
    section_number: Mapped[str | None] = mapped_column(String(20), index=True)  # "23 31 13"
    section_title: Mapped[str | None] = mapped_column(String(500))
    raw_text: Mapped[str | None] = mapped_column(Text)
    structured_data: Mapped[str | None] = mapped_column(Text)  # JSON string from Claude
    embedding: Mapped[list | None] = mapped_column(Vector(768))
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    specification: Mapped[Specification] = relationship("Specification", back_populates="sections")
    drawing_links: Mapped[list["SpecDrawingLink"]] = relationship("SpecDrawingLink", back_populates="spec_section")


class SpecDrawingLink(Base):
    __tablename__ = "spec_drawing_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spec_section_id: Mapped[int] = mapped_column(ForeignKey("spec_sections.id"), nullable=False, index=True)
    symbol_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id"))
    material_run_id: Mapped[int | None] = mapped_column(ForeignKey("material_runs.id"))
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_type: Mapped[str] = mapped_column(String(20), default="auto")  # "auto", "manual"
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    spec_section: Mapped[SpecSection] = relationship("SpecSection", back_populates="drawing_links")

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class DrawingDiscipline(str, Enum):
    mechanical = "mechanical"
    electrical = "electrical"
    plumbing = "plumbing"
    civil = "civil"
    architectural = "architectural"
    structural = "structural"
    fire_protection = "fire_protection"


class DrawingFileType(str, Enum):
    pdf = "pdf"
    dxf = "dxf"
    dwg = "dwg"
    image = "image"


class ProcessingStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"


class DetectionSource(str, Enum):
    yolo = "yolo"
    rule = "rule"
    manual = "manual"
    vector = "vector"


class Drawing(Base):
    __tablename__ = "drawings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sheet_number: Mapped[str | None] = mapped_column(String(50))
    discipline: Mapped[str] = mapped_column(String(50), default=DrawingDiscipline.mechanical, index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    processing_status: Mapped[str] = mapped_column(String(50), default=ProcessingStatus.pending, index=True)
    processing_error: Mapped[str | None] = mapped_column(Text)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    coord_system: Mapped[dict | None] = mapped_column(JSON)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="drawings")  # type: ignore[name-defined]
    pages: Mapped[list["DrawingPage"]] = relationship("DrawingPage", back_populates="drawing", cascade="all, delete-orphan")
    markups: Mapped[list["DrawingMarkup"]] = relationship("DrawingMarkup", back_populates="drawing")


class DrawingPage(Base):
    __tablename__ = "drawing_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drawing_id: Mapped[int] = mapped_column(ForeignKey("drawings.id"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    raster_path: Mapped[str | None] = mapped_column(String(1000))
    tile_manifest_path: Mapped[str | None] = mapped_column(String(1000))
    width_px: Mapped[int | None] = mapped_column(Integer)
    height_px: Mapped[int | None] = mapped_column(Integer)
    # Real-world dimensions in feet
    width_ft: Mapped[float | None] = mapped_column(Float)
    height_ft: Mapped[float | None] = mapped_column(Float)
    scale_factor: Mapped[float | None] = mapped_column(Float)  # pixels per foot
    scale_label: Mapped[str | None] = mapped_column(String(50))  # "1/8\" = 1'-0\""
    geometry_data: Mapped[dict | None] = mapped_column(JSON)  # extracted vector paths
    processing_status: Mapped[str] = mapped_column(String(50), default=ProcessingStatus.pending)

    drawing: Mapped[Drawing] = relationship("Drawing", back_populates="pages")
    symbols: Mapped[list["Symbol"]] = relationship("Symbol", back_populates="page", cascade="all, delete-orphan")
    material_runs: Mapped[list["MaterialRun"]] = relationship("MaterialRun", back_populates="page", cascade="all, delete-orphan")


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("drawing_pages.id"), nullable=False, index=True)
    symbol_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Drawing coordinates (in feet, not pixels)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float | None] = mapped_column(Float)
    height: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    detection_source: Mapped[str] = mapped_column(String(50), default=DetectionSource.yolo)
    label: Mapped[str | None] = mapped_column(String(255))
    properties: Mapped[dict | None] = mapped_column(JSON)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id"))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    page: Mapped[DrawingPage] = relationship("DrawingPage", back_populates="symbols")


class MaterialRun(Base):
    __tablename__ = "material_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("drawing_pages.id"), nullable=False, index=True)
    material_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # "conduit", "pipe_chw", "pipe_hw", "duct_supply", "duct_return", "duct_exhaust", "wire", "cable_tray"
    path: Mapped[list] = mapped_column(JSON, nullable=False)  # [{x, y}, ...] in feet
    length_ft: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[str | None] = mapped_column(String(50))  # "4x10 rect", "12\" round", "4\" pipe"
    spec_reference: Mapped[str | None] = mapped_column(String(255))
    layer_name: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    detection_source: Mapped[str] = mapped_column(String(50), default=DetectionSource.vector)
    # Fitting counts inferred from connectivity: {"elbow_45": n, "elbow_90": n,
    # "tee": n, "cross": n, "transition": n}
    fittings: Mapped[dict | None] = mapped_column(JSON)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    page: Mapped[DrawingPage] = relationship("DrawingPage", back_populates="material_runs")


class DrawingMarkup(Base):
    __tablename__ = "drawing_markups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drawing_id: Mapped[int] = mapped_column(ForeignKey("drawings.id"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    markup_type: Mapped[str] = mapped_column(String(50))  # "symbol_box", "run_highlight", "callout", "measurement"
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    color: Mapped[str | None] = mapped_column(String(20))
    label: Mapped[str | None] = mapped_column(String(500))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    drawing: Mapped[Drawing] = relationship("Drawing", back_populates="markups")

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # "symbol_correction", "run_correction", "spec_link_correction", "bid_adjustment", "takeoff_edit"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "symbol", "run", "spec_link"
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    drawing_id: Mapped[int | None] = mapped_column(ForeignKey("drawings.id"))
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    image_crop_path: Mapped[str | None] = mapped_column(String(1000))  # for YOLO training
    is_training_candidate: Mapped[bool | None] = mapped_column(Integer, default=True)
    used_in_training_job_id: Mapped[int | None] = mapped_column(ForeignKey("ml_training_jobs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MLTrainingJob(Base):
    __tablename__ = "ml_training_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "yolo_mechanical", "yolo_electrical"
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    triggered_by: Mapped[str] = mapped_column(String(50), default="scheduled")  # "scheduled", "manual"
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    dataset_snapshot_path: Mapped[str | None] = mapped_column(String(1000))
    model_artifact_path: Mapped[str | None] = mapped_column(String(1000))
    baseline_map50: Mapped[float | None] = mapped_column(Float)
    new_map50: Mapped[float | None] = mapped_column(Float)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    was_promoted: Mapped[bool | None] = mapped_column(Integer, default=None)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

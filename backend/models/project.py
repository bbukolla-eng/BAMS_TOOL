from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class ProjectStatus(str, Enum):
    active = "active"
    bidding = "bidding"
    won = "won"
    lost = "lost"
    archived = "archived"


class ProjectType(str, Enum):
    commercial = "commercial"
    industrial = "industrial"
    residential = "residential"
    institutional = "institutional"
    healthcare = "healthcare"
    data_center = "data_center"


class TaskStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_number: Mapped[str | None] = mapped_column(String(100), index=True)
    project_type: Mapped[str] = mapped_column(String(50), default=ProjectType.commercial)
    status: Mapped[str] = mapped_column(String(50), default=ProjectStatus.active, index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    bid_due_date: Mapped[date | None] = mapped_column(Date)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="projects")  # type: ignore[name-defined]
    members: Mapped[list["ProjectMember"]] = relationship("ProjectMember", back_populates="project")
    drawings: Mapped[list["Drawing"]] = relationship("Drawing", back_populates="project")  # type: ignore[name-defined]
    specifications: Mapped[list["Specification"]] = relationship("Specification", back_populates="project")  # type: ignore[name-defined]
    takeoff_items: Mapped[list["TakeoffItem"]] = relationship("TakeoffItem", back_populates="project")  # type: ignore[name-defined]
    bids: Mapped[list["Bid"]] = relationship("Bid", back_populates="project")  # type: ignore[name-defined]
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project")
    milestones: Mapped[list["Milestone"]] = relationship("Milestone", back_populates="project")
    submittals: Mapped[list["Submittal"]] = relationship("Submittal", back_populates="project")  # type: ignore[name-defined]
    closeout_docs: Mapped[list["CloseoutDocument"]] = relationship("CloseoutDocument", back_populates="project")  # type: ignore[name-defined]
    equipment: Mapped[list["Equipment"]] = relationship("Equipment", back_populates="project")  # type: ignore[name-defined]


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")  # type: ignore[name-defined]


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default=TaskStatus.open, index=True)
    priority: Mapped[str] = mapped_column(String(50), default=TaskPriority.medium)
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship("Project", back_populates="tasks")


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship("Project", back_populates="milestones")

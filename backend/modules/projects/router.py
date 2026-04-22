from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from datetime import date

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError, ForbiddenError
from models.user import User
from models.project import Project, ProjectMember, Task, Milestone, ProjectStatus, ProjectType

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    project_number: str | None = None
    project_type: str = ProjectType.commercial
    address: str | None = None
    city: str | None = None
    state: str | None = None
    description: str | None = None
    bid_due_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    project_number: str | None = None
    status: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    description: str | None = None
    bid_due_date: date | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    due_date: date | None = None
    assignee_id: int | None = None


@router.get("/")
async def list_projects(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Project).where(Project.org_id == current_user.org_id)
    if status:
        q = q.where(Project.status == status)
    q = q.order_by(Project.updated_at.desc())
    result = await db.execute(q)
    projects = result.scalars().all()
    return {"items": [_project_out(p) for p in projects], "total": len(projects)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        org_id=current_user.org_id,
        created_by_id=current_user.id,
        **data.model_dump(exclude_none=True),
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=current_user.id, role="owner"))
    await db.flush()
    return _project_out(project)


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_project_or_404(project_id, current_user.org_id, db)
    return _project_out(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_project_or_404(project_id, current_user.org_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    return _project_out(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_project_or_404(project_id, current_user.org_id, db)
    project.status = ProjectStatus.archived


@router.get("/{project_id}/tasks")
async def list_tasks(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_project_or_404(project_id, current_user.org_id, db)
    result = await db.execute(select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc()))
    return {"items": [t.__dict__ for t in result.scalars().all()]}


@router.post("/{project_id}/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: int,
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_project_or_404(project_id, current_user.org_id, db)
    task = Task(project_id=project_id, **data.model_dump(exclude_none=True))
    db.add(task)
    await db.flush()
    return task.__dict__


async def _get_project_or_404(project_id: int, org_id: int, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project")
    return project


def _project_out(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "project_number": p.project_number,
        "project_type": p.project_type,
        "status": p.status,
        "address": p.address,
        "city": p.city,
        "state": p.state,
        "description": p.description,
        "bid_due_date": p.bid_due_date.isoformat() if p.bid_due_date else None,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }

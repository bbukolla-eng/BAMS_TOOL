import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from core.storage import build_object_key, upload_file
from models.submittal import Submittal, SubmittalItem, SubmittalStatus
from models.user import User

router = APIRouter()


class SubmittalCreate(BaseModel):
    project_id: int
    title: str
    description: str | None = None
    spec_section_ref: str | None = None
    required_date: date | None = None
    equipment_id: int | None = None


class SubmittalUpdate(BaseModel):
    status: str | None = None
    submitted_date: date | None = None
    returned_date: date | None = None
    reviewer_notes: str | None = None
    submitter_notes: str | None = None


class SubmittalItemCreate(BaseModel):
    description: str
    manufacturer: str | None = None
    model_number: str | None = None
    quantity: int | None = None
    notes: str | None = None


@router.get("/project/{project_id}")
async def list_submittals(
    project_id: int,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Submittal).where(Submittal.project_id == project_id)
    if status_filter:
        q = q.where(Submittal.status == status_filter)
    q = q.order_by(Submittal.submittal_number)
    result = await db.execute(q)
    return {"items": [s.__dict__ for s in result.scalars().all()]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_submittal(
    data: SubmittalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Auto-number
    count_result = await db.execute(
        select(Submittal).where(Submittal.project_id == data.project_id)
    )
    count = len(count_result.scalars().all())
    submittal_number = f"{data.project_id:04d}-{count + 1:03d}"

    submittal = Submittal(
        submittal_number=submittal_number,
        created_by_id=current_user.id,
        **data.model_dump(exclude_none=True),
    )
    db.add(submittal)
    await db.flush()
    return submittal.__dict__


@router.patch("/{submittal_id}")
async def update_submittal(
    submittal_id: int,
    data: SubmittalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Submittal).where(Submittal.id == submittal_id))
    submittal = result.scalar_one_or_none()
    if not submittal:
        raise NotFoundError("Submittal")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(submittal, field, value)
    if data.status == SubmittalStatus.revise_resubmit:
        submittal.revision += 1
    return submittal.__dict__


@router.post("/{submittal_id}/upload")
async def upload_submittal_doc(
    submittal_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Submittal).where(Submittal.id == submittal_id))
    submittal = result.scalar_one_or_none()
    if not submittal:
        raise NotFoundError("Submittal")
    content = await file.read()
    import os
    ext = os.path.splitext(file.filename)[1]
    key = build_object_key(submittal.project_id, "submittals", f"sub_{submittal_id}_r{submittal.revision}_{uuid.uuid4()}{ext}")
    upload_file(content, key, file.content_type or "application/octet-stream")
    submittal.file_path = key
    return {"file_path": key}


@router.post("/{submittal_id}/items", status_code=status.HTTP_201_CREATED)
async def add_submittal_item(
    submittal_id: int,
    data: SubmittalItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = SubmittalItem(submittal_id=submittal_id, **data.model_dump(exclude_none=True))
    db.add(item)
    await db.flush()
    return item.__dict__

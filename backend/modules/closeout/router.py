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
from core.utils import _row, _rows
from models.closeout import CloseoutDocument
from models.user import User

router = APIRouter()


class CloseoutCreate(BaseModel):
    project_id: int
    doc_type: str
    title: str
    description: str | None = None
    equipment_id: int | None = None
    warranty_duration_months: int | None = None
    warranty_start_date: date | None = None
    warranty_provider: str | None = None


class CloseoutUpdate(BaseModel):
    is_received: bool | None = None
    received_date: date | None = None
    notes: str | None = None
    warranty_expiry_date: date | None = None


@router.get("/project/{project_id}")
async def list_closeout_docs(
    project_id: int,
    doc_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(CloseoutDocument).where(CloseoutDocument.project_id == project_id)
    if doc_type:
        q = q.where(CloseoutDocument.doc_type == doc_type)
    q = q.order_by(CloseoutDocument.doc_type, CloseoutDocument.title)
    result = await db.execute(q)
    docs = result.scalars().all()

    # Status summary by type
    summary = {}
    for doc in docs:
        t = doc.doc_type
        if t not in summary:
            summary[t] = {"total": 0, "received": 0}
        summary[t]["total"] += 1
        if doc.is_received:
            summary[t]["received"] += 1

    return {"items": _rows(docs), "summary": summary}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_closeout_doc(
    data: CloseoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import arrow
    doc = CloseoutDocument(created_by_id=current_user.id, **data.model_dump(exclude_none=True))
    if data.warranty_start_date and data.warranty_duration_months:
        doc.warranty_expiry_date = arrow.get(data.warranty_start_date).shift(months=data.warranty_duration_months).date()
    db.add(doc)
    await db.flush()
    return _row(doc)


@router.patch("/{doc_id}")
async def update_closeout_doc(
    doc_id: int,
    data: CloseoutUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(CloseoutDocument).where(CloseoutDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Closeout document")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    return _row(doc)


@router.post("/{doc_id}/upload")
async def upload_closeout_file(
    doc_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(CloseoutDocument).where(CloseoutDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Closeout document")
    import os
    content = await file.read()
    ext = os.path.splitext(file.filename)[1]
    key = build_object_key(doc.project_id, "closeout", f"doc_{doc_id}_{uuid.uuid4()}{ext}")
    upload_file(content, key, file.content_type or "application/octet-stream")
    doc.file_path = key
    doc.is_received = True
    import arrow
    doc.received_date = arrow.now().date()
    return {"file_path": key}

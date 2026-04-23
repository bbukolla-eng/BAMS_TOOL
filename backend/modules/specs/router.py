import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from core.storage import build_object_key, upload_file
from core.utils import _rows
from models.specification import SpecDrawingLink, Specification, SpecSection
from models.user import User

router = APIRouter()


class SpecDrawingLinkCreate(BaseModel):
    spec_section_id: int
    symbol_id: int | None = None
    material_run_id: int | None = None
    notes: str | None = None


@router.get("/project/{project_id}")
async def list_specs(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Specification).where(Specification.project_id == project_id).order_by(Specification.created_at.desc())
    )
    return {"items": [_spec_out(s) for s in result.scalars().all()]}


@router.post("/project/{project_id}", status_code=status.HTTP_202_ACCEPTED)
async def upload_spec(
    project_id: int,
    file: UploadFile = File(...),
    name: str = Form(None),
    division: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os
    content = await file.read()
    object_key = build_object_key(project_id, "specs", f"{uuid.uuid4()}.pdf")
    upload_file(content, object_key, "application/pdf")

    spec = Specification(
        project_id=project_id,
        name=name or os.path.splitext(file.filename)[0],
        file_path=object_key,
        original_filename=file.filename,
        division=division,
        uploaded_by_id=current_user.id,
    )
    db.add(spec)
    await db.flush()

    task_id = None
    try:
        from workers.process_spec import process_spec_task
        task = process_spec_task.delay(spec.id, object_key)
        task_id = task.id
        spec.celery_task_id = task_id
        spec.processing_status = "processing"
    except Exception:
        import asyncio
        spec.processing_status = "processing"
        await db.commit()

        async def _run_inline():
            from workers.process_spec import _process_spec_async
            try:
                await _process_spec_async(spec.id, object_key)
            except Exception:
                from sqlalchemy import select

                from core.database import AsyncSessionLocal
                from models.specification import Specification
                async with AsyncSessionLocal() as s:
                    r = await s.execute(select(Specification).where(Specification.id == spec.id))
                    sp = r.scalar_one_or_none()
                    if sp:
                        sp.processing_status = "error"
                    await s.commit()

        asyncio.create_task(_run_inline())

    return {"id": spec.id, "task_id": task_id, "status": "processing"}


@router.get("/{spec_id}")
async def get_spec(
    spec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    spec = await _get_spec_or_404(spec_id, db)
    return _spec_out(spec)


@router.get("/{spec_id}/sections")
async def list_sections(
    spec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SpecSection).where(SpecSection.specification_id == spec_id).order_by(SpecSection.section_number)
    )
    sections = result.scalars().all()
    return {"items": [_section_out(s) for s in sections]}


@router.get("/{spec_id}/sections/{section_id}/links")
async def get_section_drawing_links(
    spec_id: int,
    section_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SpecDrawingLink).where(SpecDrawingLink.spec_section_id == section_id)
    )
    return {"items": _rows(result.scalars().all())}


@router.post("/links", status_code=status.HTTP_201_CREATED)
async def create_drawing_link(
    data: SpecDrawingLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = SpecDrawingLink(
        spec_section_id=data.spec_section_id,
        symbol_id=data.symbol_id,
        material_run_id=data.material_run_id,
        match_type="manual",
        notes=data.notes,
        match_score=1.0,
    )
    db.add(link)
    await db.flush()
    return {"id": link.id}


@router.post("/{spec_id}/find-matches")
async def find_drawing_matches(
    spec_id: int,
    section_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from modules.specs.service import find_spec_drawing_matches
    matches = await find_spec_drawing_matches(spec_id, section_id, db)
    return {"matches": matches}


async def _get_spec_or_404(spec_id: int, db: AsyncSession) -> Specification:
    result = await db.execute(select(Specification).where(Specification.id == spec_id))
    spec = result.scalar_one_or_none()
    if not spec:
        raise NotFoundError("Specification")
    return spec


def _spec_out(s: Specification) -> dict:
    return {
        "id": s.id,
        "project_id": s.project_id,
        "name": s.name,
        "original_filename": s.original_filename,
        "division": s.division,
        "processing_status": s.processing_status,
        "created_at": s.created_at.isoformat(),
    }


def _section_out(s: SpecSection) -> dict:
    import json
    return {
        "id": s.id,
        "specification_id": s.specification_id,
        "section_number": s.section_number,
        "section_title": s.section_title,
        "structured_data": json.loads(s.structured_data) if s.structured_data else None,
        "page_start": s.page_start,
        "page_end": s.page_end,
    }

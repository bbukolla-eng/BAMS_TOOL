import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from core.storage import upload_file, get_presigned_url, build_object_key
from models.user import User
from models.drawing import Drawing, DrawingPage, Symbol, MaterialRun, DrawingMarkup, DrawingDiscipline
from pydantic import BaseModel

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".dxf", ".dwg", ".png", ".jpg", ".jpeg", ".tiff"}


@router.get("/project/{project_id}")
async def list_drawings(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Drawing).where(Drawing.project_id == project_id).order_by(Drawing.created_at.desc())
    )
    drawings = result.scalars().all()
    return {"items": [_drawing_out(d) for d in drawings]}


@router.post("/project/{project_id}", status_code=status.HTTP_202_ACCEPTED)
async def upload_drawing(
    project_id: int,
    file: UploadFile = File(...),
    discipline: str = Form(DrawingDiscipline.mechanical),
    name: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        from fastapi import HTTPException
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    object_key = build_object_key(project_id, "drawings", f"{uuid.uuid4()}{ext}")
    upload_file(content, object_key, file.content_type or "application/octet-stream")

    drawing = Drawing(
        project_id=project_id,
        name=name or os.path.splitext(file.filename)[0],
        discipline=discipline,
        file_path=object_key,
        original_filename=file.filename,
        file_type=ext.lstrip("."),
        file_size_bytes=len(content),
        uploaded_by_id=current_user.id,
    )
    db.add(drawing)
    await db.flush()

    # Attempt async dispatch; fall back to inline processing when no worker is available
    task_id = None
    try:
        from workers.process_drawing import process_drawing_task
        task = process_drawing_task.delay(drawing.id, object_key, ext.lstrip("."))
        task_id = task.id
        drawing.celery_task_id = task_id
        drawing.processing_status = "processing"
    except Exception:
        # No Celery worker — run synchronously in a background thread
        import asyncio, concurrent.futures
        drawing.processing_status = "processing"
        await db.commit()

        async def _run_inline():
            from workers.process_drawing import _run_pipeline
            await _run_pipeline(drawing.id, object_key, ext.lstrip("."))

        asyncio.create_task(_run_inline())

    return {"id": drawing.id, "task_id": task_id, "status": "processing"}


@router.get("/{drawing_id}")
async def get_drawing(
    drawing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drawing = await _get_drawing_or_404(drawing_id, db)
    return _drawing_out(drawing)


@router.get("/{drawing_id}/pages")
async def list_pages(
    drawing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DrawingPage).where(DrawingPage.drawing_id == drawing_id).order_by(DrawingPage.page_number)
    )
    pages = result.scalars().all()
    return {"items": [_page_out(p) for p in pages]}


@router.get("/{drawing_id}/pages/{page_number}/symbols")
async def get_symbols(
    drawing_id: int,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    page_result = await db.execute(
        select(DrawingPage).where(
            DrawingPage.drawing_id == drawing_id,
            DrawingPage.page_number == page_number,
        )
    )
    page = page_result.scalar_one_or_none()
    if not page:
        raise NotFoundError("Drawing page")

    sym_result = await db.execute(select(Symbol).where(Symbol.page_id == page.id))
    run_result = await db.execute(select(MaterialRun).where(MaterialRun.page_id == page.id))

    return {
        "symbols": [s.__dict__ for s in sym_result.scalars().all()],
        "material_runs": [r.__dict__ for r in run_result.scalars().all()],
    }


@router.get("/{drawing_id}/url")
async def get_drawing_url(
    drawing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drawing = await _get_drawing_or_404(drawing_id, db)
    url = get_presigned_url(drawing.file_path, expires_seconds=3600)
    return {"url": url, "expires_in": 3600}


@router.post("/{drawing_id}/markup")
async def save_markup(
    drawing_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    markup = DrawingMarkup(
        drawing_id=drawing_id,
        page_number=data.get("page_number", 1),
        markup_type=data.get("markup_type", "callout"),
        data=data.get("data", {}),
        color=data.get("color"),
        label=data.get("label"),
        created_by_id=current_user.id,
    )
    db.add(markup)
    await db.flush()
    return {"id": markup.id}


async def _get_drawing_or_404(drawing_id: int, db: AsyncSession) -> Drawing:
    result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise NotFoundError("Drawing")
    return drawing


def _drawing_out(d: Drawing) -> dict:
    return {
        "id": d.id,
        "project_id": d.project_id,
        "name": d.name,
        "sheet_number": d.sheet_number,
        "discipline": d.discipline,
        "original_filename": d.original_filename,
        "file_type": d.file_type,
        "file_size_bytes": d.file_size_bytes,
        "page_count": d.page_count,
        "processing_status": d.processing_status,
        "processing_error": d.processing_error,
        "created_at": d.created_at.isoformat(),
    }


def _page_out(p: DrawingPage) -> dict:
    return {
        "id": p.id,
        "drawing_id": p.drawing_id,
        "page_number": p.page_number,
        "width_px": p.width_px,
        "height_px": p.height_px,
        "width_ft": p.width_ft,
        "height_ft": p.height_ft,
        "scale_factor": p.scale_factor,
        "scale_label": p.scale_label,
        "processing_status": p.processing_status,
        "tile_manifest_path": p.tile_manifest_path,
    }

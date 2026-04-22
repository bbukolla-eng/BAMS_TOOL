from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from models.user import User
from models.drawing import Drawing, Symbol, MaterialRun
from models.learning import FeedbackEvent
from pydantic import BaseModel

router = APIRouter()


class SymbolCorrection(BaseModel):
    symbol_id: int
    correct_type: str
    notes: str | None = None


class RunCorrection(BaseModel):
    run_id: int
    correct_length_ft: float | None = None
    correct_material_type: str | None = None
    notes: str | None = None


class ReprocessRequest(BaseModel):
    drawing_id: int
    page_numbers: list[int] | None = None


@router.post("/reprocess")
async def reprocess_drawing(
    data: ReprocessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Drawing).where(Drawing.id == data.drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise NotFoundError("Drawing")

    from workers.process_drawing import process_drawing_task
    task = process_drawing_task.delay(drawing.id, drawing.file_path, drawing.file_type)
    drawing.celery_task_id = task.id
    drawing.processing_status = "processing"
    return {"task_id": task.id, "status": "processing"}


@router.post("/correct-symbol")
async def correct_symbol(
    data: SymbolCorrection,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Symbol).where(Symbol.id == data.symbol_id))
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise NotFoundError("Symbol")

    before = {"symbol_type": symbol.symbol_type}
    symbol.symbol_type = data.correct_type
    symbol.is_verified = True
    symbol.verified_by_id = current_user.id

    feedback = FeedbackEvent(
        user_id=current_user.id,
        event_type="symbol_correction",
        entity_type="symbol",
        entity_id=data.symbol_id,
        before_state=before,
        after_state={"symbol_type": data.correct_type},
    )
    db.add(feedback)
    return {"status": "corrected", "symbol_id": data.symbol_id}


@router.post("/correct-run")
async def correct_run(
    data: RunCorrection,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(MaterialRun).where(MaterialRun.id == data.run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundError("Material run")

    before = {"length_ft": run.length_ft, "material_type": run.material_type}
    if data.correct_length_ft is not None:
        run.length_ft = data.correct_length_ft
    if data.correct_material_type is not None:
        run.material_type = data.correct_material_type
    run.is_verified = True
    run.verified_by_id = current_user.id

    feedback = FeedbackEvent(
        user_id=current_user.id,
        event_type="run_correction",
        entity_type="material_run",
        entity_id=data.run_id,
        before_state=before,
        after_state={"length_ft": run.length_ft, "material_type": run.material_type},
    )
    db.add(feedback)
    return {"status": "corrected", "run_id": data.run_id}


@router.get("/job-status/{task_id}")
async def get_job_status(task_id: str, current_user: User = Depends(get_current_user)):
    from core.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@router.get("/accuracy-report")
async def get_accuracy_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from models.learning import MLTrainingJob
    result = await db.execute(
        select(MLTrainingJob).order_by(MLTrainingJob.created_at.desc()).limit(10)
    )
    jobs = result.scalars().all()
    return {"training_jobs": [j.__dict__ for j in jobs]}

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from models.user import User
from models.takeoff import TakeoffItem

router = APIRouter()


class TakeoffItemCreate(BaseModel):
    description: str
    category: str
    csi_code: str | None = None
    system: str | None = None
    quantity: float
    unit: str
    waste_factor: float = 0.05
    unit_material_cost: float | None = None
    unit_labor_hours: float | None = None
    # Aliases accepted from frontend / AI pipeline
    material_unit_cost: float | None = None
    labor_hours_per_unit: float | None = None
    confidence: float = 1.0
    notes: str | None = None


class TakeoffItemUpdate(BaseModel):
    quantity: float | None = None
    unit_material_cost: float | None = None
    unit_labor_hours: float | None = None
    notes: str | None = None
    is_locked: bool | None = None


@router.get("/project/{project_id}")
async def list_takeoff(
    project_id: int,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(TakeoffItem).where(TakeoffItem.project_id == project_id)
    if category:
        q = q.where(TakeoffItem.category == category)
    q = q.order_by(TakeoffItem.category, TakeoffItem.description)
    result = await db.execute(q)
    items = result.scalars().all()

    summary: dict = {}
    for item in items:
        cat = item.category
        if cat not in summary:
            summary[cat] = {"count": 0, "material_total": 0.0, "labor_hours": 0.0}
        summary[cat]["count"] += 1
        summary[cat]["material_total"] += item.material_total or 0.0
        summary[cat]["labor_hours"] += item.labor_total or 0.0

    return {"items": [_item_out(i) for i in items], "summary": summary, "total": len(items)}


@router.post("/project/{project_id}", status_code=status.HTTP_201_CREATED)
async def create_takeoff_item(
    project_id: int,
    data: TakeoffItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve aliased field names
    mat_cost = data.unit_material_cost or data.material_unit_cost
    labor_hrs = data.unit_labor_hours or data.labor_hours_per_unit
    adj_qty = data.quantity * (1 + data.waste_factor)

    item = TakeoffItem(
        project_id=project_id,
        description=data.description,
        category=data.category,
        csi_code=data.csi_code,
        system=data.system,
        quantity=data.quantity,
        unit=data.unit,
        waste_factor=data.waste_factor,
        adjusted_quantity=adj_qty,
        unit_material_cost=mat_cost,
        unit_labor_hours=labor_hrs,
        material_total=(mat_cost or 0) * adj_qty,
        labor_total=(labor_hrs or 0) * adj_qty,
        confidence=data.confidence,
        notes=data.notes,
    )
    db.add(item)
    await db.flush()
    return _item_out(item)


@router.patch("/{item_id}")
async def update_takeoff_item(
    item_id: int,
    data: TakeoffItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(TakeoffItem).where(TakeoffItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundError("Takeoff item")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)

    if data.quantity is not None:
        item.adjusted_quantity = data.quantity * (1 + (item.waste_factor or 0.05))
        item.is_locked = True

    if item.unit_material_cost and item.adjusted_quantity:
        item.material_total = item.unit_material_cost * item.adjusted_quantity
    if item.unit_labor_hours and item.adjusted_quantity:
        item.labor_total = item.unit_labor_hours * item.adjusted_quantity

    return _item_out(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_takeoff_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(TakeoffItem).where(TakeoffItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundError("Takeoff item")
    await db.delete(item)


@router.post("/project/{project_id}/regenerate")
async def regenerate_takeoff(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        from workers.run_takeoff import run_takeoff_task
        task = run_takeoff_task.delay(project_id)
        return {"task_id": task.id, "status": "processing"}
    except Exception as exc:
        return {"task_id": None, "status": "error", "detail": str(exc)}


def _item_out(i: TakeoffItem) -> dict:
    return {
        "id": i.id,
        "project_id": i.project_id,
        "category": i.category,
        "description": i.description,
        "csi_code": i.csi_code,
        "system": i.system,
        "quantity": i.quantity,
        "unit": i.unit,
        "waste_factor": i.waste_factor,
        "adjusted_quantity": i.adjusted_quantity,
        "unit_material_cost": i.unit_material_cost,
        "unit_labor_hours": i.unit_labor_hours,
        "material_total": i.material_total,
        "labor_total": i.labor_total,
        "confidence": i.confidence,
        "is_locked": i.is_locked,
        "notes": i.notes,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }

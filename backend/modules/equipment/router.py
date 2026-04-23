from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from models.equipment import Equipment
from models.user import User

router = APIRouter()


class EquipmentCreate(BaseModel):
    project_id: int
    trade_id: int | None = None
    tag: str | None = None
    equipment_type: str
    description: str
    csi_code: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    specifications: dict | None = None
    location_description: str | None = None
    floor: str | None = None
    room: str | None = None
    drawing_id: int | None = None
    drawing_coordinates: dict | None = None
    notes: str | None = None


class EquipmentUpdate(BaseModel):
    tag: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    serial_number: str | None = None
    specifications: dict | None = None
    location_description: str | None = None
    floor: str | None = None
    room: str | None = None
    is_approved: bool | None = None
    is_installed: bool | None = None
    notes: str | None = None


@router.get("/project/{project_id}")
async def list_equipment(
    project_id: int,
    equipment_type: str | None = None,
    is_installed: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Equipment).where(Equipment.project_id == project_id)
    if equipment_type:
        q = q.where(Equipment.equipment_type == equipment_type)
    if is_installed is not None:
        q = q.where(Equipment.is_installed == is_installed)
    q = q.order_by(Equipment.equipment_type, Equipment.tag)
    result = await db.execute(q)
    items = result.scalars().all()

    # Summary by type
    summary = {}
    for item in items:
        t = item.equipment_type
        if t not in summary:
            summary[t] = {"total": 0, "approved": 0, "installed": 0}
        summary[t]["total"] += 1
        if item.is_approved:
            summary[t]["approved"] += 1
        if item.is_installed:
            summary[t]["installed"] += 1

    return {"items": [_eq_out(i) for i in items], "summary": summary}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_equipment(
    data: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    eq = Equipment(created_by_id=current_user.id, **data.model_dump(exclude_none=True))
    db.add(eq)
    await db.flush()
    return _eq_out(eq)


@router.get("/{equipment_id}")
async def get_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Equipment).where(Equipment.id == equipment_id))
    eq = result.scalar_one_or_none()
    if not eq:
        raise NotFoundError("Equipment")
    return _eq_out(eq)


@router.patch("/{equipment_id}")
async def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Equipment).where(Equipment.id == equipment_id))
    eq = result.scalar_one_or_none()
    if not eq:
        raise NotFoundError("Equipment")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(eq, field, value)
    return _eq_out(eq)


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Equipment).where(Equipment.id == equipment_id))
    eq = result.scalar_one_or_none()
    if not eq:
        raise NotFoundError("Equipment")
    await db.delete(eq)


def _eq_out(e: Equipment) -> dict:
    return {
        "id": e.id,
        "project_id": e.project_id,
        "tag": e.tag,
        "equipment_type": e.equipment_type,
        "description": e.description,
        "csi_code": e.csi_code,
        "manufacturer": e.manufacturer,
        "model_number": e.model_number,
        "serial_number": e.serial_number,
        "specifications": e.specifications,
        "location_description": e.location_description,
        "floor": e.floor,
        "room": e.room,
        "drawing_id": e.drawing_id,
        "drawing_coordinates": e.drawing_coordinates,
        "is_approved": e.is_approved,
        "is_installed": e.is_installed,
        "notes": e.notes,
        "created_at": e.created_at.isoformat(),
    }

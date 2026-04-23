from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from models.price_book import LaborAssembly, PriceBookItem
from models.user import User

router = APIRouter()


class PriceBookItemCreate(BaseModel):
    trade_id: int | None = None
    csi_code: str | None = None
    category: str
    description: str
    manufacturer: str | None = None
    model_number: str | None = None
    size: str | None = None
    unit: str
    material_unit_cost: float = 0.0
    labor_hours_per_unit: float = 0.0
    notes: str | None = None


class PriceBookItemUpdate(BaseModel):
    material_unit_cost: float | None = None
    labor_hours_per_unit: float | None = None
    description: str | None = None
    notes: str | None = None


class LaborAssemblyCreate(BaseModel):
    trade_id: int | None = None
    name: str
    description: str | None = None
    unit_of_measure: str
    hours_per_unit: float


@router.get("/")
async def list_items(
    category: str | None = None,
    search: str | None = None,
    trade_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(PriceBookItem).where(
        PriceBookItem.org_id == current_user.org_id,
        PriceBookItem.is_active.is_(True),
    )
    if category:
        q = q.where(PriceBookItem.category == category)
    if trade_id:
        q = q.where(PriceBookItem.trade_id == trade_id)
    if search:
        q = q.where(
            or_(
                PriceBookItem.description.ilike(f"%{search}%"),
                PriceBookItem.csi_code.ilike(f"%{search}%"),
            )
        )
    q = q.order_by(PriceBookItem.category, PriceBookItem.description)
    result = await db.execute(q)
    items = result.scalars().all()
    return {"items": [i.__dict__ for i in items], "total": len(items)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    data: PriceBookItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = PriceBookItem(org_id=current_user.org_id, **data.model_dump(exclude_none=True))
    db.add(item)
    await db.flush()
    return item.__dict__


@router.patch("/{item_id}")
async def update_item(
    item_id: int,
    data: PriceBookItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PriceBookItem).where(
            PriceBookItem.id == item_id,
            PriceBookItem.org_id == current_user.org_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundError("Price book item")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    return item.__dict__


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PriceBookItem).where(
            PriceBookItem.id == item_id,
            PriceBookItem.org_id == current_user.org_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundError("Price book item")
    item.is_active = False


@router.post("/import-excel")
async def import_from_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    import io

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb.active
    created = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        item = PriceBookItem(
            org_id=current_user.org_id,
            category=str(row[0] or ""),
            description=str(row[1] or ""),
            unit=str(row[2] or "EA"),
            material_unit_cost=float(row[3] or 0),
            labor_hours_per_unit=float(row[4] or 0),
            csi_code=str(row[5]) if row[5] else None,
            size=str(row[6]) if row[6] else None,
        )
        db.add(item)
        created += 1
    return {"imported": created}


@router.get("/labor-assemblies")
async def list_labor_assemblies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LaborAssembly).where(LaborAssembly.org_id == current_user.org_id, LaborAssembly.is_active.is_(True))
    )
    return {"items": [a.__dict__ for a in result.scalars().all()]}


@router.post("/labor-assemblies", status_code=status.HTTP_201_CREATED)
async def create_labor_assembly(
    data: LaborAssemblyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assembly = LaborAssembly(org_id=current_user.org_id, **data.model_dump(exclude_none=True))
    db.add(assembly)
    await db.flush()
    return assembly.__dict__

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from models.user import User
from models.bid import Bid, BidLineItem, BidSummarySection, BidStatus
from models.overhead import OverheadConfig
from models.takeoff import TakeoffItem

router = APIRouter()


class BidCreate(BaseModel):
    project_id: int
    name: str = "Bid v1"
    overhead_config_id: int | None = None
    notes: str | None = None


class BidLineItemCreate(BaseModel):
    description: str
    category: str | None = None
    system: str | None = None
    quantity: float
    unit: str
    unit_material_cost: float = 0.0
    unit_labor_hours: float = 0.0
    labor_rate: float = 0.0
    takeoff_item_id: int | None = None
    trade_id: int | None = None
    notes: str | None = None


@router.get("/project/{project_id}")
async def list_bids(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Bid).where(Bid.project_id == project_id).order_by(Bid.version.desc())
    )
    return {"items": [_bid_out(b) for b in result.scalars().all()]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_bid(
    data: BidCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get next version for this project
    result = await db.execute(select(Bid).where(Bid.project_id == data.project_id).order_by(Bid.version.desc()).limit(1))
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    bid = Bid(
        version=version,
        created_by_id=current_user.id,
        **data.model_dump(exclude_none=True),
    )
    db.add(bid)
    await db.flush()
    return _bid_out(bid)


@router.post("/{bid_id}/import-takeoff")
async def import_takeoff_to_bid(
    bid_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bid = await _get_bid_or_404(bid_id, db)
    takeoff_result = await db.execute(
        select(TakeoffItem).where(TakeoffItem.project_id == bid.project_id)
    )
    items = takeoff_result.scalars().all()

    for i, item in enumerate(items):
        line = BidLineItem(
            bid_id=bid_id,
            takeoff_item_id=item.id,
            description=item.description,
            category=item.category,
            system=item.system,
            quantity=item.adjusted_quantity,
            unit=item.unit,
            unit_material_cost=item.unit_material_cost or 0,
            unit_labor_hours=item.unit_labor_hours or 0,
            material_total=(item.unit_material_cost or 0) * item.adjusted_quantity,
            labor_total=(item.unit_labor_hours or 0) * item.adjusted_quantity,
            line_total=((item.unit_material_cost or 0) + (item.unit_labor_hours or 0)) * item.adjusted_quantity,
            sort_order=i,
        )
        db.add(line)

    await _recalculate_bid(bid, db)
    return _bid_out(bid)


@router.get("/{bid_id}")
async def get_bid(
    bid_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bid = await _get_bid_or_404(bid_id, db)
    lines_result = await db.execute(select(BidLineItem).where(BidLineItem.bid_id == bid_id).order_by(BidLineItem.sort_order))
    lines = lines_result.scalars().all()
    out = _bid_out(bid)
    out["line_items"] = [l.__dict__ for l in lines]
    return out


@router.post("/{bid_id}/line-items", status_code=status.HTTP_201_CREATED)
async def add_line_item(
    bid_id: int,
    data: BidLineItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bid = await _get_bid_or_404(bid_id, db)
    mat_total = data.unit_material_cost * data.quantity
    labor_total = data.unit_labor_hours * data.labor_rate * data.quantity
    line = BidLineItem(
        bid_id=bid_id,
        material_total=mat_total,
        labor_total=labor_total,
        line_total=mat_total + labor_total,
        **data.model_dump(exclude_none=True),
    )
    db.add(line)
    await db.flush()
    await _recalculate_bid(bid, db)
    return line.__dict__


class BidCalculateParams(BaseModel):
    overhead_config_id: int | None = None
    labor_rate: float | None = None


@router.post("/{bid_id}/calculate")
async def calculate_bid(
    bid_id: int,
    params: BidCalculateParams | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bid = await _get_bid_or_404(bid_id, db)
    if params:
        if params.overhead_config_id is not None:
            bid.overhead_config_id = params.overhead_config_id
        if params.labor_rate is not None:
            # Recompute labor_total on all line items with new rate
            lines_result = await db.execute(select(BidLineItem).where(BidLineItem.bid_id == bid_id))
            for line in lines_result.scalars().all():
                line.labor_rate = params.labor_rate
                line.labor_total = line.unit_labor_hours * params.labor_rate * line.quantity
                line.line_total = line.material_total + line.labor_total
    await _recalculate_bid(bid, db)
    return _bid_out(bid)


@router.get("/{bid_id}/export/excel")
async def export_bid_excel(
    bid_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from modules.bidding.exporter import export_to_excel
    bid = await _get_bid_or_404(bid_id, db)
    lines_result = await db.execute(select(BidLineItem).where(BidLineItem.bid_id == bid_id).order_by(BidLineItem.sort_order))
    lines = lines_result.scalars().all()
    content = export_to_excel(bid, lines)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=bid_{bid_id}_v{bid.version}.xlsx"},
    )


async def _recalculate_bid(bid: Bid, db: AsyncSession) -> None:
    lines_result = await db.execute(select(BidLineItem).where(BidLineItem.bid_id == bid.id))
    lines = lines_result.scalars().all()

    bid.total_material_cost = sum(l.material_total for l in lines)
    bid.total_labor_hours = sum(l.unit_labor_hours * l.quantity for l in lines if l.unit_labor_hours)
    bid.total_labor_cost = sum(l.labor_total for l in lines)

    config = None
    if bid.overhead_config_id:
        cfg_result = await db.execute(select(OverheadConfig).where(OverheadConfig.id == bid.overhead_config_id))
        config = cfg_result.scalar_one_or_none()

    if config:
        bid.total_burden = bid.total_labor_cost * config.total_burden_rate
        bid.total_material_markup = bid.total_material_cost * config.material_markup
        bid.total_overhead = (bid.total_material_cost + bid.total_labor_cost + bid.total_burden) * config.general_overhead_rate
        bid.subtotal = bid.total_material_cost + bid.total_material_markup + bid.total_labor_cost + bid.total_burden + bid.total_overhead
        bid.contingency = bid.subtotal * config.contingency_rate
        bid.bond = bid.subtotal * config.bond_rate
        bid.permit = bid.subtotal * config.permit_rate
        bid.profit = (bid.subtotal + bid.contingency + bid.bond + bid.permit) * config.profit_margin
        bid.grand_total = bid.subtotal + bid.contingency + bid.bond + bid.permit + bid.profit
    else:
        bid.subtotal = bid.total_material_cost + bid.total_labor_cost
        bid.grand_total = bid.subtotal

    await db.flush()
    await db.refresh(bid)


async def _get_bid_or_404(bid_id: int, db: AsyncSession) -> Bid:
    result = await db.execute(select(Bid).where(Bid.id == bid_id))
    bid = result.scalar_one_or_none()
    if not bid:
        raise NotFoundError("Bid")
    return bid


def _bid_out(b: Bid) -> dict:
    return {
        "id": b.id,
        "project_id": b.project_id,
        "name": b.name,
        "version": b.version,
        "status": b.status,
        "total_material_cost": b.total_material_cost,
        "total_labor_hours": b.total_labor_hours,
        "total_labor_cost": b.total_labor_cost,
        "total_burden": b.total_burden,
        "total_overhead": b.total_overhead,
        "total_material_markup": b.total_material_markup,
        "subtotal": b.subtotal,
        "contingency": b.contingency,
        "bond": b.bond,
        "permit": b.permit,
        "profit": b.profit,
        "grand_total": b.grand_total,
        "notes": b.notes,
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat(),
    }

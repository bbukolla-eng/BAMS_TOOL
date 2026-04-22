from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from models.user import User
from models.overhead import OverheadConfig

router = APIRouter()


class OverheadCreate(BaseModel):
    name: str = "Default"
    fica_rate: float = 0.0765
    futa_rate: float = 0.006
    suta_rate: float = 0.027
    workers_comp_rate: float = 0.12
    general_liability_rate: float = 0.015
    health_insurance_rate: float = 0.08
    vacation_rate: float = 0.05
    general_overhead_rate: float = 0.10
    small_tools_rate: float = 0.02
    material_markup: float = 0.10
    profit_margin: float = 0.08
    contingency_rate: float = 0.03
    bond_rate: float = 0.015
    permit_rate: float = 0.01
    is_default: bool = False


@router.get("/")
async def list_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(OverheadConfig).where(OverheadConfig.org_id == current_user.org_id).order_by(OverheadConfig.is_default.desc())
    )
    return {"items": [c.__dict__ for c in result.scalars().all()]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_config(
    data: OverheadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    burden = (
        data.fica_rate + data.futa_rate + data.suta_rate + data.workers_comp_rate
        + data.general_liability_rate + data.health_insurance_rate + data.vacation_rate
    )
    config = OverheadConfig(
        org_id=current_user.org_id,
        total_burden_rate=burden,
        **data.model_dump(exclude_none=True),
    )
    db.add(config)
    await db.flush()
    return config.__dict__


@router.patch("/{config_id}")
async def update_config(
    config_id: int,
    data: OverheadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(OverheadConfig).where(OverheadConfig.id == config_id, OverheadConfig.org_id == current_user.org_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError("Overhead config")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(config, field, value)

    config.total_burden_rate = (
        data.fica_rate + data.futa_rate + data.suta_rate + data.workers_comp_rate
        + data.general_liability_rate + data.health_insurance_rate + data.vacation_rate
    )
    return config.__dict__


@router.post("/{config_id}/calculate")
async def calculate_overhead(
    config_id: int,
    material_cost: float,
    labor_hours: float,
    labor_rate: float,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OverheadConfig).where(OverheadConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError("Overhead config")

    raw_labor = labor_hours * labor_rate
    burden = raw_labor * config.total_burden_rate
    mat_markup = material_cost * config.material_markup
    overhead = (material_cost + raw_labor + burden) * config.general_overhead_rate
    small_tools = raw_labor * config.small_tools_rate
    subtotal = material_cost + mat_markup + raw_labor + burden + overhead + small_tools
    contingency = subtotal * config.contingency_rate
    bond = subtotal * config.bond_rate
    permit = subtotal * config.permit_rate
    profit = (subtotal + contingency + bond + permit) * config.profit_margin
    grand_total = subtotal + contingency + bond + permit + profit

    return {
        "material_cost": material_cost,
        "material_markup": mat_markup,
        "raw_labor": raw_labor,
        "burden": burden,
        "overhead": overhead,
        "small_tools": small_tools,
        "subtotal": subtotal,
        "contingency": contingency,
        "bond": bond,
        "permit": permit,
        "profit": profit,
        "grand_total": grand_total,
    }

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from core.utils import _row, _rows
from models.trade import Trade
from models.user import User

router = APIRouter()


class TradeCreate(BaseModel):
    name: str
    code: str
    division: str | None = None
    description: str | None = None
    base_labor_rate: float = 0.0
    foreman_rate: float = 0.0
    is_primary: bool = False


class TradeUpdate(BaseModel):
    name: str | None = None
    base_labor_rate: float | None = None
    foreman_rate: float | None = None
    description: str | None = None
    is_active: bool | None = None


@router.get("/")
async def list_trades(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Trade).where(Trade.org_id == current_user.org_id, Trade.is_active.is_(True)).order_by(Trade.is_primary.desc(), Trade.name)
    )
    return {"items": _rows(result.scalars().all())}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_trade(
    data: TradeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trade = Trade(org_id=current_user.org_id, **data.model_dump(exclude_none=True))
    db.add(trade)
    await db.flush()
    return _row(trade)


@router.patch("/{trade_id}")
async def update_trade(
    trade_id: int,
    data: TradeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.org_id == current_user.org_id)
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise NotFoundError("Trade")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(trade, field, value)
    return _row(trade)

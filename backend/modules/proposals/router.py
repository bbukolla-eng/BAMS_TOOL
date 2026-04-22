from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from models.user import User
from models.proposal import Proposal, ProposalStatus

router = APIRouter()


class ProposalCreate(BaseModel):
    project_id: int
    bid_id: int | None = None
    title: str
    client_name: str | None = None
    client_address: str | None = None
    attention_to: str | None = None
    project_description: str | None = None
    scope_of_work: str | None = None
    inclusions: str | None = None
    exclusions: str | None = None
    clarifications: str | None = None
    terms_conditions: str | None = None
    validity_days: int = 30


@router.get("/project/{project_id}")
async def list_proposals(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Proposal).where(Proposal.project_id == project_id).order_by(Proposal.created_at.desc())
    )
    return {"items": [p.__dict__ for p in result.scalars().all()]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_proposal(
    data: ProposalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import arrow
    expiry = arrow.now().shift(days=data.validity_days).date()
    proposal = Proposal(
        created_by_id=current_user.id,
        expiry_date=expiry,
        **data.model_dump(exclude_none=True),
    )
    db.add(proposal)
    await db.flush()
    return proposal.__dict__


@router.get("/{proposal_id}")
async def get_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise NotFoundError("Proposal")
    return proposal.__dict__


@router.get("/{proposal_id}/export/pdf")
async def export_proposal_pdf(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from modules.proposals.generator import generate_proposal_pdf
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise NotFoundError("Proposal")
    content = await generate_proposal_pdf(proposal, db)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=proposal_{proposal_id}.pdf"},
    )

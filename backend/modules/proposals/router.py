
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from core.exceptions import NotFoundError
from core.utils import _row, _rows
from models.proposal import Proposal, ProposalStatus
from models.user import User

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
    return {"items": _rows(result.scalars().all())}


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
    return _row(proposal)


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
    return _row(proposal)


@router.post("/{proposal_id}/ai-scope")
async def ai_fill_scope(
    proposal_id: int,
    overwrite: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Use Claude (with takeoff + spec context) to fill empty Scope of Work,
    Inclusions, Exclusions, and Clarifications fields. Existing manual text
    is preserved unless `overwrite=true`."""
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise NotFoundError("Proposal")
    if overwrite:
        for f in ("scope_of_work", "inclusions", "exclusions", "clarifications"):
            setattr(proposal, f, None)
    from modules.proposals.ai_scope import write_proposal_text_into
    applied = await write_proposal_text_into(proposal, db)
    await db.flush()
    return {"applied_fields": list(applied.keys()), "proposal": _row(proposal)}


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


class ProposalSendRequest(BaseModel):
    to_email: EmailStr
    cc_email: EmailStr | None = None
    custom_message: str | None = None


@router.post("/{proposal_id}/send")
async def send_proposal(
    proposal_id: int,
    data: ProposalSendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Email the proposal PDF to the client."""
    from core.email import proposal_html, send_email
    from modules.proposals.generator import generate_proposal_pdf

    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise NotFoundError("Proposal")

    pdf_bytes = await generate_proposal_pdf(proposal, db)
    filename = f"proposal_{proposal.proposal_number or proposal_id}.pdf"

    recipients = [data.to_email]
    if data.cc_email:
        recipients.append(data.cc_email)

    subject = f"Proposal: {proposal.title}"
    if proposal.proposal_number:
        subject = f"[{proposal.proposal_number}] {proposal.title}"

    html_body = proposal_html(proposal)
    if data.custom_message:
        html_body = html_body.replace(
            "Please find attached",
            f"{data.custom_message}<br><br>Please find attached",
        )

    sent = await send_email(
        to=recipients,
        subject=subject,
        body_html=html_body,
        attachments=[(pdf_bytes, filename, "application/pdf")],
    )

    if not sent:
        raise HTTPException(
            status_code=503,
            detail="SMTP is not configured. Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in your .env file.",
        )

    proposal.status = ProposalStatus.sent
    return {"sent": True, "to": recipients, "filename": filename}

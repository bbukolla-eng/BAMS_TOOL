"""Celery task for async proposal PDF generation."""
import logging

from core.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.generate_proposal.generate_proposal_task")
def generate_proposal_task(self, proposal_id: int):
    import asyncio
    asyncio.run(_generate_async(proposal_id))
    return {"status": "done", "proposal_id": proposal_id}


async def _generate_async(proposal_id: int):
    from sqlalchemy import select

    from core.database import AsyncSessionLocal
    from core.storage import build_object_key, upload_file
    from models.proposal import Proposal
    from modules.proposals.generator import generate_proposal_pdf

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
        proposal = result.scalar_one_or_none()
        if not proposal:
            return

        content = await generate_proposal_pdf(proposal, db)
        key = build_object_key(proposal.project_id, "proposals", f"proposal_{proposal_id}.pdf")
        upload_file(content, key, "application/pdf")
        proposal.file_path = key
        await db.commit()
    log.info(f"Proposal {proposal_id} PDF generated")

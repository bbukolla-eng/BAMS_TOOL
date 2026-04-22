"""Celery task for spec document processing."""
import logging
import json
from celery import shared_task
from core.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="workers.process_spec.process_spec_task")
def process_spec_task(self, spec_id: int, file_path: str):
    import asyncio
    try:
        asyncio.run(_process_spec_async(spec_id, file_path))
        return {"status": "done", "spec_id": spec_id}
    except Exception as exc:
        log.error(f"Spec {spec_id} processing failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


async def _process_spec_async(spec_id: int, file_path: str):
    from core.storage import download_file
    from core.database import AsyncSessionLocal
    from models.specification import Specification, SpecSection
    from ai.spec_parser import extract_spec_sections, analyze_section_with_claude, generate_embeddings, classify_spec_division
    from sqlalchemy import select

    file_bytes = download_file(file_path)

    # Detect division
    import pdfplumber, io
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        first_text = pdf.pages[0].extract_text() if pdf.pages else ""

    import os
    filename = os.path.basename(file_path)
    division = await classify_spec_division(filename, first_text)

    # Extract sections
    sections = extract_spec_sections(file_bytes)
    log.info(f"Spec {spec_id}: found {len(sections)} sections")

    async with AsyncSessionLocal() as db:
        # Update spec division
        spec_result = await db.execute(select(Specification).where(Specification.id == spec_id))
        spec = spec_result.scalar_one_or_none()
        if spec:
            spec.division = division

        # Process each section
        for section_data in sections:
            # Get structured data from Claude
            structured = await analyze_section_with_claude(section_data)

            # Generate embedding
            embed_text = f"{section_data.section_number} {section_data.section_title}\n{section_data.raw_text[:1000]}"
            embedding = await generate_embeddings(embed_text)

            sec = SpecSection(
                specification_id=spec_id,
                section_number=section_data.section_number,
                section_title=section_data.section_title,
                raw_text=section_data.raw_text,
                structured_data=json.dumps(structured) if structured else None,
                embedding=embedding if embedding else None,
                page_start=section_data.page_start,
                page_end=section_data.page_end,
            )
            db.add(sec)

        if spec:
            spec.processing_status = "done"

        await db.commit()
    log.info(f"Spec {spec_id} processed successfully")

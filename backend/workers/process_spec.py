"""Celery task for spec document processing."""
import json
import logging

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
        if self.request.retries >= self.max_retries:
            # Permanent failure — mark spec as error
            asyncio.run(_update_spec_status(spec_id, "error", str(exc)))
        raise self.retry(exc=exc, countdown=30) from exc


async def _process_spec_async(spec_id: int, file_path: str):
    from sqlalchemy import select

    from ai.spec_parser import (
        analyze_section_with_claude,
        classify_spec_division,
        extract_spec_sections,
        generate_embeddings,
    )
    from core.database import AsyncSessionLocal
    from core.storage import download_file
    from models.specification import Specification, SpecSection

    await _publish_spec_progress(spec_id, "downloading", 5)
    file_bytes = download_file(file_path)

    # Detect division
    await _publish_spec_progress(spec_id, "classifying", 15)
    import io

    import pdfplumber
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        first_text = pdf.pages[0].extract_text() if pdf.pages else ""

    import os
    filename = os.path.basename(file_path)
    division = await classify_spec_division(filename, first_text)

    # Extract sections
    await _publish_spec_progress(spec_id, "extracting_sections", 30)
    sections = extract_spec_sections(file_bytes)
    log.info(f"Spec {spec_id}: found {len(sections)} sections")

    async with AsyncSessionLocal() as db:
        # Update spec division
        spec_result = await db.execute(select(Specification).where(Specification.id == spec_id))
        spec = spec_result.scalar_one_or_none()
        if spec:
            spec.division = division

        total = len(sections)
        for idx, section_data in enumerate(sections):
            pct = 30 + int((idx / max(total, 1)) * 55)
            await _publish_spec_progress(spec_id, "analyzing_sections", pct,
                                         f"Section {idx + 1}/{total}: {section_data.section_title or ''}")

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

    await _publish_spec_progress(spec_id, "done", 100)
    log.info(f"Spec {spec_id} processed successfully")


async def _publish_spec_progress(spec_id: int, stage: str, pct: int, message: str | None = None):
    _stage_messages = {
        "downloading": "Downloading file",
        "classifying": "Detecting CSI division",
        "extracting_sections": "Extracting sections",
        "analyzing_sections": "Analyzing with AI",
        "done": "Complete",
        "error": "Processing failed",
    }
    try:
        from core.redis_client import publish_job_progress, set_job_status
        data = {
            "stage": stage,
            "pct": pct,
            "message": message or _stage_messages.get(stage, stage.replace("_", " ")),
        }
        await publish_job_progress(f"spec:{spec_id}", data)
        if stage in ("done", "error"):
            await set_job_status(f"spec:{spec_id}", data)
    except Exception:
        pass


async def _update_spec_status(spec_id: int, status: str, error: str | None = None):
    from sqlalchemy import select

    from core.database import AsyncSessionLocal
    from models.specification import Specification
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Specification).where(Specification.id == spec_id))
            spec = result.scalar_one_or_none()
            if spec:
                spec.processing_status = status
                await db.commit()
        await _publish_spec_progress(spec_id, "error", 0, error)
    except Exception:
        pass

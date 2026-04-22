"""
Celery task chain for drawing processing.
Step 1: Download from storage
Step 2: Convert DWG→DXF if needed
Step 3: Extract geometry
Step 4: Detect symbols
Step 5: Trace material runs
Step 6: Generate page tiles
Step 7: Save results to DB and update drawing status
"""
import logging
from celery import shared_task

from core.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="workers.process_drawing.process_drawing_task")
def process_drawing_task(self, drawing_id: int, file_path: str, file_type: str):
    """Main drawing processing task."""
    import asyncio
    try:
        asyncio.run(_process_drawing_async(self, drawing_id, file_path, file_type))
        return {"status": "done", "drawing_id": drawing_id}
    except Exception as exc:
        log.error(f"Drawing {drawing_id} processing failed: {exc}")
        _update_drawing_status(drawing_id, "error", str(exc))
        raise self.retry(exc=exc, countdown=30)


async def _process_drawing_async(task, drawing_id: int, file_path: str, file_type: str):
    from core.storage import download_file
    from core.database import AsyncSessionLocal
    from models.drawing import Drawing, DrawingPage, Symbol, MaterialRun
    from ai.drawing_analyzer import analyze_drawing

    await _publish_progress(drawing_id, "downloading", 5)

    # Download file
    file_bytes = download_file(file_path)

    # Convert DWG to DXF if needed
    if file_type == "dwg":
        await _publish_progress(drawing_id, "converting_dwg", 15)
        file_bytes = _convert_dwg_to_dxf(file_bytes)
        file_type = "dxf"

    await _publish_progress(drawing_id, "extracting_geometry", 30)

    # Run AI analysis
    results = await analyze_drawing(drawing_id, file_bytes, file_type)

    await _publish_progress(drawing_id, "saving_results", 80)

    async with AsyncSessionLocal() as db:
        for result in results:
            # Upsert DrawingPage
            from sqlalchemy import select
            page_result = await db.execute(
                select(DrawingPage).where(
                    DrawingPage.drawing_id == drawing_id,
                    DrawingPage.page_number == result.page_number,
                )
            )
            page = page_result.scalar_one_or_none()
            if not page:
                page = DrawingPage(drawing_id=drawing_id, page_number=result.page_number)
                db.add(page)
                await db.flush()

            page.width_ft = result.width_ft
            page.height_ft = result.height_ft
            page.scale_factor = result.scale_ft
            page.scale_label = result.scale_label
            page.vector_extracted = True
            page.processing_status = "done"

            # Save symbols
            for sym in result.symbols:
                symbol = Symbol(
                    page_id=page.id,
                    symbol_type=sym["symbol_type"],
                    x=sym["x"],
                    y=sym["y"],
                    width=sym.get("width"),
                    height=sym.get("height"),
                    confidence=sym.get("confidence", 1.0),
                    detection_source=sym.get("detection_source", "rule"),
                    label=sym.get("label"),
                    properties=sym.get("properties"),
                )
                db.add(symbol)

            # Save material runs
            for run in result.material_runs:
                mat_run = MaterialRun(
                    page_id=page.id,
                    material_type=run["material_type"],
                    path=run["path"],
                    length_ft=run["length_ft"],
                    size=run.get("size"),
                    layer_name=run.get("layer_name"),
                    confidence=run.get("confidence", 1.0),
                    detection_source=run.get("detection_source", "vector"),
                )
                db.add(mat_run)

        # Update drawing status
        drawing_result = await db.execute(
            select(Drawing).where(Drawing.id == drawing_id)
        )
        drawing = drawing_result.scalar_one_or_none()
        if drawing:
            drawing.processing_status = "done"
            drawing.page_count = len(results)

        await db.commit()

    await _publish_progress(drawing_id, "done", 100)
    log.info(f"Drawing {drawing_id} processed: {len(results)} pages")


def _convert_dwg_to_dxf(dwg_bytes: bytes) -> bytes:
    """Convert DWG to DXF using ODA File Converter."""
    import subprocess, tempfile, os
    from core.config import settings

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, "input.dwg")
        out_dir = os.path.join(tmpdir, "out")
        os.makedirs(out_dir)

        with open(in_path, "wb") as f:
            f.write(dwg_bytes)

        result = subprocess.run(
            [settings.oda_converter_path, tmpdir, out_dir, "ACAD2018", "DXF", "0", "1"],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ODA converter failed: {result.stderr.decode()}")

        out_file = os.path.join(out_dir, "input.dxf")
        if os.path.exists(out_file):
            with open(out_file, "rb") as f:
                return f.read()

    raise RuntimeError("ODA converter produced no output")


async def _publish_progress(drawing_id: int, stage: str, percent: int):
    try:
        from core.redis_client import publish_job_progress
        await publish_job_progress(f"drawing:{drawing_id}", {"stage": stage, "percent": percent})
    except Exception:
        pass


def _update_drawing_status(drawing_id: int, status: str, error: str | None = None):
    import asyncio
    asyncio.run(_async_update_status(drawing_id, status, error))


async def _async_update_status(drawing_id: int, status: str, error: str | None):
    from core.database import AsyncSessionLocal
    from models.drawing import Drawing
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
        drawing = result.scalar_one_or_none()
        if drawing:
            drawing.processing_status = status
            drawing.processing_error = error
            await db.commit()


async def _run_pipeline(drawing_id: int, file_path: str, file_type: str):
    """Public entry point for inline (non-Celery) processing."""
    try:
        await _process_drawing_async(None, drawing_id, file_path, file_type)
    except Exception as exc:
        log.error(f"Inline drawing processing failed: {exc}")
        await _async_update_status(drawing_id, "error", str(exc))

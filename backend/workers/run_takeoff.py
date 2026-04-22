"""
Celery task to regenerate takeoff from drawing analysis results.
Aggregates symbols and material runs into TakeoffItem rows.
Only updates items that are not locked (is_locked=False).
"""
import logging
from celery import shared_task
from core.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.run_takeoff.run_takeoff_task")
def run_takeoff_task(self, project_id: int):
    import asyncio
    asyncio.run(_run_takeoff_async(project_id))
    return {"status": "done", "project_id": project_id}


async def _run_takeoff_async(project_id: int):
    from core.database import AsyncSessionLocal
    from models.drawing import Drawing, DrawingPage, Symbol, MaterialRun
    from models.takeoff import TakeoffItem
    from models.price_book import PriceBookItem
    from ai.div23.symbols import HVAC_SYMBOLS, MATERIAL_RUN_TYPES
    from sqlalchemy import select, delete

    async with AsyncSessionLocal() as db:
        # Delete non-locked takeoff items for this project
        await db.execute(
            delete(TakeoffItem).where(
                TakeoffItem.project_id == project_id,
                TakeoffItem.is_locked == False,
            )
        )

        # Get all processed drawings for this project
        drawings_result = await db.execute(
            select(Drawing).where(
                Drawing.project_id == project_id,
                Drawing.processing_status == "done",
            )
        )
        drawings = drawings_result.scalars().all()

        symbol_counts: dict[tuple, list[int]] = {}  # (type, size) → [symbol_ids]
        run_totals: dict[tuple, dict] = {}           # (type, size) → {length, run_ids}

        for drawing in drawings:
            pages_result = await db.execute(
                select(DrawingPage).where(DrawingPage.drawing_id == drawing.id)
            )
            pages = pages_result.scalars().all()

            for page in pages:
                # Aggregate symbols
                syms_result = await db.execute(select(Symbol).where(Symbol.page_id == page.id))
                for sym in syms_result.scalars().all():
                    key = (sym.symbol_type, None)
                    if key not in symbol_counts:
                        symbol_counts[key] = []
                    symbol_counts[key].append(sym.id)

                # Aggregate material runs
                runs_result = await db.execute(select(MaterialRun).where(MaterialRun.page_id == page.id))
                for run in runs_result.scalars().all():
                    key = (run.material_type, run.size)
                    if key not in run_totals:
                        run_totals[key] = {"length_ft": 0.0, "run_ids": []}
                    run_totals[key]["length_ft"] += run.length_ft
                    run_totals[key]["run_ids"].append(run.id)

        # Create TakeoffItems for symbol counts
        for (sym_type, _), sym_ids in symbol_counts.items():
            sym_def = HVAC_SYMBOLS.get(sym_type)
            if not sym_def:
                continue

            # Try to match price book
            pb_result = await db.execute(
                select(PriceBookItem).where(
                    PriceBookItem.csi_code == sym_def.csi_code,
                    PriceBookItem.is_active == True,
                ).limit(1)
            )
            pb_item = pb_result.scalar_one_or_none()

            qty = float(len(sym_ids))
            item = TakeoffItem(
                project_id=project_id,
                category=sym_def.category,
                description=sym_def.description,
                csi_code=sym_def.csi_code,
                system=sym_def.system,
                quantity=qty,
                unit=sym_def.unit,
                waste_factor=sym_def.waste_factor,
                adjusted_quantity=qty * (1 + sym_def.waste_factor),
                source_symbol_ids=sym_ids[:100],
                confidence=0.85,
                unit_material_cost=pb_item.material_unit_cost if pb_item else None,
                unit_labor_hours=pb_item.labor_hours_per_unit if pb_item else None,
                price_book_item_id=pb_item.id if pb_item else None,
            )
            if pb_item:
                item.material_total = (pb_item.material_unit_cost or 0) * item.adjusted_quantity
            db.add(item)

        # Create TakeoffItems for material runs
        for (mat_type, size), data in run_totals.items():
            run_def = MATERIAL_RUN_TYPES.get(mat_type)
            if not run_def:
                continue

            description = run_def["description"]
            if size:
                description += f" — {size}"

            pb_result = await db.execute(
                select(PriceBookItem).where(
                    PriceBookItem.csi_code == run_def["csi_code"],
                    PriceBookItem.is_active == True,
                ).limit(1)
            )
            pb_item = pb_result.scalar_one_or_none()

            length = data["length_ft"]
            waste = 0.05
            adj_length = length * (1 + waste)
            item = TakeoffItem(
                project_id=project_id,
                category=run_def["category"],
                description=description,
                csi_code=run_def["csi_code"],
                quantity=length,
                unit="LF",
                waste_factor=waste,
                adjusted_quantity=adj_length,
                source_run_ids=data["run_ids"][:100],
                confidence=0.90,
                unit_material_cost=pb_item.material_unit_cost if pb_item else None,
                unit_labor_hours=pb_item.labor_hours_per_unit if pb_item else None,
                price_book_item_id=pb_item.id if pb_item else None,
            )
            if pb_item:
                item.material_total = (pb_item.material_unit_cost or 0) * adj_length
            db.add(item)

        await db.commit()
    log.info(f"Takeoff generated for project {project_id}: {len(symbol_counts)} symbol types, {len(run_totals)} run types")

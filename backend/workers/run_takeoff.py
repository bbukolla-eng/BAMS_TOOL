"""
Celery task to regenerate takeoff from drawing analysis results.

Pipeline:
  1. Wipe unlocked TakeoffItems for the project (locked rows survive).
  2. Walk every processed Drawing/Page, dedupe equipment across sheets by tag.
  3. Emit one TakeoffItem per (symbol_type, size) tuple, sized from block
     attributes / nearby annotation text where available.
  4. Emit one TakeoffItem per (material_type, size) tuple from material runs.
  5. Emit fitting line items (elbow_45, elbow_90, tee, cross, transition)
     aggregated from the per-run fittings JSON.
  6. Lookup price book by CSI + size where possible — falls back to CSI-only.

Locked items (is_locked=True) are never overwritten.
"""
import logging

from core.celery_app import celery_app

log = logging.getLogger(__name__)


# Map fitting key → (CSI hint, human description, category, waste factor)
FITTING_DEFS: dict[str, dict] = {
    "elbow_45": {
        "category_suffix": "fitting",
        "description": "45° Elbow",
        "csi_hint_duct": "23 31 13",
        "csi_hint_pipe": "23 21 13",
        "waste": 0.0,
    },
    "elbow_90": {
        "category_suffix": "fitting",
        "description": "90° Elbow",
        "csi_hint_duct": "23 31 13",
        "csi_hint_pipe": "23 21 13",
        "waste": 0.0,
    },
    "tee": {
        "category_suffix": "fitting",
        "description": "Tee / Wye",
        "csi_hint_duct": "23 31 13",
        "csi_hint_pipe": "23 21 13",
        "waste": 0.0,
    },
    "cross": {
        "category_suffix": "fitting",
        "description": "Cross",
        "csi_hint_duct": "23 31 13",
        "csi_hint_pipe": "23 21 13",
        "waste": 0.0,
    },
    "transition": {
        "category_suffix": "fitting",
        "description": "Transition / Reducer",
        "csi_hint_duct": "23 31 13",
        "csi_hint_pipe": "23 21 13",
        "waste": 0.0,
    },
}


@celery_app.task(bind=True, name="workers.run_takeoff.run_takeoff_task")
def run_takeoff_task(self, project_id: int):
    import asyncio
    asyncio.run(_run_takeoff_async(project_id))
    return {"status": "done", "project_id": project_id}


def _symbol_size(properties: dict | None) -> str | None:
    """Pick the most informative size hint from a symbol's enriched properties."""
    if not properties:
        return None
    return (
        properties.get("size")
        or properties.get("inlet_size")
        or _capacity_size(properties)
    )


def _capacity_size(properties: dict) -> str | None:
    """Render a capacity number into the size string the catalog uses
    (e.g. ``50 ton``, ``10000 CFM``, ``1000 MBH``, ``200 GPM``)."""
    if (tons := properties.get("tons")):
        return f"{tons:g} ton"
    if (cfm := properties.get("cfm")):
        return f"{cfm:g} CFM"
    if (mbh := properties.get("mbh")):
        return f"{mbh:g} MBH"
    if (gpm := properties.get("gpm")):
        return f"{gpm:g} GPM"
    if (hp := properties.get("hp")):
        return f"{hp:g} HP"
    return None


def _equipment_dedup_key(symbol) -> tuple | None:
    """Return a stable identity key for an equipment instance, so the same
    AHU drawn on a plan + a riser doesn't get counted twice."""
    props = getattr(symbol, "properties", None) or {}
    tag = (props.get("tag") or "").strip()
    if not tag:
        return None
    return (symbol.symbol_type, tag.upper())


async def _lookup_price_book(db, csi_code: str | None, size: str | None):
    """Try size-aware lookup first, then fall back to CSI-only.

    Pricing precision matters: a 10,000-CFM AHU and a 50,000-CFM AHU share a
    CSI code but cost ~6× different.
    """
    from sqlalchemy import select

    from models.price_book import PriceBookItem

    if not csi_code:
        return None
    if size:
        result = await db.execute(
            select(PriceBookItem).where(
                PriceBookItem.csi_code == csi_code,
                PriceBookItem.size == size,
                PriceBookItem.is_active.is_(True),
            ).limit(1)
        )
        item = result.scalar_one_or_none()
        if item:
            return item
    result = await db.execute(
        select(PriceBookItem).where(
            PriceBookItem.csi_code == csi_code,
            PriceBookItem.is_active.is_(True),
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def _run_takeoff_async(project_id: int):
    from sqlalchemy import delete, select, update

    from ai.div23.symbols import HVAC_SYMBOLS, MATERIAL_RUN_TYPES
    from core.database import AsyncSessionLocal
    from models.bid import BidLineItem
    from models.drawing import Drawing, DrawingPage, MaterialRun, Symbol
    from models.takeoff import TakeoffItem

    async with AsyncSessionLocal() as db:
        # Detach unlocked takeoff rows from any bid line items first.
        unlocked_ids_result = await db.execute(
            select(TakeoffItem.id).where(
                TakeoffItem.project_id == project_id,
                TakeoffItem.is_locked.is_(False),
            )
        )
        unlocked_ids = [row[0] for row in unlocked_ids_result.fetchall()]
        if unlocked_ids:
            await db.execute(
                update(BidLineItem)
                .where(BidLineItem.takeoff_item_id.in_(unlocked_ids))
                .values(takeoff_item_id=None)
            )
        await db.execute(
            delete(TakeoffItem).where(
                TakeoffItem.project_id == project_id,
                TakeoffItem.is_locked.is_(False),
            )
        )

        # Pull all processed drawings + pages.
        drawings_result = await db.execute(
            select(Drawing).where(
                Drawing.project_id == project_id,
                Drawing.processing_status == "done",
            )
        )
        drawings = drawings_result.scalars().all()

        # Aggregations:
        symbol_counts: dict[tuple, dict] = {}   # (type, size) → {ids: [], dedup_keys: set}
        seen_equipment_keys: set[tuple] = set() # (symbol_type, tag) we've already counted
        run_totals: dict[tuple, dict] = {}      # (type, size) → {length, ids}
        # Fittings keyed by (mat_type, size, fitting_kind) → count
        fitting_totals: dict[tuple, dict] = {}

        for drawing in drawings:
            pages_result = await db.execute(
                select(DrawingPage).where(DrawingPage.drawing_id == drawing.id)
            )
            pages = pages_result.scalars().all()

            for page in pages:
                syms_result = await db.execute(
                    select(Symbol).where(Symbol.page_id == page.id)
                )
                for sym in syms_result.scalars().all():
                    # Multi-page dedup: same equipment tag across sheets is
                    # the same instance, count once.
                    dedup_key = _equipment_dedup_key(sym)
                    if dedup_key:
                        if dedup_key in seen_equipment_keys:
                            continue
                        seen_equipment_keys.add(dedup_key)

                    size = _symbol_size(sym.properties)
                    key = (sym.symbol_type, size)
                    bucket = symbol_counts.setdefault(
                        key, {"ids": [], "tags": set()}
                    )
                    bucket["ids"].append(sym.id)
                    if dedup_key:
                        bucket["tags"].add(dedup_key[1])

                runs_result = await db.execute(
                    select(MaterialRun).where(MaterialRun.page_id == page.id)
                )
                for run in runs_result.scalars().all():
                    run_key = (run.material_type, run.size)
                    rb = run_totals.setdefault(
                        run_key, {"length_ft": 0.0, "run_ids": []}
                    )
                    rb["length_ft"] += run.length_ft
                    rb["run_ids"].append(run.id)

                    if run.fittings:
                        for fkind, count in run.fittings.items():
                            if not count or fkind not in FITTING_DEFS:
                                continue
                            fkey = (run.material_type, run.size, fkind)
                            fb = fitting_totals.setdefault(
                                fkey, {"count": 0, "run_ids": []}
                            )
                            fb["count"] += count
                            fb["run_ids"].append(run.id)

        # ── Symbol takeoff items ─────────────────────────────────────────
        for (sym_type, size), bucket in symbol_counts.items():
            sym_def = HVAC_SYMBOLS.get(sym_type)
            if not sym_def:
                continue

            pb_item = await _lookup_price_book(db, sym_def.csi_code, size)
            qty = float(len(bucket["ids"]))
            description = sym_def.description
            if size:
                description += f" — {size}"

            item = TakeoffItem(
                project_id=project_id,
                category=sym_def.category,
                description=description,
                csi_code=sym_def.csi_code,
                system=sym_def.system,
                quantity=qty,
                unit=sym_def.unit,
                waste_factor=sym_def.waste_factor,
                adjusted_quantity=qty * (1 + sym_def.waste_factor),
                source_symbol_ids=bucket["ids"][:100],
                confidence=0.85,
                unit_material_cost=pb_item.material_unit_cost if pb_item else None,
                unit_labor_hours=pb_item.labor_hours_per_unit if pb_item else None,
                price_book_item_id=pb_item.id if pb_item else None,
            )
            if pb_item and pb_item.material_unit_cost:
                item.material_total = pb_item.material_unit_cost * item.adjusted_quantity
            db.add(item)

        # ── Material run takeoff items ───────────────────────────────────
        for (mat_type, size), data in run_totals.items():
            run_def = MATERIAL_RUN_TYPES.get(mat_type)
            if not run_def:
                continue

            description = run_def["description"]
            if size:
                description += f" — {size}"

            pb_item = await _lookup_price_book(db, run_def["csi_code"], size)

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
            if pb_item and pb_item.material_unit_cost:
                item.material_total = pb_item.material_unit_cost * adj_length
            db.add(item)

        # ── Fitting takeoff items ────────────────────────────────────────
        for (mat_type, size, fkind), data in fitting_totals.items():
            count = data["count"]
            if count <= 0:
                continue
            fdef = FITTING_DEFS[fkind]
            base_desc = fdef["description"]
            kind = "Pipe" if "pipe" in mat_type else "Duct"
            csi_hint = fdef["csi_hint_pipe"] if kind == "Pipe" else fdef["csi_hint_duct"]
            description = f"{kind} {base_desc}"
            if size:
                description += f" — {size}"

            pb_item = await _lookup_price_book(db, csi_hint, size)
            adj_qty = count * (1 + fdef["waste"])
            item = TakeoffItem(
                project_id=project_id,
                category=f"{kind.lower()}_{fdef['category_suffix']}",
                description=description,
                csi_code=csi_hint,
                quantity=float(count),
                unit="EA",
                waste_factor=fdef["waste"],
                adjusted_quantity=float(adj_qty),
                source_run_ids=data["run_ids"][:100],
                confidence=0.80,
                unit_material_cost=pb_item.material_unit_cost if pb_item else None,
                unit_labor_hours=pb_item.labor_hours_per_unit if pb_item else None,
                price_book_item_id=pb_item.id if pb_item else None,
            )
            if pb_item and pb_item.material_unit_cost:
                item.material_total = pb_item.material_unit_cost * adj_qty
            db.add(item)

        await db.commit()

    log.info(
        "Takeoff for project %s: %s symbol groups, %s run groups, %s fitting groups, %s deduped tags",
        project_id, len(symbol_counts), len(run_totals), len(fitting_totals),
        len(seen_equipment_keys),
    )

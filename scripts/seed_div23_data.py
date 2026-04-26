"""
Seed script: Division 23 trade, price book skeleton, labor assemblies,
and default overhead config.

Pricing intentionally NOT seeded with values — costs and labor hours are
left at 0.0 with notes flags so they show up as PRICE_PENDING in the bid
pipeline. Real pricing comes from manufacturer blue books / line lists,
ingested via:

    make import-prices file=path/to/manufacturer.csv

Run: python scripts/seed_div23_data.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.overhead import OverheadConfig
from models.price_book import LaborAssembly, PriceBookItem
from models.trade import Trade
from models.user import Organization
from seeds.division_23_assemblies import ASSEMBLIES
from seeds.division_23_catalog import CATALOG_ITEMS


async def _ensure_org(db) -> Organization | None:
    result = await db.execute(select(Organization).limit(1))
    org = result.scalar_one_or_none()
    if not org:
        print("No organization found. Run seed_users.py first.")
        return None
    return org


async def _ensure_mech_trade(db, org_id: int) -> Trade:
    result = await db.execute(
        select(Trade).where(Trade.code == "MECH", Trade.org_id == org_id)
    )
    mech = result.scalar_one_or_none()
    if mech:
        print(f"Mechanical trade already exists (id={mech.id})")
        return mech
    mech = Trade(
        org_id=org_id,
        name="Mechanical (Division 23)",
        code="MECH",
        division="23",
        description="HVAC and Mechanical Systems — Primary Trade",
        base_labor_rate=0.0,  # populated from local agreement / shop rate
        foreman_rate=0.0,
        is_primary=True,
    )
    db.add(mech)
    await db.flush()
    print(f"Created Mechanical trade (id={mech.id})")
    return mech


async def _seed_price_book(db, org_id: int, trade_id: int) -> tuple[int, int]:
    created = 0
    skipped = 0
    for entry in CATALOG_ITEMS:
        existing = await db.execute(
            select(PriceBookItem).where(
                PriceBookItem.org_id == org_id,
                PriceBookItem.description == entry["description"],
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        item = PriceBookItem(
            org_id=org_id,
            trade_id=trade_id,
            csi_code=entry.get("csi_code"),
            category=entry["category"],
            description=entry["description"],
            size=entry.get("size"),
            unit=entry["unit"],
            manufacturer=entry.get("manufacturer"),
            model_number=entry.get("model_number"),
            material_unit_cost=0.0,
            labor_hours_per_unit=0.0,
            notes=entry.get("notes"),
        )
        db.add(item)
        created += 1
    return created, skipped


async def _seed_assemblies(db, org_id: int, trade_id: int) -> tuple[int, int]:
    created = 0
    skipped = 0
    for entry in ASSEMBLIES:
        existing = await db.execute(
            select(LaborAssembly).where(
                LaborAssembly.org_id == org_id,
                LaborAssembly.name == entry["name"],
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        assembly = LaborAssembly(
            org_id=org_id,
            trade_id=trade_id,
            name=entry["name"],
            description=entry["description"],
            unit_of_measure=entry["unit_of_measure"],
            hours_per_unit=0.0,
        )
        db.add(assembly)
        created += 1
    return created, skipped


async def _seed_overhead(db, org_id: int) -> bool:
    result = await db.execute(
        select(OverheadConfig).where(
            OverheadConfig.org_id == org_id, OverheadConfig.is_default.is_(True)
        )
    )
    if result.scalar_one_or_none():
        return False
    overhead = OverheadConfig(
        org_id=org_id,
        name="Standard Mechanical",
        is_default=True,
        # Statutory burdens (US federal/state — adjust per locality)
        fica_rate=0.0765,
        futa_rate=0.006,
        suta_rate=0.027,
        workers_comp_rate=0.12,
        general_liability_rate=0.015,
        health_insurance_rate=0.08,
        vacation_rate=0.05,
        total_burden_rate=0.375,
        # Markups (replace with shop's actuals)
        general_overhead_rate=0.10,
        small_tools_rate=0.02,
        material_markup=0.10,
        profit_margin=0.08,
        contingency_rate=0.03,
        bond_rate=0.015,
        permit_rate=0.01,
    )
    db.add(overhead)
    return True


async def seed():
    async with AsyncSessionLocal() as db:
        org = await _ensure_org(db)
        if not org:
            return
        org_id = org.id

        mech = await _ensure_mech_trade(db, org_id)

        pb_created, pb_skipped = await _seed_price_book(db, org_id, mech.id)
        as_created, as_skipped = await _seed_assemblies(db, org_id, mech.id)
        oh_created = await _seed_overhead(db, org_id)

        await db.commit()

        print(f"Price book items   — created: {pb_created}, skipped (existed): {pb_skipped}")
        print(f"Labor assemblies   — created: {as_created}, skipped (existed): {as_skipped}")
        print(f"Default overhead   — {'created' if oh_created else 'already existed'}")
        print()
        print(f"  ▸ {pb_created} price book items seeded with PRICE_PENDING_BLUE_BOOK")
        print(f"  ▸ {as_created} labor assemblies seeded with HOURS_PENDING_HISTORICAL_DATA")
        print()
        print("Populate pricing from manufacturer line lists with:")
        print("    make import-prices file=path/to/manufacturer.csv")


if __name__ == "__main__":
    asyncio.run(seed())

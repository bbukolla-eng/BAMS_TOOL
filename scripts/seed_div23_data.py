"""
Seed script: Division 23 HVAC trades and price book data.
Run: python scripts/seed_div23_data.py
"""
import asyncio
import sys
sys.path.insert(0, "backend")

from core.database import AsyncSessionLocal
from models.user import Organization
from models.trade import Trade
from models.price_book import PriceBookItem, LaborAssembly
from models.overhead import OverheadConfig
from sqlalchemy import select


DIV23_PRICE_BOOK = [
    # ── Ductwork ──────────────────────────────────────────────────────────
    {"csi_code": "23 31 13", "category": "duct", "description": "Rectangular Duct, G-90 Galvanized, 12x8", "unit": "LF", "material_unit_cost": 18.50, "labor_hours_per_unit": 0.25, "size": "12x8"},
    {"csi_code": "23 31 13", "category": "duct", "description": "Rectangular Duct, G-90 Galvanized, 24x12", "unit": "LF", "material_unit_cost": 32.00, "labor_hours_per_unit": 0.35, "size": "24x12"},
    {"csi_code": "23 31 13", "category": "duct", "description": "Rectangular Duct, G-90 Galvanized, 36x18", "unit": "LF", "material_unit_cost": 52.00, "labor_hours_per_unit": 0.50, "size": "36x18"},
    {"csi_code": "23 31 13", "category": "duct", "description": "Round Spiral Duct, G-90, 6\" Dia", "unit": "LF", "material_unit_cost": 8.50, "labor_hours_per_unit": 0.12, "size": "6\" round"},
    {"csi_code": "23 31 13", "category": "duct", "description": "Round Spiral Duct, G-90, 10\" Dia", "unit": "LF", "material_unit_cost": 14.00, "labor_hours_per_unit": 0.18, "size": "10\" round"},
    {"csi_code": "23 31 13", "category": "duct", "description": "Round Spiral Duct, G-90, 14\" Dia", "unit": "LF", "material_unit_cost": 22.00, "labor_hours_per_unit": 0.25, "size": "14\" round"},
    {"csi_code": "23 31 13", "category": "duct", "description": "Flex Duct, 6\"", "unit": "LF", "material_unit_cost": 2.50, "labor_hours_per_unit": 0.05, "size": "6\""},
    {"csi_code": "23 31 13", "category": "duct", "description": "Flex Duct, 10\"", "unit": "LF", "material_unit_cost": 4.00, "labor_hours_per_unit": 0.07, "size": "10\""},
    {"csi_code": "23 33 13", "category": "damper", "description": "Manual Volume Damper, Rectangular", "unit": "EA", "material_unit_cost": 85.00, "labor_hours_per_unit": 1.0},
    {"csi_code": "23 33 13", "category": "damper", "description": "Motorized Control Damper, 12x12", "unit": "EA", "material_unit_cost": 385.00, "labor_hours_per_unit": 2.5},
    {"csi_code": "23 33 46", "category": "damper", "description": "Fire Damper, Rectangular, 12x12", "unit": "EA", "material_unit_cost": 285.00, "labor_hours_per_unit": 2.0},
    {"csi_code": "23 33 46", "category": "damper", "description": "Combination Fire/Smoke Damper, 12x12", "unit": "EA", "material_unit_cost": 650.00, "labor_hours_per_unit": 3.0},

    # ── Duct Insulation ────────────────────────────────────────────────────
    {"csi_code": "23 07 13", "category": "insulation", "description": "Duct Insulation, Fiberglass, 2\" thick", "unit": "SF", "material_unit_cost": 3.20, "labor_hours_per_unit": 0.04},
    {"csi_code": "23 07 13", "category": "insulation", "description": "Duct Liner, 1\" Fiberglass", "unit": "SF", "material_unit_cost": 2.10, "labor_hours_per_unit": 0.03},

    # ── Piping ─────────────────────────────────────────────────────────────
    {"csi_code": "23 21 13", "category": "pipe", "description": "Black Steel Pipe, Sch 40, 2\" CHW/HHW", "unit": "LF", "material_unit_cost": 14.00, "labor_hours_per_unit": 0.30, "size": "2\""},
    {"csi_code": "23 21 13", "category": "pipe", "description": "Black Steel Pipe, Sch 40, 4\" CHW/HHW", "unit": "LF", "material_unit_cost": 26.00, "labor_hours_per_unit": 0.50, "size": "4\""},
    {"csi_code": "23 21 13", "category": "pipe", "description": "Black Steel Pipe, Sch 40, 6\" CHW/HHW", "unit": "LF", "material_unit_cost": 45.00, "labor_hours_per_unit": 0.75, "size": "6\""},
    {"csi_code": "23 21 13", "category": "pipe", "description": "Black Steel Pipe, Sch 40, 8\" CHW/HHW", "unit": "LF", "material_unit_cost": 68.00, "labor_hours_per_unit": 1.00, "size": "8\""},
    {"csi_code": "23 21 13", "category": "valve", "description": "Ball Valve, 2\", Bronze", "unit": "EA", "material_unit_cost": 145.00, "labor_hours_per_unit": 1.5, "size": "2\""},
    {"csi_code": "23 21 13", "category": "valve", "description": "Ball Valve, 4\", Carbon Steel", "unit": "EA", "material_unit_cost": 485.00, "labor_hours_per_unit": 3.0, "size": "4\""},
    {"csi_code": "23 21 13", "category": "valve", "description": "Butterfly Valve, 6\", Lug Style", "unit": "EA", "material_unit_cost": 380.00, "labor_hours_per_unit": 2.5, "size": "6\""},
    {"csi_code": "23 21 13", "category": "valve", "description": "Circuit Balancing Valve, 2\"", "unit": "EA", "material_unit_cost": 285.00, "labor_hours_per_unit": 1.5, "size": "2\""},

    # ── Pipe Insulation ────────────────────────────────────────────────────
    {"csi_code": "23 07 19", "category": "insulation", "description": "Pipe Insulation, Fiberglass, 2\" pipe, 1\" thick", "unit": "LF", "material_unit_cost": 4.50, "labor_hours_per_unit": 0.08, "size": "2\" pipe"},
    {"csi_code": "23 07 19", "category": "insulation", "description": "Pipe Insulation, Fiberglass, 4\" pipe, 1.5\" thick", "unit": "LF", "material_unit_cost": 7.50, "labor_hours_per_unit": 0.12, "size": "4\" pipe"},

    # ── Air Terminal Units ─────────────────────────────────────────────────
    {"csi_code": "23 36 00", "category": "air_terminal", "description": "VAV Box, Single Duct, 6\" inlet", "unit": "EA", "material_unit_cost": 485.00, "labor_hours_per_unit": 3.0, "size": "6\""},
    {"csi_code": "23 36 00", "category": "air_terminal", "description": "VAV Box, Single Duct, 10\" inlet", "unit": "EA", "material_unit_cost": 685.00, "labor_hours_per_unit": 4.0, "size": "10\""},
    {"csi_code": "23 36 00", "category": "air_terminal", "description": "VAV Box, Single Duct w/ Reheat, 8\" inlet", "unit": "EA", "material_unit_cost": 985.00, "labor_hours_per_unit": 5.0, "size": "8\""},
    {"csi_code": "23 37 13", "category": "diffuser", "description": "Supply Diffuser, 12x12 Louvered Face", "unit": "EA", "material_unit_cost": 65.00, "labor_hours_per_unit": 0.75, "size": "12x12"},
    {"csi_code": "23 37 13", "category": "diffuser", "description": "Supply Diffuser, 24x24 Louvered Face", "unit": "EA", "material_unit_cost": 125.00, "labor_hours_per_unit": 1.0, "size": "24x24"},
    {"csi_code": "23 37 13", "category": "diffuser", "description": "Return Air Grille, 24x24", "unit": "EA", "material_unit_cost": 85.00, "labor_hours_per_unit": 0.75, "size": "24x24"},
    {"csi_code": "23 37 23", "category": "diffuser", "description": "Linear Bar Grille, 48\" x 6\"", "unit": "EA", "material_unit_cost": 145.00, "labor_hours_per_unit": 1.25, "size": "48x6"},

    # ── Equipment ──────────────────────────────────────────────────────────
    {"csi_code": "23 73 13", "category": "equipment", "description": "Air Handling Unit, 10,000 CFM", "unit": "EA", "material_unit_cost": 28500.00, "labor_hours_per_unit": 80.0},
    {"csi_code": "23 82 19", "category": "equipment", "description": "Fan Coil Unit, 400 CFM, 2-pipe", "unit": "EA", "material_unit_cost": 1850.00, "labor_hours_per_unit": 12.0},
    {"csi_code": "23 34 23", "category": "equipment", "description": "Exhaust Fan, Inline, 1,000 CFM", "unit": "EA", "material_unit_cost": 685.00, "labor_hours_per_unit": 6.0},
    {"csi_code": "23 21 23", "category": "equipment", "description": "Centrifugal Pump, Base-Mounted, 50 GPM", "unit": "EA", "material_unit_cost": 4200.00, "labor_hours_per_unit": 24.0},
    {"csi_code": "23 52 16", "category": "equipment", "description": "Hot Water Boiler, 1,000 MBH", "unit": "EA", "material_unit_cost": 22000.00, "labor_hours_per_unit": 60.0},
    {"csi_code": "23 64 16", "category": "equipment", "description": "Air-Cooled Chiller, 50 Ton", "unit": "EA", "material_unit_cost": 75000.00, "labor_hours_per_unit": 120.0},
    {"csi_code": "23 65 00", "category": "equipment", "description": "Cooling Tower, 100 Ton", "unit": "EA", "material_unit_cost": 42000.00, "labor_hours_per_unit": 80.0},
    {"csi_code": "23 09 23", "category": "controls", "description": "Room Thermostat / BAS Sensor", "unit": "EA", "material_unit_cost": 185.00, "labor_hours_per_unit": 2.0},
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Get or create default org
        result = await db.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()
        if not org:
            print("No organization found. Run seed_users.py first.")
            return
        org_id = org.id

        # Seed Division 23 trade
        trade_result = await db.execute(select(Trade).where(Trade.code == "MECH", Trade.org_id == org_id))
        mech_trade = trade_result.scalar_one_or_none()
        if not mech_trade:
            mech_trade = Trade(
                org_id=org_id,
                name="Mechanical (Division 23)",
                code="MECH",
                division="23",
                description="HVAC and Mechanical Systems — Primary Trade",
                base_labor_rate=95.00,
                foreman_rate=115.00,
                is_primary=True,
            )
            db.add(mech_trade)
            await db.flush()
            print(f"Created Mechanical trade (id={mech_trade.id})")
        else:
            print(f"Mechanical trade already exists (id={mech_trade.id})")

        # Seed price book items
        created = 0
        for item_data in DIV23_PRICE_BOOK:
            existing = await db.execute(
                select(PriceBookItem).where(
                    PriceBookItem.org_id == org_id,
                    PriceBookItem.description == item_data["description"],
                )
            )
            if not existing.scalar_one_or_none():
                item = PriceBookItem(
                    org_id=org_id,
                    trade_id=mech_trade.id,
                    **item_data,
                )
                db.add(item)
                created += 1

        # Seed default overhead config
        oh_result = await db.execute(select(OverheadConfig).where(OverheadConfig.org_id == org_id, OverheadConfig.is_default == True))
        if not oh_result.scalar_one_or_none():
            overhead = OverheadConfig(
                org_id=org_id,
                name="Standard Mechanical",
                is_default=True,
                fica_rate=0.0765,
                futa_rate=0.006,
                suta_rate=0.027,
                workers_comp_rate=0.12,
                general_liability_rate=0.015,
                health_insurance_rate=0.08,
                vacation_rate=0.05,
                total_burden_rate=0.375,
                general_overhead_rate=0.10,
                small_tools_rate=0.02,
                material_markup=0.10,
                profit_margin=0.08,
                contingency_rate=0.03,
                bond_rate=0.015,
                permit_rate=0.01,
            )
            db.add(overhead)
            print("Created default overhead config")

        await db.commit()
        print(f"Seeded {created} Division 23 price book items")


if __name__ == "__main__":
    asyncio.run(seed())

"""
Division 23 (HVAC / Mechanical) price book catalog.

Costs and labor hours are intentionally left as None. They must be populated
from manufacturer blue books / distributor line lists via the CSV importer
(scripts/import_price_book.py) or by hand. Items where pricing is missing
get notes="PRICE_PENDING_BLUE_BOOK" so the bid pipeline can flag them.

Suggested sources to populate pricing:
  - Trane / Carrier / Daikin / York / JCI for AHUs, RTUs, chillers, FCUs, VRF
  - Greenheck for fans, louvers, dampers, energy recovery
  - Hart & Cooley / Titus / Krueger / Price for diffusers, grilles, registers
  - Victaulic / Anvil for grooved couplings & fittings
  - Mueller / Cerro / NIBCO for copper pipe and fittings
  - Charlotte / Spears for PVC
  - Apollo / Watts / Bray for valves
  - Armstrong / Bell & Gossett / Taco for pumps
  - Burnham / Lochinvar / Cleaver-Brooks for boilers
  - Owens Corning / Knauf / Johns Manville for insulation
  - RSMeans, BNi, or trade-shop historicals for labor hours
"""

from typing import TypedDict


class CatalogItem(TypedDict, total=False):
    csi_code: str
    category: str
    description: str
    size: str | None
    unit: str
    manufacturer: str | None
    model_number: str | None
    notes: str | None


PRICE_PENDING = "PRICE_PENDING_BLUE_BOOK"


def _item(
    csi_code: str,
    category: str,
    description: str,
    unit: str,
    size: str | None = None,
    manufacturer: str | None = None,
    model_number: str | None = None,
    notes: str | None = None,
) -> CatalogItem:
    return {
        "csi_code": csi_code,
        "category": category,
        "description": description,
        "size": size,
        "unit": unit,
        "manufacturer": manufacturer,
        "model_number": model_number,
        "notes": notes or PRICE_PENDING,
    }


# ── Ductwork — Rectangular Galvanized (G-90, 26 ga unless noted) ──────────────
RECT_DUCT_SIZES = [
    "6x4", "6x6", "8x4", "8x6", "8x8",
    "10x6", "10x8", "10x10",
    "12x6", "12x8", "12x10", "12x12",
    "14x10", "14x12", "14x14",
    "16x10", "16x12", "16x16",
    "18x12", "18x16", "18x18",
    "20x12", "20x16", "20x20",
    "24x12", "24x16", "24x20", "24x24",
    "30x16", "30x20", "30x24",
    "36x18", "36x24", "36x30",
    "42x24", "48x24", "48x36",
    "60x24", "60x36",
]

# ── Ductwork — Round Spiral Galvanized ─────────────────────────────────────────
ROUND_DUCT_SIZES = [
    "4\"", "5\"", "6\"", "7\"", "8\"", "9\"", "10\"",
    "12\"", "14\"", "16\"", "18\"", "20\"",
    "22\"", "24\"", "26\"", "28\"", "30\"",
    "32\"", "36\"", "42\"", "48\"", "54\"", "60\"",
]

# ── Common pipe sizes ──────────────────────────────────────────────────────────
PIPE_STEEL_SIZES = [
    "1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"",
    "2\"", "2-1/2\"", "3\"", "4\"", "5\"",
    "6\"", "8\"", "10\"", "12\"",
]
PIPE_COPPER_SIZES = [
    "1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"",
    "2\"", "2-1/2\"", "3\"", "4\"",
]

DIFFUSER_SIZES_SQUARE = ["6x6", "8x8", "10x10", "12x12", "16x16", "20x20", "24x24"]
DIFFUSER_SIZES_ROUND = ["6\"", "8\"", "10\"", "12\"", "14\""]
RETURN_GRILLE_SIZES = ["12x12", "16x16", "20x20", "24x24", "30x30", "36x36"]
LINEAR_SLOT_LENGTHS = ["24\"", "36\"", "48\"", "60\"", "72\"", "96\""]


def _build_catalog() -> list[CatalogItem]:
    items: list[CatalogItem] = []

    # ── 23 31 13 — Metal Ductwork ─────────────────────────────────────────────
    for s in RECT_DUCT_SIZES:
        items.append(_item("23 31 13", "duct_rectangular",
                           f"Rectangular Duct, G-90 Galvanized 26 ga, {s}",
                           "LF", size=s))
    for s in ROUND_DUCT_SIZES:
        items.append(_item("23 31 13", "duct_round",
                           f"Round Spiral Duct, G-90 Galvanized, {s} dia",
                           "LF", size=s))
    # Flex duct (insulated R-6)
    for s in ["4\"", "6\"", "8\"", "10\"", "12\"", "14\"", "16\""]:
        items.append(_item("23 31 13", "duct_flex",
                           f"Flex Duct, Insulated R-6, {s}", "LF", size=s))
    # Stainless steel kitchen exhaust
    for s in ["12x12", "18x12", "24x18"]:
        items.append(_item("23 31 13", "duct_stainless",
                           f"Stainless Steel Kitchen Exhaust Duct, 16 ga, {s}",
                           "LF", size=s))

    # ── 23 31 13 — Duct Fittings ──────────────────────────────────────────────
    fitting_size_groups = ["small (≤12\")", "medium (14\"-24\")", "large (>24\")"]
    for grp in fitting_size_groups:
        items.append(_item("23 31 13", "duct_fitting",
                           f"Rectangular Duct 90° Elbow, {grp}", "EA", size=grp))
        items.append(_item("23 31 13", "duct_fitting",
                           f"Rectangular Duct 45° Elbow, {grp}", "EA", size=grp))
        items.append(_item("23 31 13", "duct_fitting",
                           f"Rectangular Duct Tee, {grp}", "EA", size=grp))
        items.append(_item("23 31 13", "duct_fitting",
                           f"Rectangular Duct Transition, {grp}", "EA", size=grp))
        items.append(_item("23 31 13", "duct_fitting",
                           f"Round Duct 90° Elbow, {grp}", "EA", size=grp))
        items.append(_item("23 31 13", "duct_fitting",
                           f"Round Duct Tee/Wye, {grp}", "EA", size=grp))
        items.append(_item("23 31 13", "duct_fitting",
                           f"Round Duct Reducer, {grp}", "EA", size=grp))

    # ── 23 33 — Duct Specialties ──────────────────────────────────────────────
    for s in ["8x8", "12x12", "16x16", "24x24", "30x30"]:
        items.append(_item("23 33 13", "damper",
                           f"Manual Volume Damper, Rectangular, {s}", "EA", size=s))
    for s in ["6\"", "10\"", "14\"", "20\""]:
        items.append(_item("23 33 13", "damper",
                           f"Manual Volume Damper, Round, {s}", "EA", size=s))
    for s in ["12x12", "24x24", "36x24"]:
        items.append(_item("23 33 13", "damper",
                           f"Motorized Control Damper, Rectangular, {s}", "EA", size=s))
        items.append(_item("23 33 13", "damper",
                           f"Backdraft Damper, Rectangular, {s}", "EA", size=s))
    for s in ["12x12", "16x16", "24x24", "36x24"]:
        items.append(_item("23 33 46", "damper",
                           f"Fire Damper, Rectangular, 1.5-hr UL, {s}", "EA", size=s))
        items.append(_item("23 33 46", "damper",
                           f"Combination Fire/Smoke Damper, Rectangular, {s}",
                           "EA", size=s))
    for s in ["16x16", "24x24", "36x24"]:
        items.append(_item("23 33 46", "damper",
                           f"Smoke Damper, Rectangular, {s}", "EA", size=s))
    for s in ["24x24", "36x24", "48x36", "72x48"]:
        items.append(_item("23 37 23", "louver",
                           f"Stationary Wall Louver, Extruded Aluminum, {s}",
                           "EA", size=s))

    # ── 23 37 — Air Outlets / Inlets ──────────────────────────────────────────
    for s in DIFFUSER_SIZES_SQUARE:
        items.append(_item("23 37 13", "diffuser",
                           f"Supply Diffuser, Square Louvered Face, {s}", "EA", size=s))
        items.append(_item("23 37 13", "diffuser",
                           f"Supply Diffuser, Plaque Style, {s}", "EA", size=s))
    for s in DIFFUSER_SIZES_ROUND:
        items.append(_item("23 37 13", "diffuser",
                           f"Supply Diffuser, Round Adjustable Pattern, {s}",
                           "EA", size=s))
    for s in LINEAR_SLOT_LENGTHS:
        items.append(_item("23 37 13", "diffuser",
                           f"Linear Slot Diffuser, 1-Slot, {s} long", "EA", size=s))
        items.append(_item("23 37 13", "diffuser",
                           f"Linear Slot Diffuser, 2-Slot, {s} long", "EA", size=s))
    items.append(_item("23 37 23", "grille",
                       "Linear Bar Grille, 0.5\" deflection, 48x6", "EA", size="48x6"))
    items.append(_item("23 37 23", "grille",
                       "Linear Bar Grille, 0.5\" deflection, 72x6", "EA", size="72x6"))
    for s in RETURN_GRILLE_SIZES:
        items.append(_item("23 37 23", "grille",
                           f"Return Air Grille, Lay-In, {s}", "EA", size=s))
        items.append(_item("23 37 23", "grille",
                           f"Eggcrate Return Grille, {s}", "EA", size=s))
    for s in ["10x6", "14x8", "20x10"]:
        items.append(_item("23 37 23", "register",
                           f"Sidewall Supply Register, Double Deflection, {s}",
                           "EA", size=s))
        items.append(_item("23 37 23", "register",
                           f"Sidewall Return Register, {s}", "EA", size=s))

    # ── 23 36 00 — Air Terminal Units (VAV / FPB) ─────────────────────────────
    vav_inlets = ["4\"", "5\"", "6\"", "7\"", "8\"", "10\"", "12\"", "14\"", "16\""]
    for s in vav_inlets:
        items.append(_item("23 36 00", "vav_box",
                           f"VAV Box, Single Duct, Pressure Independent, {s} inlet",
                           "EA", size=s))
        items.append(_item("23 36 00", "vav_box",
                           f"VAV Box w/ Hot Water Reheat, {s} inlet", "EA", size=s))
        items.append(_item("23 36 00", "vav_box",
                           f"VAV Box w/ Electric Reheat, {s} inlet", "EA", size=s))
    for s in ["6\"", "8\"", "10\"", "12\""]:
        items.append(_item("23 36 00", "vav_box",
                           f"Parallel Fan-Powered VAV, {s} inlet", "EA", size=s))
        items.append(_item("23 36 00", "vav_box",
                           f"Series Fan-Powered VAV, {s} inlet", "EA", size=s))

    # ── 23 73 — Air Handling Units ────────────────────────────────────────────
    for cfm in [1000, 2000, 5000, 8000, 10000, 15000, 20000, 30000, 40000, 60000]:
        items.append(_item("23 73 13", "ahu",
                           f"Custom Air Handling Unit, {cfm:,} CFM",
                           "EA", size=f"{cfm} CFM"))
    for tons in [3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 75]:
        items.append(_item("23 74 13", "rtu",
                           f"Packaged Rooftop Unit, DX Cooling + Gas Heat, {tons} ton",
                           "EA", size=f"{tons} ton"))
    for cfm in [500, 1000, 2000, 5000, 10000]:
        items.append(_item("23 72 00", "erv",
                           f"Energy Recovery Ventilator, {cfm:,} CFM",
                           "EA", size=f"{cfm} CFM"))
    for cfm in [1000, 2500, 5000, 10000]:
        items.append(_item("23 74 23", "mau",
                           f"Make-Up Air Unit, Gas-Fired, {cfm:,} CFM",
                           "EA", size=f"{cfm} CFM"))

    # ── 23 34 — Fans ──────────────────────────────────────────────────────────
    for cfm in [250, 500, 1000, 2000, 4000]:
        items.append(_item("23 34 23", "fan",
                           f"Inline Cabinet Fan, Belt Drive, {cfm:,} CFM",
                           "EA", size=f"{cfm} CFM"))
        items.append(_item("23 34 13", "fan",
                           f"Roof Exhaust Fan, Centrifugal, {cfm:,} CFM",
                           "EA", size=f"{cfm} CFM"))
    for cfm in [80, 150, 300, 600]:
        items.append(_item("23 34 13", "fan",
                           f"Ceiling Exhaust Fan (Bathroom), {cfm} CFM",
                           "EA", size=f"{cfm} CFM"))
    for cfm in [800, 1500, 3000]:
        items.append(_item("23 38 13", "fan",
                           f"Kitchen Hood Exhaust Fan, Upblast, {cfm:,} CFM",
                           "EA", size=f"{cfm} CFM"))

    # ── 23 82 19 — Fan Coil Units ─────────────────────────────────────────────
    for cfm in [200, 300, 400, 600, 800, 1000, 1200]:
        items.append(_item("23 82 19", "fcu",
                           f"Fan Coil Unit, 2-pipe, Horizontal, {cfm} CFM",
                           "EA", size=f"{cfm} CFM"))
        items.append(_item("23 82 19", "fcu",
                           f"Fan Coil Unit, 4-pipe, Horizontal, {cfm} CFM",
                           "EA", size=f"{cfm} CFM"))

    # ── 23 21 23 — Pumps ──────────────────────────────────────────────────────
    for gpm in [10, 25, 50]:
        items.append(_item("23 21 23", "pump",
                           f"Inline Circulator Pump, Bronze, {gpm} GPM",
                           "EA", size=f"{gpm} GPM"))
    for gpm in [50, 100, 200, 400, 600, 1000]:
        items.append(_item("23 21 23", "pump",
                           f"Base-Mounted End-Suction Pump, {gpm} GPM",
                           "EA", size=f"{gpm} GPM"))
    items.append(_item("23 21 23", "pump",
                       "Vertical Inline Split-Coupled Pump, 200 GPM",
                       "EA", size="200 GPM"))
    items.append(_item("23 22 23", "pump",
                       "Condensate Transfer Pump w/ Receiver",
                       "EA", size="50 GPH"))

    # ── 23 52 — Boilers ───────────────────────────────────────────────────────
    for mbh in [200, 500, 1000, 2000, 3000, 5000]:
        items.append(_item("23 52 16", "boiler",
                           f"Hot Water Boiler, Condensing, Gas, {mbh:,} MBH",
                           "EA", size=f"{mbh} MBH"))
    for mbh in [500, 1000, 2000, 5000]:
        items.append(_item("23 52 16", "boiler",
                           f"Hot Water Boiler, Non-Condensing, {mbh:,} MBH",
                           "EA", size=f"{mbh} MBH"))
    items.append(_item("23 52 33", "boiler",
                       "Steam Boiler, Firetube, 1,000 MBH", "EA", size="1000 MBH"))
    items.append(_item("23 52 33", "boiler",
                       "Steam Boiler, Firetube, 3,000 MBH", "EA", size="3000 MBH"))

    # ── 23 64 — Chillers ──────────────────────────────────────────────────────
    for tons in [20, 40, 60, 80, 100, 150, 200]:
        items.append(_item("23 64 23", "chiller",
                           f"Air-Cooled Scroll Chiller, {tons} ton",
                           "EA", size=f"{tons} ton"))
    for tons in [150, 200, 300, 400]:
        items.append(_item("23 64 23", "chiller",
                           f"Air-Cooled Screw Chiller, {tons} ton",
                           "EA", size=f"{tons} ton"))
    for tons in [200, 500, 1000, 2000]:
        items.append(_item("23 64 16", "chiller",
                           f"Water-Cooled Centrifugal Chiller, {tons} ton",
                           "EA", size=f"{tons} ton"))
    for tons in [100, 200, 400]:
        items.append(_item("23 64 16", "chiller",
                           f"Water-Cooled Screw Chiller, {tons} ton",
                           "EA", size=f"{tons} ton"))

    # ── 23 65 — Cooling Towers ────────────────────────────────────────────────
    for tons in [50, 100, 200, 500, 1000]:
        items.append(_item("23 65 16", "cooling_tower",
                           f"Open-Circuit Induced-Draft Cooling Tower, {tons} ton",
                           "EA", size=f"{tons} ton"))

    # ── 23 21 13 — Hydronic Piping ────────────────────────────────────────────
    for s in PIPE_STEEL_SIZES:
        items.append(_item("23 21 13", "pipe_steel",
                           f"Black Steel Pipe, Sch 40, {s}, Threaded/Welded",
                           "LF", size=s))
    for s in PIPE_STEEL_SIZES[3:]:  # 1-1/4"+
        items.append(_item("23 21 13", "pipe_steel",
                           f"Black Steel Pipe, Sch 40, {s}, Grooved End",
                           "LF", size=s))
    for s in PIPE_COPPER_SIZES:
        items.append(_item("23 21 13", "pipe_copper",
                           f"Type L Copper Tubing, {s}", "LF", size=s))
    for s in ["3/4\"", "1\"", "1-1/4\"", "1-1/2\""]:
        items.append(_item("23 21 13", "pipe_copper",
                           f"Type K Copper Tubing (underground), {s}", "LF", size=s))
    for s in ["1/2\"", "3/4\"", "1\"", "1-1/4\""]:
        items.append(_item("23 21 13", "pipe_pex",
                           f"PEX Tubing w/ Oxygen Barrier, {s}", "LF", size=s))
    for s in ["3/4\"", "1\"", "1-1/4\""]:
        items.append(_item("23 22 13", "pipe_pvc",
                           f"PVC Sch 40 Condensate Drain, {s}", "LF", size=s))

    # ── Pipe Fittings ─────────────────────────────────────────────────────────
    for s in ["1\"", "2\"", "4\"", "6\""]:
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Steel Pipe 90° Elbow, Sch 40 Welded, {s}",
                           "EA", size=s))
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Steel Pipe 45° Elbow, Sch 40, {s}", "EA", size=s))
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Steel Pipe Tee, {s}", "EA", size=s))
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Steel Pipe Reducer, {s}", "EA", size=s))
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Grooved Coupling (Victaulic-style), {s}",
                           "EA", size=s, manufacturer="Victaulic"))
    for s in ["1/2\"", "1\"", "2\""]:
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Copper 90° Elbow, Wrot, {s}", "EA", size=s))
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Copper Tee, Wrot, {s}", "EA", size=s))
        items.append(_item("23 21 13", "pipe_fitting",
                           f"Copper Coupling, Wrot, {s}", "EA", size=s))

    # ── 23 21 16 — Valves ─────────────────────────────────────────────────────
    for s in ["1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"", "2\""]:
        items.append(_item("23 21 16", "valve_ball",
                           f"Ball Valve, Bronze, Threaded, {s}", "EA", size=s))
    for s in ["2\"", "2-1/2\"", "3\"", "4\"", "6\""]:
        items.append(_item("23 21 16", "valve_ball",
                           f"Ball Valve, Carbon Steel, Flanged, {s}", "EA", size=s))
    for s in ["2\"", "2-1/2\"", "3\"", "4\"", "6\"", "8\"", "10\"", "12\""]:
        items.append(_item("23 21 16", "valve_butterfly",
                           f"Butterfly Valve, Lug, Ductile Iron, {s}", "EA", size=s))
        items.append(_item("23 21 16", "valve_butterfly",
                           f"Butterfly Valve, Wafer, Ductile Iron, {s}", "EA", size=s))
    for s in ["1/2\"", "1\"", "2\"", "4\"", "6\""]:
        items.append(_item("23 21 16", "valve_check",
                           f"Swing Check Valve, {s}", "EA", size=s))
        items.append(_item("23 21 16", "valve_check",
                           f"Silent Check Valve, Spring-Loaded, {s}", "EA", size=s))
    for s in ["1/2\"", "1\"", "2\"", "3\"", "4\""]:
        items.append(_item("23 21 16", "valve_globe",
                           f"Globe Valve, Bronze, {s}", "EA", size=s))
        items.append(_item("23 21 16", "valve_balancing",
                           f"Circuit Balancing Valve, {s}", "EA", size=s))
    for s in ["1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"", "2\""]:
        items.append(_item("23 09 53", "valve_control",
                           f"2-Way Control Valve w/ Actuator, {s}", "EA", size=s))
        items.append(_item("23 09 53", "valve_control",
                           f"3-Way Control Valve w/ Actuator, {s}", "EA", size=s))

    # ── Strainers ─────────────────────────────────────────────────────────────
    for s in ["1\"", "2\"", "4\"", "6\"", "8\""]:
        items.append(_item("23 21 16", "strainer",
                           f"Y-Type Strainer, Bronze/Iron, {s}", "EA", size=s))

    # ── 23 21 19 — Hydronic Specialties ───────────────────────────────────────
    for gal in [5, 15, 30, 60, 100]:
        items.append(_item("23 21 19", "expansion_tank",
                           f"Expansion Tank, Bladder, {gal} gal", "EA", size=f"{gal} gal"))
    for s in ["2\"", "4\"", "6\""]:
        items.append(_item("23 21 19", "air_separator",
                           f"Tangential Air Separator, {s}", "EA", size=s))
    items.append(_item("23 21 19", "glycol_feeder",
                       "Glycol Make-Up Feeder, 50-gal", "EA", size="50 gal"))
    items.append(_item("23 21 19", "prv",
                       "Hydronic Pressure-Reducing Valve", "EA"))
    items.append(_item("23 21 19", "relief_valve",
                       "ASME Pressure Relief Valve, 30 psi", "EA"))

    # ── 23 07 — Insulation ────────────────────────────────────────────────────
    for thk in ["1.5\"", "2\"", "3\""]:
        items.append(_item("23 07 13", "duct_insulation",
                           f"Duct Wrap Fiberglass FSK, {thk}", "SF", size=thk))
    for thk in ["1\"", "1.5\"", "2\""]:
        items.append(_item("23 07 13", "duct_insulation",
                           f"Duct Liner Fiberglass, {thk}", "SF", size=thk))
    for s in ["1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"", "2\""]:
        items.append(_item("23 07 19", "pipe_insulation",
                           f"Pipe Insulation, Fiberglass 1\" thick, {s} pipe",
                           "LF", size=s))
    for s in ["2\"", "3\"", "4\"", "6\"", "8\""]:
        items.append(_item("23 07 19", "pipe_insulation",
                           f"Pipe Insulation, Fiberglass 1.5\" thick, {s} pipe",
                           "LF", size=s))
    for s in ["4\"", "6\"", "8\""]:
        items.append(_item("23 07 19", "pipe_insulation",
                           f"Pipe Insulation, Calcium Silicate 2\" (high-temp), {s} pipe",
                           "LF", size=s))
    items.append(_item("23 07 19", "pipe_jacketing",
                       "PVC Pipe Insulation Jacketing", "LF"))
    items.append(_item("23 07 19", "pipe_jacketing",
                       "Aluminum Pipe Insulation Jacketing", "LF"))

    # ── 23 81 / 23 82 — Refrigerant / VRF ─────────────────────────────────────
    for tons in [6, 8, 10, 14, 18, 24]:
        items.append(_item("23 81 26", "vrf_outdoor",
                           f"VRF Outdoor Heat Pump, {tons} ton",
                           "EA", size=f"{tons} ton"))
    for cfm in [200, 400, 600, 800]:
        items.append(_item("23 81 26", "vrf_indoor",
                           f"VRF Indoor Ceiling Cassette, {cfm} CFM",
                           "EA", size=f"{cfm} CFM"))
        items.append(_item("23 81 26", "vrf_indoor",
                           f"VRF Indoor High-Wall, {cfm} CFM",
                           "EA", size=f"{cfm} CFM"))
    for tons in [1, 1.5, 2, 3, 4]:
        items.append(_item("23 81 23", "minisplit",
                           f"Mini-Split Ductless System, {tons} ton",
                           "EA", size=f"{tons} ton"))
    for s in ["1/4\"", "3/8\"", "1/2\"", "5/8\"", "3/4\"", "7/8\"", "1-1/8\""]:
        items.append(_item("23 23 00", "refrigerant_pipe",
                           f"Refrigerant Copper Tubing (ACR), {s}", "LF", size=s))

    # ── 23 22 — Steam / Condensate ────────────────────────────────────────────
    for s in ["1/2\"", "3/4\"", "1\""]:
        items.append(_item("23 22 23", "steam_trap",
                           f"Float & Thermostatic Steam Trap, {s}", "EA", size=s))
        items.append(_item("23 22 23", "steam_trap",
                           f"Inverted Bucket Steam Trap, {s}", "EA", size=s))
    items.append(_item("23 22 23", "prv_station",
                       "Steam Pressure-Reducing Station w/ Bypass", "EA"))

    # ── 23 09 — Controls / BAS ────────────────────────────────────────────────
    items.append(_item("23 09 13", "controller", "DDC Building Controller", "EA"))
    items.append(_item("23 09 13", "controller", "VAV Zone Controller", "EA"))
    items.append(_item("23 09 13", "controller", "Equipment Unit Controller", "EA"))
    items.append(_item("23 09 23", "sensor", "Room Temperature Sensor w/ Setpoint", "EA"))
    items.append(_item("23 09 23", "sensor", "Duct Temperature Sensor (Averaging)", "EA"))
    items.append(_item("23 09 23", "sensor", "Immersion Temperature Sensor", "EA"))
    items.append(_item("23 09 23", "sensor", "Outdoor Air Temperature Sensor", "EA"))
    items.append(_item("23 09 23", "sensor", "Room Humidity Sensor", "EA"))
    items.append(_item("23 09 23", "sensor", "Room CO2 Sensor", "EA"))
    items.append(_item("23 09 23", "sensor", "Duct Static Pressure Transducer", "EA"))
    items.append(_item("23 09 23", "sensor", "Differential Pressure Switch", "EA"))
    for hp in [1, 3, 5, 10, 25, 50, 100]:
        items.append(_item("23 09 33", "vfd",
                           f"Variable Frequency Drive, {hp} HP", "EA", size=f"{hp} HP"))
    for inlb in ["35 in-lb", "70 in-lb", "150 in-lb", "300 in-lb"]:
        items.append(_item("23 09 33", "actuator",
                           f"Spring-Return Damper Actuator, {inlb}", "EA", size=inlb))
    items.append(_item("23 09 13", "bas_panel", "BAS Field Panel Enclosure", "EA"))

    # ── 23 05 — Equipment Connections / Common Work ───────────────────────────
    items.append(_item("23 05 48", "vibration_iso",
                       "Spring Vibration Isolator, 1\" deflection", "EA"))
    items.append(_item("23 05 48", "vibration_iso",
                       "Neoprene Vibration Pad", "EA"))
    for s in ["6\"", "12\"", "18\"", "24\""]:
        items.append(_item("23 33 53", "flex_connector",
                           f"Duct Flexible Connector, {s} length", "EA", size=s))
    items.append(_item("23 05 29", "roof_curb", "Roof Curb, Insulated, 24\" tall", "EA"))
    items.append(_item("23 05 29", "equipment_pad", "Concrete Equipment Pad, 4\" thick", "SF"))
    items.append(_item("23 05 29", "hanger", "Pipe Hanger w/ Clevis", "EA"))
    items.append(_item("23 05 29", "hanger", "Trapeze Hanger Assembly", "EA"))
    items.append(_item("23 05 29", "support", "Duct Support Trapeze, Galvanized", "LF"))

    # ── 23 05 33 — Identification ─────────────────────────────────────────────
    items.append(_item("23 05 53", "identification", "Pipe Marker Label", "EA"))
    items.append(_item("23 05 53", "identification", "Equipment Nameplate", "EA"))
    items.append(_item("23 05 53", "identification", "Valve Tag w/ Chain", "EA"))

    # ── 23 05 93 — Test / Adjust / Balance & 23 05 — Cleaning / Startup ───────
    items.append(_item("23 05 93", "tab",
                       "TAB — Air Side, per terminal device", "EA"))
    items.append(_item("23 05 93", "tab",
                       "TAB — Hydronic Side, per balance valve", "EA"))
    items.append(_item("23 05 93", "tab",
                       "TAB — Equipment startup, per equipment", "EA"))
    items.append(_item("23 05 33", "cleaning",
                       "Duct Cleaning (Internal), per LF of main", "LF"))
    items.append(_item("23 05 00", "startup",
                       "System Commissioning Allowance, per ton of cooling",
                       "EA", size="per ton"))

    return items


CATALOG_ITEMS: list[CatalogItem] = _build_catalog()


def get_catalog() -> list[CatalogItem]:
    """Return a fresh copy of the catalog so callers can mutate freely."""
    return [dict(item) for item in CATALOG_ITEMS]

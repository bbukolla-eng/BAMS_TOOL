"""
Division 23 labor assemblies — standard production rates by trade activity.

Hours are intentionally None. They must come from a trade-shop historical
or an industry source (RSMeans, NECA, SMACNA labor units, MCAA, BNi).
The seed loader writes 0.0 with a note so the bid pipeline can flag any
assembly that hasn't been priced yet.
"""

from typing import TypedDict


class AssemblyDef(TypedDict, total=False):
    name: str
    description: str
    unit_of_measure: str
    notes: str | None


PENDING_NOTE = "HOURS_PENDING_HISTORICAL_DATA"


def _a(name: str, description: str, unit: str, notes: str | None = None) -> AssemblyDef:
    return {
        "name": name,
        "description": description,
        "unit_of_measure": unit,
        "notes": notes or PENDING_NOTE,
    }


# Labor unit conventions: time per LF, per EA, per SF, or per ton/CFM/MBH.
ASSEMBLIES: list[AssemblyDef] = [
    # ── Sheet metal (ductwork install + fab) ──────────────────────────────────
    _a("Sheet Metal — Rectangular Duct Install (≤24\" wide)",
       "Rectangular galvanized duct, hung in place, sealed, including hangers",
       "LF"),
    _a("Sheet Metal — Rectangular Duct Install (>24\" wide)",
       "Large rectangular duct, mains and risers", "LF"),
    _a("Sheet Metal — Round Duct Install (≤14\")",
       "Round spiral duct, hung in place, sealed", "LF"),
    _a("Sheet Metal — Round Duct Install (>14\")",
       "Large round spiral, mains", "LF"),
    _a("Sheet Metal — Flex Duct Install",
       "Flex duct connection from main to terminal device", "LF"),
    _a("Sheet Metal — Fitting Set in Place",
       "Elbow / tee / transition install only", "EA"),

    # ── Air outlets / inlets ──────────────────────────────────────────────────
    _a("Diffuser Install — Lay-in Ceiling",
       "Diffuser dropped into T-bar grid, neck connected", "EA"),
    _a("Diffuser Install — Hard Ceiling",
       "Diffuser cut into drywall ceiling, supported", "EA"),
    _a("Linear Slot Diffuser Install",
       "Linear diffuser w/ plenum, per LF of slot", "LF"),
    _a("Return Grille Install",
       "Lay-in or wall return grille", "EA"),

    # ── Air terminal units ────────────────────────────────────────────────────
    _a("VAV Box Install — Single Duct",
       "VAV hung, ducted, controls connected", "EA"),
    _a("VAV Box Install — w/ Reheat Coil",
       "VAV w/ HW or electric reheat, additional connections", "EA"),
    _a("Fan-Powered VAV Install",
       "Fan-powered terminal w/ controls", "EA"),

    # ── Hydronic piping ───────────────────────────────────────────────────────
    _a("Pipe Install — Steel Sch 40 ≤2\"",
       "Threaded black steel pipe, hangers and supports", "LF"),
    _a("Pipe Install — Steel Sch 40 2½\"–4\"",
       "Welded or grooved steel pipe, hangers, supports", "LF"),
    _a("Pipe Install — Steel Sch 40 6\"+",
       "Welded/grooved steel pipe, large bore", "LF"),
    _a("Pipe Install — Copper Type L ≤1\"",
       "Soldered copper, small bore", "LF"),
    _a("Pipe Install — Copper Type L 1¼\"–2\"",
       "Soldered or pressed copper, medium bore", "LF"),
    _a("Pipe Install — PEX",
       "Crimp / expansion PEX", "LF"),
    _a("Pipe Install — Refrigerant ACR Copper",
       "Brazed copper for refrigerant, including N₂ purge", "LF"),

    # ── Pipe fittings & specialties ───────────────────────────────────────────
    _a("Steel Fitting Install — ≤2\"",
       "Welded/threaded steel fitting", "EA"),
    _a("Steel Fitting Install — >2\"",
       "Welded steel fitting, large", "EA"),
    _a("Grooved Coupling Install",
       "Victaulic-style coupling, gasket and bolts", "EA"),
    _a("Valve Install — ≤2\" Threaded",
       "Bronze ball / globe / check valve install", "EA"),
    _a("Valve Install — Flanged Cast Iron",
       "Butterfly / gate / check valve, flanged", "EA"),
    _a("Strainer Install",
       "Y-strainer including blowdown valve", "EA"),
    _a("Control Valve Install w/ Actuator",
       "2-way or 3-way control valve, actuator wired", "EA"),

    # ── Equipment hookup ──────────────────────────────────────────────────────
    _a("AHU Install — Set in Place + Connect",
       "Custom AHU, structural set, duct/piping/electrical connections (per ton or CFM)",
       "ton"),
    _a("RTU Install — Set + Curb + Connect",
       "Packaged RTU, on roof curb, gas/electrical/refrigerant", "ton"),
    _a("FCU Install — Hang + Connect",
       "Fan coil unit, mounted, piped, drained, controls", "EA"),
    _a("Boiler Install — Set + Connect",
       "Hot water or steam boiler, piped, vented, gas/electrical (per MBH)",
       "MBH"),
    _a("Chiller Install — Set + Connect (per ton)",
       "Air-cooled or water-cooled chiller, piping/electrical/controls", "ton"),
    _a("Cooling Tower Install — Set + Connect",
       "Cooling tower set on structure, piping and basin", "ton"),
    _a("Pump Install — Set + Connect",
       "Pump base, alignment, piping, electrical connection", "EA"),
    _a("VRF System Hookup",
       "Outdoor unit + indoor branches, refrigerant, controls (per ton outdoor)",
       "ton"),
    _a("Mini-Split Install",
       "Outdoor + indoor unit, line set, condensate", "EA"),

    # ── Insulation ────────────────────────────────────────────────────────────
    _a("Duct Insulation Wrap",
       "External duct insulation FSK, taped seams", "SF"),
    _a("Duct Liner Install",
       "Internal acoustic/thermal liner, glued and pinned", "SF"),
    _a("Pipe Insulation — ≤2\" pipe",
       "Fiberglass pipe insulation, sectional, jacketed", "LF"),
    _a("Pipe Insulation — >2\" pipe",
       "Larger pipe insulation including fittings/valves", "LF"),

    # ── Controls / BAS ────────────────────────────────────────────────────────
    _a("DDC Controller Install",
       "Mount and wire field controller", "EA"),
    _a("BAS Sensor Install",
       "Temperature, humidity, CO2, or pressure sensor mount + wire", "EA"),
    _a("VFD Install",
       "Mount, power, control wiring", "EA"),
    _a("Damper Actuator Install",
       "Mount actuator on damper, wire", "EA"),
    _a("Controls Programming & Point-to-Point",
       "Per BAS point: programmed, mapped, verified", "EA"),

    # ── Test / Adjust / Balance / Startup ─────────────────────────────────────
    _a("Air Balance — Per Terminal",
       "Read, adjust, certify per diffuser/grille/VAV", "EA"),
    _a("Hydronic Balance — Per Balance Valve",
       "Read, adjust, certify per circuit balancing valve", "EA"),
    _a("Equipment Startup — Per Major Unit",
       "Manufacturer-supervised startup of AHU/RTU/Boiler/Chiller", "EA"),
    _a("System Commissioning",
       "Functional performance testing, per ton of installed cooling", "ton"),
    _a("Duct Cleaning (Internal)",
       "Robotic / contact cleaning per LF of main", "LF"),

    # ── Identification & Closeout ─────────────────────────────────────────────
    _a("Pipe Marker Application",
       "Apply pipe markers per ASME A13.1", "EA"),
    _a("Valve Tag Application",
       "Tag valves and update valve schedule", "EA"),
    _a("As-Built Drawing Markup",
       "Field redlines transferred to as-builts", "hr"),
    _a("O&M Manual Compilation",
       "Per major equipment item documented", "EA"),

    # ── Demolition (selective HVAC demo) ──────────────────────────────────────
    _a("Demo — Existing Ductwork",
       "Cut, cap, and remove existing duct", "LF"),
    _a("Demo — Existing Pipe (insulated)",
       "Cut, drain, remove insulated hydronic pipe", "LF"),
    _a("Demo — Existing Equipment Removal",
       "Disconnect and remove existing AHU/FCU/boiler", "EA"),
]


def get_assemblies() -> list[AssemblyDef]:
    return [dict(a) for a in ASSEMBLIES]

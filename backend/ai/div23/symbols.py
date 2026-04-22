"""
Division 23 HVAC symbol library.
Maps symbol types to CSI codes, descriptions, and takeoff rules.
"""
from dataclasses import dataclass, field


@dataclass
class SymbolDefinition:
    symbol_type: str
    csi_code: str
    description: str
    unit: str  # "EA", "LF", "SF", "TON"
    category: str
    system: str
    waste_factor: float = 0.05
    # How to count: "each" = count instances, "area" = use bounding box, "length" = use run
    count_method: str = "each"
    typical_size_range: str = ""
    notes: str = ""


HVAC_SYMBOLS: dict[str, SymbolDefinition] = {
    # ── Air Handling Units ────────────────────────────────────────────────
    "ahu": SymbolDefinition(
        symbol_type="ahu",
        csi_code="23 73 13",
        description="Air Handling Unit (AHU)",
        unit="EA",
        category="equipment",
        system="Supply Air",
        count_method="each",
        typical_size_range="500-100,000 CFM",
    ),
    "fcu": SymbolDefinition(
        symbol_type="fcu",
        csi_code="23 82 19",
        description="Fan Coil Unit (FCU)",
        unit="EA",
        category="equipment",
        system="Supply Air",
        count_method="each",
        typical_size_range="100-4,000 CFM",
    ),
    "vav_box": SymbolDefinition(
        symbol_type="vav_box",
        csi_code="23 36 00",
        description="Variable Air Volume (VAV) Box",
        unit="EA",
        category="air_terminal",
        system="Supply Air",
        count_method="each",
        typical_size_range="4\"-14\" inlet",
    ),

    # ── Diffusers and Grilles ─────────────────────────────────────────────
    "diffuser_supply": SymbolDefinition(
        symbol_type="diffuser_supply",
        csi_code="23 37 13",
        description="Supply Air Diffuser",
        unit="EA",
        category="diffuser",
        system="Supply Air",
        count_method="each",
        typical_size_range="6x6 to 24x24",
    ),
    "diffuser_return": SymbolDefinition(
        symbol_type="diffuser_return",
        csi_code="23 37 13",
        description="Return Air Grille",
        unit="EA",
        category="diffuser",
        system="Return Air",
        count_method="each",
    ),
    "grille": SymbolDefinition(
        symbol_type="grille",
        csi_code="23 37 23",
        description="Linear Bar Grille",
        unit="EA",
        category="diffuser",
        system="Supply Air",
        count_method="each",
    ),

    # ── Fans ──────────────────────────────────────────────────────────────
    "exhaust_fan": SymbolDefinition(
        symbol_type="exhaust_fan",
        csi_code="23 34 23",
        description="Exhaust Fan",
        unit="EA",
        category="equipment",
        system="Exhaust Air",
        count_method="each",
    ),
    "inline_fan": SymbolDefinition(
        symbol_type="inline_fan",
        csi_code="23 34 13",
        description="Inline Centrifugal Fan",
        unit="EA",
        category="equipment",
        system="Supply Air",
        count_method="each",
    ),

    # ── Cooling Equipment ─────────────────────────────────────────────────
    "chiller": SymbolDefinition(
        symbol_type="chiller",
        csi_code="23 64 16",
        description="Centrifugal Water Chiller",
        unit="EA",
        category="equipment",
        system="Chilled Water",
        count_method="each",
        typical_size_range="50-2,000 tons",
    ),
    "cooling_tower": SymbolDefinition(
        symbol_type="cooling_tower",
        csi_code="23 65 00",
        description="Cooling Tower",
        unit="EA",
        category="equipment",
        system="Condenser Water",
        count_method="each",
    ),
    "vrf_outdoor": SymbolDefinition(
        symbol_type="vrf_outdoor",
        csi_code="23 81 26",
        description="VRF Outdoor Condensing Unit",
        unit="EA",
        category="equipment",
        system="Refrigerant",
        count_method="each",
    ),
    "vrf_indoor": SymbolDefinition(
        symbol_type="vrf_indoor",
        csi_code="23 81 26",
        description="VRF Indoor Fan Coil",
        unit="EA",
        category="equipment",
        system="Refrigerant",
        count_method="each",
    ),

    # ── Heating Equipment ─────────────────────────────────────────────────
    "boiler": SymbolDefinition(
        symbol_type="boiler",
        csi_code="23 52 16",
        description="Hot Water Boiler",
        unit="EA",
        category="equipment",
        system="Heating Water",
        count_method="each",
    ),
    "heat_exchanger": SymbolDefinition(
        symbol_type="heat_exchanger",
        csi_code="23 57 13",
        description="Shell and Tube Heat Exchanger",
        unit="EA",
        category="equipment",
        system="Heating Water",
        count_method="each",
    ),

    # ── Pumps ─────────────────────────────────────────────────────────────
    "pump": SymbolDefinition(
        symbol_type="pump",
        csi_code="23 21 23",
        description="Base-Mounted Centrifugal Pump",
        unit="EA",
        category="equipment",
        system="Hydronic",
        count_method="each",
    ),

    # ── Controls ──────────────────────────────────────────────────────────
    "thermostat": SymbolDefinition(
        symbol_type="thermostat",
        csi_code="23 09 23",
        description="Room Thermostat / BAS Sensor",
        unit="EA",
        category="controls",
        system="Controls",
        count_method="each",
    ),
    "damper_manual": SymbolDefinition(
        symbol_type="damper_manual",
        csi_code="23 33 13",
        description="Manual Volume Damper",
        unit="EA",
        category="damper",
        system="Supply Air",
        count_method="each",
    ),
    "damper_motorized": SymbolDefinition(
        symbol_type="damper_motorized",
        csi_code="23 33 13",
        description="Motorized Control Damper",
        unit="EA",
        category="damper",
        system="Controls",
        count_method="each",
    ),
    "fire_damper": SymbolDefinition(
        symbol_type="fire_damper",
        csi_code="23 33 46",
        description="Fire Damper (UL Listed)",
        unit="EA",
        category="damper",
        system="Fire/Life Safety",
        count_method="each",
    ),
    "smoke_damper": SymbolDefinition(
        symbol_type="smoke_damper",
        csi_code="23 33 46",
        description="Smoke Damper",
        unit="EA",
        category="damper",
        system="Fire/Life Safety",
        count_method="each",
    ),

    # ── Valves ────────────────────────────────────────────────────────────
    "valve_gate": SymbolDefinition(
        symbol_type="valve_gate",
        csi_code="23 21 13",
        description="Gate Valve",
        unit="EA",
        category="valve",
        system="Hydronic",
        count_method="each",
    ),
    "valve_ball": SymbolDefinition(
        symbol_type="valve_ball",
        csi_code="23 21 13",
        description="Ball Valve",
        unit="EA",
        category="valve",
        system="Hydronic",
        count_method="each",
    ),
    "valve_butterfly": SymbolDefinition(
        symbol_type="valve_butterfly",
        csi_code="23 21 13",
        description="Butterfly Valve",
        unit="EA",
        category="valve",
        system="Hydronic",
        count_method="each",
    ),
    "valve_check": SymbolDefinition(
        symbol_type="valve_check",
        csi_code="23 21 13",
        description="Check Valve",
        unit="EA",
        category="valve",
        system="Hydronic",
        count_method="each",
    ),
    "valve_balancing": SymbolDefinition(
        symbol_type="valve_balancing",
        csi_code="23 21 13",
        description="Circuit Balancing Valve",
        unit="EA",
        category="valve",
        system="Hydronic",
        count_method="each",
    ),
}


def get_symbol_def(symbol_type: str) -> SymbolDefinition | None:
    return HVAC_SYMBOLS.get(symbol_type)


# Material run types → CSI codes and descriptions
MATERIAL_RUN_TYPES: dict[str, dict] = {
    "duct_supply": {"csi_code": "23 31 13", "description": "Supply Air Ductwork", "unit": "LF", "category": "duct"},
    "duct_return": {"csi_code": "23 31 13", "description": "Return Air Ductwork", "unit": "LF", "category": "duct"},
    "duct_exhaust": {"csi_code": "23 31 13", "description": "Exhaust Air Ductwork", "unit": "LF", "category": "duct"},
    "duct_oa": {"csi_code": "23 31 13", "description": "Outside Air Ductwork", "unit": "LF", "category": "duct"},
    "pipe_chw_supply": {"csi_code": "23 21 13", "description": "Chilled Water Supply Pipe", "unit": "LF", "category": "pipe"},
    "pipe_chw_return": {"csi_code": "23 21 13", "description": "Chilled Water Return Pipe", "unit": "LF", "category": "pipe"},
    "pipe_hw_supply": {"csi_code": "23 21 13", "description": "Heating Water Supply Pipe", "unit": "LF", "category": "pipe"},
    "pipe_hw_return": {"csi_code": "23 21 13", "description": "Heating Water Return Pipe", "unit": "LF", "category": "pipe"},
    "pipe_cw_supply": {"csi_code": "23 21 13", "description": "Condenser Water Supply Pipe", "unit": "LF", "category": "pipe"},
    "pipe_cw_return": {"csi_code": "23 21 13", "description": "Condenser Water Return Pipe", "unit": "LF", "category": "pipe"},
    "pipe_steam": {"csi_code": "23 22 13", "description": "Steam Supply Pipe", "unit": "LF", "category": "pipe"},
    "pipe_condensate": {"csi_code": "23 22 13", "description": "Condensate Return Pipe", "unit": "LF", "category": "pipe"},
    "pipe_refrigerant": {"csi_code": "23 23 00", "description": "Refrigerant Piping", "unit": "LF", "category": "pipe"},
    "pipe_hvac": {"csi_code": "23 21 13", "description": "HVAC Pipe", "unit": "LF", "category": "pipe"},
    "conduit": {"csi_code": "26 05 33", "description": "Electrical Conduit", "unit": "LF", "category": "conduit"},
    "pipe_sanitary": {"csi_code": "22 13 16", "description": "Sanitary Waste Pipe", "unit": "LF", "category": "pipe"},
    "pipe_domestic_hot": {"csi_code": "22 11 16", "description": "Domestic Hot Water Pipe", "unit": "LF", "category": "pipe"},
    "pipe_domestic_cold": {"csi_code": "22 11 16", "description": "Domestic Cold Water Pipe", "unit": "LF", "category": "pipe"},
}

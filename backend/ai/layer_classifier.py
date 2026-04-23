"""
Classifies drawing layers and colors into material types.
Handles AIA layer naming conventions plus common firm-specific patterns.
Division 23 (Mechanical/HVAC) is the primary focus.
"""

# AIA Layer name → material type mapping
# Priority: more specific patterns first
LAYER_PATTERNS: list[tuple[str, str]] = [
    # ── Division 23 HVAC ──────────────────────────────────────────────────
    ("M-HVAC-DUCT-S", "duct_supply"),
    ("M-HVAC-DUCT-R", "duct_return"),
    ("M-HVAC-DUCT-E", "duct_exhaust"),
    ("M-HVAC-DUCT-O", "duct_oa"),         # outside air
    ("M-HVAC-DUCT", "duct_supply"),        # fallback
    ("MECH-DUCT-SUPPLY", "duct_supply"),
    ("MECH-DUCT-RETURN", "duct_return"),
    ("MECH-DUCT-EXHAUST", "duct_exhaust"),
    ("MECH_SUPPLY", "duct_supply"),
    ("MECH_RETURN", "duct_return"),
    ("DUCT-SUPPLY", "duct_supply"),
    ("DUCT-RETURN", "duct_return"),
    ("DUCT-EXHAUST", "duct_exhaust"),
    ("DUCT", "duct_supply"),               # generic duct
    # Chilled water
    ("M-PIPE-CHW-S", "pipe_chw_supply"),
    ("M-PIPE-CHW-R", "pipe_chw_return"),
    ("M-PIPE-CHW", "pipe_chw_supply"),
    ("CHWS", "pipe_chw_supply"),
    ("CHWR", "pipe_chw_return"),
    ("CHW-S", "pipe_chw_supply"),
    ("CHW-R", "pipe_chw_return"),
    # Hot water / heating water
    ("M-PIPE-HHW-S", "pipe_hw_supply"),
    ("M-PIPE-HHW-R", "pipe_hw_return"),
    ("M-PIPE-HW", "pipe_hw_supply"),
    ("HWS", "pipe_hw_supply"),
    ("HWR", "pipe_hw_return"),
    ("HW-S", "pipe_hw_supply"),
    ("HW-R", "pipe_hw_return"),
    # Condenser water
    ("M-PIPE-CW-S", "pipe_cw_supply"),
    ("M-PIPE-CW-R", "pipe_cw_return"),
    ("CWS", "pipe_cw_supply"),
    ("CWR", "pipe_cw_return"),
    # Steam and condensate
    ("M-PIPE-STM", "pipe_steam"),
    ("M-PIPE-CON", "pipe_condensate"),
    ("STEAM", "pipe_steam"),
    # Refrigerant
    ("M-PIPE-REF", "pipe_refrigerant"),
    ("REFRIG", "pipe_refrigerant"),
    # General mechanical pipe
    ("M-PIPE", "pipe_hvac"),
    ("MECH-PIPE", "pipe_hvac"),
    # Insulation
    ("M-INSL", "insulation"),
    ("INSULATION", "insulation"),
    # Equipment
    ("M-EQUIP", "hvac_equipment"),
    ("MECH-EQUIP", "hvac_equipment"),
    # Controls
    ("M-CTRL", "hvac_controls"),
    ("CONTROLS", "hvac_controls"),

    # ── Division 26 Electrical ────────────────────────────────────────────
    # Must appear before short abbreviations like "COND" to avoid false matches
    ("E-POWR-CONDUIT", "conduit"),
    ("E-LTNG-CONDUIT", "conduit"),
    ("E-CONDUIT", "conduit"),
    ("ELEC-CONDUIT", "conduit"),
    # Short condensate abbreviation — placed after all CONDUIT patterns
    ("COND", "pipe_condensate"),
    ("E-WIRE", "wire"),
    ("E-CABLE", "wire"),
    ("E-TRAY", "cable_tray"),
    ("E-PANEL", "electrical_panel"),
    ("E-EQUIP", "electrical_equipment"),

    # ── Division 22 Plumbing ──────────────────────────────────────────────
    ("P-SANR", "pipe_sanitary"),
    ("P-DOMW-H", "pipe_domestic_hot"),
    ("P-DOMW-C", "pipe_domestic_cold"),
    ("P-STRM", "pipe_storm"),
    ("P-VENT", "pipe_vent"),
    ("P-FIRE", "pipe_fire"),
    ("PLMB", "pipe_plumbing"),
]

# Color-based fallback classification (RGB tuples, approximate)
COLOR_MAP: list[tuple[tuple, str]] = [
    ((0, 0, 255), "pipe_chw_supply"),      # blue → chilled water supply
    ((0, 0, 128), "pipe_chw_return"),      # dark blue → CHW return
    ((255, 0, 0), "pipe_hw_supply"),       # red → hot water supply
    ((128, 0, 0), "pipe_hw_return"),       # dark red → HW return
    ((0, 200, 0), "duct_supply"),          # green → supply duct
    ((0, 100, 0), "duct_return"),          # dark green → return duct
    ((255, 165, 0), "duct_exhaust"),       # orange → exhaust
    ((128, 0, 128), "pipe_steam"),         # purple → steam
    ((255, 255, 0), "conduit"),            # yellow → electrical conduit
    ((100, 100, 100), "pipe_sanitary"),    # gray → sanitary
]


def classify_layer_from_name(layer_name: str) -> str:
    upper = layer_name.upper()
    for pattern, material_type in LAYER_PATTERNS:
        if pattern.upper() in upper:
            return material_type
    # Generic fallback based on first letter
    if upper.startswith("M-") or upper.startswith("MECH"):
        return "mechanical"
    if upper.startswith("E-") or upper.startswith("ELEC"):
        return "electrical"
    if upper.startswith("P-") or upper.startswith("PLMB"):
        return "plumbing"
    return "unknown"


def classify_layer_from_color(color) -> str:
    if not color:
        return "unknown"
    if isinstance(color, (list, tuple)) and len(color) == 3:
        r, g, b = [int(c * 255) for c in color]
        min_dist = float("inf")
        best = "unknown"
        for (cr, cg, cb), material_type in COLOR_MAP:
            dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if dist < min_dist:
                min_dist = dist
                best = material_type
        # Only use color classification if reasonably close
        return best if min_dist < 20000 else "unknown"
    return "unknown"

"""
Extract structured equipment metadata (tag, model, capacity, size) from
DXF block attributes and nearby drawing text annotations.

A drawn AHU symbol with no metadata is just "1 EA AHU" — useless for
pricing. With block ATTRIBs (ATTDEF entries) populated by the design tool,
or with adjacent text like ``AHU-1 / 12,000 CFM / 480V``, we can pin down
the actual equipment so the bid line item maps to the right price book entry.

Public surface:
    extract_metadata(block_dict, nearby_text=None) -> dict
        Normalizes attribute keys and folds in any size/capacity that text
        proximity reveals.
    parse_size_token(text) -> str | None
        Best-effort conversion of "12x12", "24X24", "10\"", "10 IN" → canonical
        forms used elsewhere in the catalog.
    parse_capacity(text) -> dict
        Extract any of: cfm, tons, mbh, gpm, hp, voltage, model.
"""
from __future__ import annotations

import re
from typing import Any

# DXF ATTRIB tag names vary; map every common spelling to one canonical key.
_ATTRIB_KEY_ALIASES: dict[str, str] = {
    "TAG": "tag",
    "MARK": "tag",
    "ID": "tag",
    "EQUIPMENT_TAG": "tag",
    "EQUIP_TAG": "tag",
    "EQUIPMENT": "tag",
    "NAME": "tag",
    "MODEL": "model",
    "MODEL_NUMBER": "model",
    "MODEL_NO": "model",
    "MODEL#": "model",
    "MFR": "manufacturer",
    "MANUFACTURER": "manufacturer",
    "MAKE": "manufacturer",
    "CFM": "cfm",
    "AIRFLOW": "cfm",
    "SUPPLY_CFM": "cfm",
    "TONS": "tons",
    "TONNAGE": "tons",
    "TONS_COOLING": "tons",
    "MBH": "mbh",
    "BTU": "mbh",
    "BTUH": "mbh",
    "HEATING_MBH": "mbh",
    "GPM": "gpm",
    "FLOW": "gpm",
    "HP": "hp",
    "MOTOR_HP": "hp",
    "VOLTS": "voltage",
    "VOLTAGE": "voltage",
    "V": "voltage",
    "PHASE": "phase",
    "SIZE": "size",
    "DIM": "size",
    "DIMENSIONS": "size",
    "DIA": "size",
    "INLET": "inlet_size",
    "INLET_SIZE": "inlet_size",
    "INLET_DIA": "inlet_size",
    "NECK": "inlet_size",
    "CAPACITY": "capacity",
    "REMARK": "notes",
    "REMARKS": "notes",
    "NOTES": "notes",
}

_SIZE_TOKEN = re.compile(r"\b(\d+)\s*[xX]\s*(\d+)\b")
_DIAMETER_TOKEN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:\"|in\b|inch\b|IN\b|INCH\b|RD\b|DIA\b)", re.IGNORECASE)
_CFM_TOKEN = re.compile(r"\b([\d,]+(?:\.\d+)?)\s*CFM\b", re.IGNORECASE)
_TON_TOKEN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:TONS?|T)\b", re.IGNORECASE)
_MBH_TOKEN = re.compile(r"\b([\d,]+(?:\.\d+)?)\s*MBH\b", re.IGNORECASE)
_GPM_TOKEN = re.compile(r"\b([\d,]+(?:\.\d+)?)\s*GPM\b", re.IGNORECASE)
_HP_TOKEN = re.compile(r"\b(\d+(?:\.\d+)?)\s*HP\b", re.IGNORECASE)
_VOLTAGE_TOKEN = re.compile(r"\b(208|230|240|277|460|480|600)\s*V\b", re.IGNORECASE)
# Tag pattern: equipment marks like AHU-1, VAV-3.2, FCU-04, P-100.
_TAG_TOKEN = re.compile(r"\b([A-Z]{1,4}[-]?\d+(?:\.\d+)?)\b")


def _coerce_number(raw: str) -> float | None:
    s = raw.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_size_token(text: str | None) -> str | None:
    """Normalize a free-text size into our catalog form: ``12x12`` or ``10\"``."""
    if not text:
        return None
    s = text.strip()
    m = _SIZE_TOKEN.search(s)
    if m:
        return f"{int(m.group(1))}x{int(m.group(2))}"
    m = _DIAMETER_TOKEN.search(s)
    if m:
        # Drop trailing zeros so 10.0 becomes "10\""
        n = float(m.group(1))
        nstr = f"{n:g}"
        return f"{nstr}\""
    return None


def parse_capacity(text: str | None) -> dict[str, Any]:
    """Pull CFM / tons / MBH / GPM / HP / voltage out of a free-text label."""
    out: dict[str, Any] = {}
    if not text:
        return out
    if (m := _CFM_TOKEN.search(text)) and (n := _coerce_number(m.group(1))) is not None:
        out["cfm"] = n
    if (m := _TON_TOKEN.search(text)) and (n := _coerce_number(m.group(1))) is not None:
        out["tons"] = n
    if (m := _MBH_TOKEN.search(text)) and (n := _coerce_number(m.group(1))) is not None:
        out["mbh"] = n
    if (m := _GPM_TOKEN.search(text)) and (n := _coerce_number(m.group(1))) is not None:
        out["gpm"] = n
    if (m := _HP_TOKEN.search(text)) and (n := _coerce_number(m.group(1))) is not None:
        out["hp"] = n
    if m := _VOLTAGE_TOKEN.search(text):
        out["voltage"] = int(m.group(1))
    return out


def extract_tag(text: str | None) -> str | None:
    """Pull the equipment tag (AHU-1, VAV-3.2) from text. Returns the first
    plausible match; callers can refine with proximity if multiple tags appear.
    """
    if not text:
        return None
    # Skip pure dimensions like "12x12" — they look like tags otherwise.
    cleaned = _SIZE_TOKEN.sub("", text)
    m = _TAG_TOKEN.search(cleaned)
    return m.group(1) if m else None


def _normalize_attribs(raw: dict[str, str]) -> dict[str, Any]:
    """Map manufacturer attribute keys to canonical field names; coerce numbers."""
    out: dict[str, Any] = {}
    for raw_key, raw_value in raw.items():
        key = _ATTRIB_KEY_ALIASES.get(raw_key.upper().strip())
        if not key or not raw_value:
            continue
        value: Any = raw_value.strip()
        if key in ("cfm", "tons", "mbh", "gpm", "hp"):
            number = _coerce_number(value)
            if number is not None:
                out[key] = number
            continue
        if key == "voltage":
            number = _coerce_number(value)
            if number is not None:
                out[key] = int(number)
            continue
        if key == "size":
            normalized = parse_size_token(value) or value
            out["size"] = normalized
            continue
        if key == "inlet_size":
            normalized = parse_size_token(value) or value
            out["inlet_size"] = normalized
            continue
        out[key] = value
    return out


def extract_metadata(
    block: dict[str, Any], nearby_text: list[str] | None = None
) -> dict[str, Any]:
    """Combine DXF block attributes with adjacent annotation text.

    Block attributes win over text-derived values: a designer who set TAG=AHU-1
    on the block is more authoritative than nearby loose text.
    """
    metadata: dict[str, Any] = {}
    raw_attribs = block.get("attribs") or {}
    if isinstance(raw_attribs, dict):
        metadata.update(_normalize_attribs(raw_attribs))

    if not nearby_text:
        return metadata

    combined = " | ".join(t for t in nearby_text if t)
    if "tag" not in metadata:
        tag = extract_tag(combined)
        if tag:
            metadata["tag"] = tag
    if "size" not in metadata:
        size = parse_size_token(combined)
        if size:
            metadata["size"] = size
    capacity = parse_capacity(combined)
    for k, v in capacity.items():
        metadata.setdefault(k, v)
    return metadata


def text_within_radius(
    cx: float,
    cy: float,
    text_elements: list[dict[str, Any]],
    radius_ft: float = 6.0,
) -> list[str]:
    """Return text strings whose anchor point is within `radius_ft` of (cx,cy).

    Used to pull annotations like "AHU-1" or "12,000 CFM" sitting next to the
    drawn equipment symbol. Sorted nearest-first so callers can pick the most
    likely label.
    """
    found: list[tuple[float, str]] = []
    r2 = radius_ft * radius_ft
    for t in text_elements:
        tx = t.get("x")
        ty = t.get("y")
        if tx is None or ty is None:
            continue
        d2 = (tx - cx) ** 2 + (ty - cy) ** 2
        if d2 <= r2:
            text = (t.get("text") or "").strip()
            if text:
                found.append((d2, text))
    found.sort(key=lambda pair: pair[0])
    return [text for _, text in found]

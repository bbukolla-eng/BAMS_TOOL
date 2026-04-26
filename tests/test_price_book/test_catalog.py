"""
Catalog data integrity — every Division 23 catalog entry must have the
fields the seed loader and bid pipeline rely on, and pricing must not be
silently invented.
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from seeds.division_23_assemblies import ASSEMBLIES, PENDING_NOTE
from seeds.division_23_catalog import CATALOG_ITEMS, PRICE_PENDING


CSI_PATTERN = re.compile(r"^\d{2} \d{2} \d{2}$")
ALLOWED_UNITS = {"LF", "EA", "SF", "ton", "MBH", "hr"}


def test_catalog_is_non_trivial():
    assert len(CATALOG_ITEMS) >= 250, (
        f"Catalog should cover Division 23 broadly; got only {len(CATALOG_ITEMS)} items"
    )


def test_every_item_has_required_fields():
    for item in CATALOG_ITEMS:
        assert item.get("description"), f"missing description: {item}"
        assert item.get("category"), f"missing category: {item}"
        assert item.get("unit"), f"missing unit: {item}"
        assert item.get("csi_code"), f"missing csi_code: {item['description']}"


def test_csi_codes_are_division_23():
    for item in CATALOG_ITEMS:
        code = item["csi_code"]
        assert CSI_PATTERN.match(code), f"bad CSI format: {code!r} ({item['description']})"
        assert code.startswith("23 "), (
            f"expected Division 23 CSI prefix, got {code!r} ({item['description']})"
        )


def test_units_are_valid():
    for item in CATALOG_ITEMS:
        assert item["unit"] in ALLOWED_UNITS, (
            f"unexpected unit {item['unit']!r} on {item['description']}"
        )


def test_no_duplicate_descriptions():
    counts = Counter(item["description"] for item in CATALOG_ITEMS)
    dupes = {desc: n for desc, n in counts.items() if n > 1}
    assert not dupes, f"duplicate descriptions in catalog: {dupes}"


def test_every_item_flagged_pending_pricing():
    """User directive: no fabricated prices. Every entry must signal that
    pricing comes from a manufacturer blue book."""
    for item in CATALOG_ITEMS:
        notes = item.get("notes") or ""
        assert PRICE_PENDING in notes, (
            f"Item missing PRICE_PENDING_BLUE_BOOK marker: {item['description']}"
        )


def test_catalog_covers_core_div23_categories():
    """Smoke test: the catalog must touch every major HVAC category, otherwise
    the takeoff/bid pipeline can't price a real Division 23 job."""
    categories = {item["category"] for item in CATALOG_ITEMS}
    required = {
        "duct_rectangular", "duct_round", "duct_flex", "duct_fitting",
        "damper", "diffuser", "grille",
        "vav_box", "ahu", "rtu", "fan", "fcu",
        "pump", "boiler", "chiller", "cooling_tower",
        "pipe_steel", "pipe_copper", "pipe_fitting",
        "valve_ball", "valve_butterfly", "valve_check",
        "duct_insulation", "pipe_insulation",
        "vrf_outdoor", "minisplit",
        "controller", "sensor", "vfd", "actuator",
        "tab", "startup",
    }
    missing = required - categories
    assert not missing, f"catalog missing critical Division 23 categories: {missing}"


def test_assemblies_non_trivial():
    assert len(ASSEMBLIES) >= 30, (
        f"labor assembly catalog too thin ({len(ASSEMBLIES)} items)"
    )


def test_assemblies_have_required_fields():
    for a in ASSEMBLIES:
        assert a.get("name"), f"missing name: {a}"
        assert a.get("description"), f"missing description: {a}"
        assert a.get("unit_of_measure"), f"missing unit: {a}"
        assert a.get("notes") and PENDING_NOTE in a["notes"], (
            f"assembly missing HOURS_PENDING marker: {a['name']}"
        )


def test_assembly_names_unique():
    names = [a["name"] for a in ASSEMBLIES]
    assert len(names) == len(set(names)), "duplicate labor assembly names"

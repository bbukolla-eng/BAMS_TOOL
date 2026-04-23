"""Tests for the bid Excel export function."""
import sys
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

# Skip entire module if openpyxl is unavailable (bare test env without heavy deps)
openpyxl = pytest.importorskip("openpyxl", reason="openpyxl not installed")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from modules.bidding.exporter import export_to_excel


def make_bid(**kwargs):
    defaults = dict(
        version=1,
        name="Bid v1",
        total_material_cost=10000.0,
        total_labor_hours=80.0,
        total_labor_cost=4000.0,
        total_burden=1400.0,
        total_overhead=1848.0,
        total_material_markup=1000.0,
        subtotal=18248.0,
        contingency=547.44,
        bond=182.48,
        permit=91.24,
        profit=1527.37,
        grand_total=20596.53,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_line_item(**kwargs):
    defaults = dict(
        description="Supply Air Ductwork",
        category="duct",
        system="Supply Air",
        quantity=100.0,
        unit="LF",
        unit_material_cost=15.0,
        unit_labor_hours=0.25,
        material_total=1500.0,
        labor_total=500.0,
        line_total=2000.0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestExportToExcel:
    def test_returns_bytes(self):
        bid = make_bid()
        result = export_to_excel(bid, [])
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_xlsx_format(self):
        bid = make_bid()
        result = export_to_excel(bid, [make_line_item()])
        wb = openpyxl.load_workbook(io.BytesIO(result))
        assert wb is not None

    def test_sheet_name_contains_version(self):
        bid = make_bid(version=3)
        result = export_to_excel(bid, [])
        wb = openpyxl.load_workbook(io.BytesIO(result))
        assert any("3" in name for name in wb.sheetnames)

    def test_line_items_written(self):
        items = [
            make_line_item(description="Supply Duct"),
            make_line_item(description="Return Duct"),
        ]
        bid = make_bid()
        result = export_to_excel(bid, items)
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        descriptions = [ws.cell(row=r, column=2).value for r in range(4, 7)]
        assert "Supply Duct" in descriptions
        assert "Return Duct" in descriptions

    def test_grand_total_in_output(self):
        bid = make_bid(grand_total=99999.99)
        result = export_to_excel(bid, [])
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        all_values = [
            ws.cell(row=r, column=c).value
            for r in range(1, ws.max_row + 1)
            for c in range(1, ws.max_column + 1)
        ]
        assert 99999.99 in all_values

    def test_empty_line_items(self):
        bid = make_bid()
        result = export_to_excel(bid, [])
        wb = openpyxl.load_workbook(io.BytesIO(result))
        assert wb.active is not None

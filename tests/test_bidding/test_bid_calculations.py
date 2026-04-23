"""
Tests for bid calculation logic extracted from the bidding router.
These test the pure arithmetic of overhead, markup, contingency, and grand total.
All tests use simple in-memory objects — no DB required.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


def make_line(material_total=0.0, labor_total=0.0, unit_labor_hours=0.0, quantity=1.0):
    return SimpleNamespace(
        material_total=material_total,
        labor_total=labor_total,
        unit_labor_hours=unit_labor_hours,
        quantity=quantity,
    )


def make_config(
    total_burden_rate=0.35,
    material_markup=0.10,
    general_overhead_rate=0.12,
    contingency_rate=0.03,
    bond_rate=0.01,
    permit_rate=0.005,
    profit_margin=0.08,
):
    return SimpleNamespace(
        total_burden_rate=total_burden_rate,
        material_markup=material_markup,
        general_overhead_rate=general_overhead_rate,
        contingency_rate=contingency_rate,
        bond_rate=bond_rate,
        permit_rate=permit_rate,
        profit_margin=profit_margin,
    )


def compute_totals(lines, config=None):
    """Pure-Python mirror of _recalculate_bid's arithmetic."""
    total_material = sum(l.material_total for l in lines)
    total_labor_hours = sum(l.unit_labor_hours * l.quantity for l in lines if l.unit_labor_hours)
    total_labor = sum(l.labor_total for l in lines)

    if config:
        burden = total_labor * config.total_burden_rate
        mat_markup = total_material * config.material_markup
        overhead = (total_material + total_labor + burden) * config.general_overhead_rate
        subtotal = total_material + mat_markup + total_labor + burden + overhead
        contingency = subtotal * config.contingency_rate
        bond = subtotal * config.bond_rate
        permit = subtotal * config.permit_rate
        profit = (subtotal + contingency + bond + permit) * config.profit_margin
        grand_total = subtotal + contingency + bond + permit + profit
    else:
        subtotal = total_material + total_labor
        grand_total = subtotal
        burden = mat_markup = overhead = contingency = bond = permit = profit = 0.0

    return {
        "total_material": total_material,
        "total_labor_hours": total_labor_hours,
        "total_labor": total_labor,
        "burden": burden,
        "mat_markup": mat_markup,
        "overhead": overhead,
        "subtotal": subtotal,
        "contingency": contingency,
        "bond": bond,
        "permit": permit,
        "profit": profit,
        "grand_total": grand_total,
    }


class TestBidCalculationsNoConfig:
    def test_empty_bid_zero_totals(self):
        result = compute_totals([])
        assert result["grand_total"] == 0.0
        assert result["subtotal"] == 0.0

    def test_single_material_line(self):
        lines = [make_line(material_total=1000.0)]
        result = compute_totals(lines)
        assert result["total_material"] == 1000.0
        assert result["subtotal"] == 1000.0
        assert result["grand_total"] == 1000.0

    def test_single_labor_line(self):
        lines = [make_line(labor_total=500.0)]
        result = compute_totals(lines)
        assert result["total_labor"] == 500.0
        assert result["grand_total"] == 500.0

    def test_mixed_lines_sum(self):
        lines = [
            make_line(material_total=1000.0, labor_total=300.0),
            make_line(material_total=500.0, labor_total=200.0),
        ]
        result = compute_totals(lines)
        assert result["total_material"] == 1500.0
        assert result["total_labor"] == 500.0
        assert result["grand_total"] == 2000.0

    def test_labor_hours_sum(self):
        lines = [
            make_line(unit_labor_hours=2.0, quantity=10.0),
            make_line(unit_labor_hours=3.0, quantity=5.0),
        ]
        result = compute_totals(lines)
        assert result["total_labor_hours"] == 35.0


class TestBidCalculationsWithConfig:
    def test_material_markup_applied(self):
        lines = [make_line(material_total=10000.0)]
        config = make_config(
            material_markup=0.10,
            total_burden_rate=0.0,
            general_overhead_rate=0.0,
            contingency_rate=0.0,
            bond_rate=0.0,
            permit_rate=0.0,
            profit_margin=0.0,
        )
        result = compute_totals(lines, config)
        assert result["mat_markup"] == 1000.0
        assert result["subtotal"] == 11000.0
        assert result["grand_total"] == 11000.0

    def test_burden_on_labor(self):
        lines = [make_line(labor_total=1000.0)]
        config = make_config(
            total_burden_rate=0.35,
            material_markup=0.0,
            general_overhead_rate=0.0,
            contingency_rate=0.0,
            bond_rate=0.0,
            permit_rate=0.0,
            profit_margin=0.0,
        )
        result = compute_totals(lines, config)
        assert abs(result["burden"] - 350.0) < 0.01

    def test_profit_margin_on_subtotal_plus_extras(self):
        lines = [make_line(material_total=10000.0)]
        config = make_config(
            material_markup=0.0,
            total_burden_rate=0.0,
            general_overhead_rate=0.0,
            contingency_rate=0.0,
            bond_rate=0.0,
            permit_rate=0.0,
            profit_margin=0.10,
        )
        result = compute_totals(lines, config)
        # profit = subtotal * 0.10 = 1000
        assert abs(result["profit"] - 1000.0) < 0.01
        assert abs(result["grand_total"] - 11000.0) < 0.01

    def test_full_calculation_reasonableness(self):
        lines = [
            make_line(material_total=50000.0, labor_total=20000.0, unit_labor_hours=200.0, quantity=1.0),
        ]
        config = make_config()
        result = compute_totals(lines, config)
        assert result["grand_total"] > result["subtotal"]
        assert result["subtotal"] > result["total_material"] + result["total_labor"]
        assert result["profit"] > 0

    def test_zero_rates_config_no_extra_cost(self):
        lines = [make_line(material_total=5000.0, labor_total=2000.0)]
        config = make_config(
            total_burden_rate=0.0,
            material_markup=0.0,
            general_overhead_rate=0.0,
            contingency_rate=0.0,
            bond_rate=0.0,
            permit_rate=0.0,
            profit_margin=0.0,
        )
        result = compute_totals(lines, config)
        assert abs(result["grand_total"] - 7000.0) < 0.01

    def test_contingency_is_percentage_of_subtotal(self):
        lines = [make_line(material_total=10000.0)]
        config = make_config(
            material_markup=0.0,
            total_burden_rate=0.0,
            general_overhead_rate=0.0,
            contingency_rate=0.05,
            bond_rate=0.0,
            permit_rate=0.0,
            profit_margin=0.0,
        )
        result = compute_totals(lines, config)
        assert abs(result["contingency"] - 500.0) < 0.01

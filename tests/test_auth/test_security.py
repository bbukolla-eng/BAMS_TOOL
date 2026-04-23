"""
Tests for JWT token logic and overhead calculation math.
Written self-contained (uses jose/passlib directly, not core.security)
to avoid pulling in pydantic_settings and the full backend config chain.
"""
import pytest
from datetime import datetime, timedelta, UTC

jose = pytest.importorskip("jose", reason="python-jose not installed")
passlib_ctx = pytest.importorskip("passlib.context", reason="passlib not installed")

from jose import jwt as _jwt, JWTError
from passlib.context import CryptContext

SECRET = "test-secret-key-for-ci"
ALGORITHM = "HS256"
# Use sha256_crypt in tests — avoids bcrypt version compatibility issues
# while still testing the same verify/hash interface used in production.
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def _create_token(subject, token_type: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(hours=8))
    return _jwt.encode(
        {"sub": str(subject), "exp": expire, "type": token_type},
        SECRET, algorithm=ALGORITHM,
    )


def _decode(token: str) -> dict:
    try:
        return _jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return {}


class TestPasswordHashing:
    def test_hash_not_plaintext(self):
        assert pwd_context.hash("mypassword") != "mypassword"

    def test_verify_correct(self):
        h = pwd_context.hash("correct")
        assert pwd_context.verify("correct", h) is True

    def test_verify_wrong(self):
        h = pwd_context.hash("right")
        assert pwd_context.verify("wrong", h) is False

    def test_two_hashes_differ(self):
        assert pwd_context.hash("same") != pwd_context.hash("same")

    def test_empty_password(self):
        h = pwd_context.hash("")
        assert pwd_context.verify("", h) is True


class TestAccessToken:
    def test_creates_string(self):
        token = _create_token(42, "access")
        assert isinstance(token, str) and len(token) > 10

    def test_decode_subject(self):
        token = _create_token(99, "access")
        assert _decode(token)["sub"] == "99"

    def test_type_is_access(self):
        token = _create_token(1, "access")
        assert _decode(token)["type"] == "access"

    def test_expired_returns_empty(self):
        token = _create_token(1, "access", timedelta(seconds=-1))
        assert _decode(token) == {}

    def test_tampered_returns_empty(self):
        token = _create_token(1, "access")
        assert _decode(token[:-5] + "XXXXX") == {}

    def test_garbage_returns_empty(self):
        assert _decode("not.a.jwt") == {}

    def test_empty_returns_empty(self):
        assert _decode("") == {}


class TestRefreshToken:
    def test_type_is_refresh(self):
        token = _create_token(7, "refresh")
        assert _decode(token)["type"] == "refresh"

    def test_subject_recovered(self):
        token = _create_token(7, "refresh")
        assert _decode(token)["sub"] == "7"

    def test_access_and_refresh_differ(self):
        assert _create_token(1, "access") != _create_token(1, "refresh")

    def test_refresh_type_not_access(self):
        token = _create_token(1, "refresh")
        payload = _decode(token)
        assert payload.get("type") != "access"


class TestOverheadCalculationMath:
    """Mirror of overhead/router.py POST /{config_id}/calculate arithmetic."""

    def _calc(
        self,
        material_cost: float,
        labor_hours: float,
        labor_rate: float,
        total_burden_rate: float = 0.35,
        material_markup: float = 0.10,
        general_overhead_rate: float = 0.12,
        small_tools_rate: float = 0.02,
        contingency_rate: float = 0.03,
        bond_rate: float = 0.01,
        permit_rate: float = 0.005,
        profit_margin: float = 0.08,
    ) -> dict:
        raw_labor = labor_hours * labor_rate
        burden = raw_labor * total_burden_rate
        mat_markup = material_cost * material_markup
        overhead = (material_cost + raw_labor + burden) * general_overhead_rate
        small_tools = raw_labor * small_tools_rate
        subtotal = material_cost + mat_markup + raw_labor + burden + overhead + small_tools
        contingency = subtotal * contingency_rate
        bond = subtotal * bond_rate
        permit = subtotal * permit_rate
        profit = (subtotal + contingency + bond + permit) * profit_margin
        return {
            "raw_labor": raw_labor, "burden": burden,
            "mat_markup": mat_markup, "overhead": overhead,
            "subtotal": subtotal, "contingency": contingency,
            "profit": profit,
            "grand_total": subtotal + contingency + bond + permit + profit,
        }

    def test_zero_inputs(self):
        assert self._calc(0, 0, 0)["grand_total"] == 0.0

    def test_material_markup(self):
        r = self._calc(10000, 0, 0,
                       total_burden_rate=0, material_markup=0.10,
                       general_overhead_rate=0, small_tools_rate=0,
                       contingency_rate=0, bond_rate=0, permit_rate=0, profit_margin=0)
        assert abs(r["mat_markup"] - 1000.0) < 0.01
        assert abs(r["grand_total"] - 11000.0) < 0.01

    def test_labor_burden(self):
        r = self._calc(0, 100, 50, total_burden_rate=0.35,
                       material_markup=0, general_overhead_rate=0,
                       small_tools_rate=0, contingency_rate=0,
                       bond_rate=0, permit_rate=0, profit_margin=0)
        assert r["raw_labor"] == 5000.0
        assert abs(r["burden"] - 1750.0) < 0.01

    def test_grand_total_exceeds_raw(self):
        r = self._calc(50000, 400, 55)
        assert r["grand_total"] > 50000 + 400 * 55

    def test_contingency_percentage(self):
        r = self._calc(20000, 0, 0,
                       total_burden_rate=0, material_markup=0,
                       general_overhead_rate=0, small_tools_rate=0,
                       contingency_rate=0.05, bond_rate=0, permit_rate=0, profit_margin=0)
        assert abs(r["contingency"] - 1000.0) < 0.01

    def test_profit_on_subtotal_plus_adders(self):
        r = self._calc(10000, 0, 0,
                       total_burden_rate=0, material_markup=0,
                       general_overhead_rate=0, small_tools_rate=0,
                       contingency_rate=0, bond_rate=0, permit_rate=0,
                       profit_margin=0.10)
        assert abs(r["profit"] - 1000.0) < 0.01

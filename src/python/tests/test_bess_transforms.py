"""Tests for BESS transformers (Sungrow PowerTitan, BYD) — SEP-026."""

import pytest
from pathlib import Path

from odse.transformer import (
    transform,
    SungrowBESSTransformer,
    BYDBESSTransformer,
)
from odse.validator import validate, PROFILES


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Sungrow PowerTitan
# ---------------------------------------------------------------------------

def test_sungrow_bess_charging(fixtures_dir):
    transformer = SungrowBESSTransformer()
    records = transformer.transform(
        fixtures_dir / "sungrow_powertitan_sample.json",
        interval_minutes=5,
        asset_id="za-globeleq:bess:red-sands-pt001",
    )

    assert len(records) == 3

    # First point: charging
    rec0 = records[0]
    assert rec0["asset_id"] == "za-globeleq:bess:red-sands-pt001"
    assert rec0["timestamp"] == "2026-06-27T10:00:00+02:00"
    assert rec0["dispatch_mode"] == "charging"
    assert rec0["soc"] == 42.5
    assert rec0["soh"] == 98.3
    assert rec0["cycle_count"] == 312
    assert rec0["cell_temp_min_c"] == 28.4
    assert rec0["cell_temp_max_c"] == 31.2
    assert rec0["cell_voltage_min_v"] == 3.341
    assert rec0["cell_voltage_max_v"] == 3.352
    # 50 kW * (5/60) h = 4.167 kWh charged
    assert rec0["charge_kWh"] == pytest.approx(50.0 * (5.0 / 60.0))
    assert rec0["discharge_kWh"] == 0.0
    assert rec0["error_type"] == "normal"


def test_sungrow_bess_discharging(fixtures_dir):
    transformer = SungrowBESSTransformer()
    records = transformer.transform(
        fixtures_dir / "sungrow_powertitan_sample.json",
        interval_minutes=5,
    )

    rec1 = records[1]
    assert rec1["dispatch_mode"] == "discharging"
    assert rec1["discharge_kWh"] == pytest.approx(75.0 * (5.0 / 60.0))
    assert rec1["charge_kWh"] == 0.0


def test_sungrow_bess_standby(fixtures_dir):
    transformer = SungrowBESSTransformer()
    records = transformer.transform(
        fixtures_dir / "sungrow_powertitan_sample.json",
        interval_minutes=5,
    )

    rec2 = records[2]
    assert rec2["dispatch_mode"] == "standby"
    assert rec2["charge_kWh"] == 0.0
    assert rec2["discharge_kWh"] == 0.0


def test_sungrow_bess_via_transform_dispatch(fixtures_dir):
    """The public transform() dispatcher should route sungrow_bess correctly."""
    records = transform(
        fixtures_dir / "sungrow_powertitan_sample.json",
        source="sungrow_bess",
        interval_minutes=5,
    )
    assert len(records) == 3
    assert {r["dispatch_mode"] for r in records} == {
        "charging", "discharging", "standby",
    }


def test_sungrow_bess_empty_payload():
    transformer = SungrowBESSTransformer()
    records = transformer.transform('{"device_id": "x", "data_points": []}')
    assert records == []


# ---------------------------------------------------------------------------
# BYD BatteryBox / BMS
# ---------------------------------------------------------------------------

def test_byd_bess_export(fixtures_dir):
    transformer = BYDBESSTransformer()
    records = transformer.transform(
        fixtures_dir / "byd_bess_sample.csv",
        interval_minutes=15,
        asset_id="za-byd:bess:box-001",
    )

    assert len(records) == 3

    rec0 = records[0]
    assert rec0["asset_id"] == "za-byd:bess:box-001"
    assert rec0["timestamp"] == "2026-06-27T10:00:00Z"
    assert rec0["dispatch_mode"] == "charging"
    assert rec0["soc"] == 55.0
    assert rec0["soh"] == 97.5
    assert rec0["cycle_count"] == 540
    assert rec0["cell_temp_min_c"] == 27.1
    assert rec0["cell_temp_max_c"] == 29.8
    assert rec0["cell_voltage_min_v"] == 3.321
    assert rec0["cell_voltage_max_v"] == 3.340
    # 40 kW * (15/60) h = 10 kWh charged
    assert rec0["charge_kWh"] == pytest.approx(40.0 * (15.0 / 60.0))
    assert rec0["discharge_kWh"] == 0.0
    assert rec0["error_type"] == "normal"

    rec1 = records[1]
    assert rec1["dispatch_mode"] == "discharging"
    assert rec1["discharge_kWh"] == pytest.approx(60.0 * (15.0 / 60.0))

    rec2 = records[2]
    assert rec2["dispatch_mode"] == "standby"
    assert rec2["error_type"] == "standby"


def test_byd_bess_via_transform_dispatch(fixtures_dir):
    records = transform(
        fixtures_dir / "byd_bess_sample.csv",
        source="byd_bess",
        interval_minutes=15,
    )
    assert len(records) == 3


# ---------------------------------------------------------------------------
# Schema validation of transformer output
# ---------------------------------------------------------------------------

def test_bess_output_schema_valid(fixtures_dir):
    transformer = SungrowBESSTransformer()
    records = transformer.transform(
        fixtures_dir / "sungrow_powertitan_sample.json",
        interval_minutes=5,
    )
    for rec in records:
        result = validate(rec)
        assert not result.errors, f"Schema errors: {result.errors}"


# ---------------------------------------------------------------------------
# bess_dispatch conformance profile
# ---------------------------------------------------------------------------

def test_bess_dispatch_profile_registered():
    assert "bess_dispatch" in PROFILES


def test_bess_dispatch_profile_valid(fixtures_dir):
    transformer = SungrowBESSTransformer()
    records = transformer.transform(
        fixtures_dir / "sungrow_powertitan_sample.json",
        interval_minutes=5,
    )
    for rec in records:
        result = validate(rec, profile="bess_dispatch")
        assert not result.errors, f"Profile errors: {result.errors}"


def test_bess_dispatch_profile_missing_soc():
    rec = {
        "timestamp": "2026-06-27T10:00:00+02:00",
        "kWh": 4.167,
        "error_type": "normal",
        "dispatch_mode": "charging",
    }
    result = validate(rec, profile="bess_dispatch")
    codes = [e.code for e in result.errors]
    assert "PROFILE_FIELD_MISSING" in codes


def test_bess_dispatch_profile_missing_mode():
    rec = {
        "timestamp": "2026-06-27T10:00:00+02:00",
        "kWh": 4.167,
        "error_type": "normal",
        "soc": 50.0,
    }
    result = validate(rec, profile="bess_dispatch")
    codes = [e.code for e in result.errors]
    assert "PROFILE_FIELD_MISSING" in codes


def test_bess_dispatch_mode_invalid_enum():
    rec = {
        "timestamp": "2026-06-27T10:00:00+02:00",
        "kWh": 4.167,
        "error_type": "normal",
        "soc": 50.0,
        "dispatch_mode": "fast_charging",
    }
    result = validate(rec)
    codes = [e.code for e in result.errors]
    assert "ENUM_MISMATCH" in codes


def test_cell_voltage_bounds():
    rec = {
        "timestamp": "2026-06-27T10:00:00+02:00",
        "kWh": 4.167,
        "error_type": "normal",
        "cell_voltage_min_v": -1.0,
    }
    result = validate(rec)
    codes = [e.code for e in result.errors]
    assert "OUT_OF_BOUNDS" in codes

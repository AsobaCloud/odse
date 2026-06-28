"""Tests for wind turbine SCADA transformers (Vestas, Siemens Gamesa, Nordex) — SEP-025."""

import pytest
from pathlib import Path

from odse.transformer import (
    transform,
    VestasTransformer,
    SiemensGamesaTransformer,
    NordexTransformer,
)
from odse.validator import validate, PROFILES


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Vestas Online
# ---------------------------------------------------------------------------

def test_vestas_production(fixtures_dir):
    transformer = VestasTransformer()
    records = transformer.transform(
        fixtures_dir / "vestas_online_sample.csv",
        interval_minutes=10,
        asset_id="za-globeleq:wind:vestas-001",
    )

    assert len(records) == 3

    rec0 = records[0]
    assert rec0["asset_id"] == "za-globeleq:wind:vestas-001"
    assert rec0["timestamp"] == "2026-06-27T10:00:00+00:00"
    assert rec0["error_type"] == "normal"
    assert rec0["wind_speed_ms"] == 9.5
    assert rec0["rotor_rpm"] == 14.2
    assert rec0["nacelle_direction_deg"] == 270.5
    assert rec0["blade_pitch_deg"] == 4.5
    assert rec0["kW"] == 1800.0
    # 1800 kW * (10/60) h = 300 kWh
    assert rec0["kWh"] == pytest.approx(1800.0 * (10.0 / 60.0))


def test_vestas_standby(fixtures_dir):
    transformer = VestasTransformer()
    records = transformer.transform(
        fixtures_dir / "vestas_online_sample.csv",
        interval_minutes=10,
    )

    rec1 = records[1]
    assert rec1["error_type"] == "standby"
    assert rec1["kWh"] == 0.0
    assert rec1["wind_speed_ms"] == 2.8
    assert rec1["blade_pitch_deg"] == 85.0


def test_vestas_fault(fixtures_dir):
    transformer = VestasTransformer()
    records = transformer.transform(
        fixtures_dir / "vestas_online_sample.csv",
        interval_minutes=10,
    )

    rec2 = records[2]
    assert rec2["error_type"] == "fault"
    assert rec2["kWh"] == 0.0
    assert rec2["rotor_rpm"] == 0.0


def test_vestas_via_transform_dispatch(fixtures_dir):
    records = transform(
        fixtures_dir / "vestas_online_sample.csv",
        source="vestas",
        interval_minutes=10,
    )
    assert len(records) == 3
    assert {r["error_type"] for r in records} == {"normal", "standby", "fault"}


def test_vestas_empty_payload():
    transformer = VestasTransformer()
    records = transformer.transform("timestamp,active_power_kw,wind_speed\n")
    assert records == []


# ---------------------------------------------------------------------------
# Siemens Gamesa Diagnostic System
# ---------------------------------------------------------------------------

def test_siemens_gamesa_production(fixtures_dir):
    transformer = SiemensGamesaTransformer()
    records = transformer.transform(
        fixtures_dir / "siemens_gamesa_sample.csv",
        interval_minutes=10,
        asset_id="za-globeleq:wind:sgre-001",
    )

    assert len(records) == 3

    rec0 = records[0]
    assert rec0["asset_id"] == "za-globeleq:wind:sgre-001"
    assert rec0["timestamp"] == "2026-06-27T10:00:00+00:00"
    assert rec0["error_type"] == "normal"
    assert rec0["wind_speed_ms"] == 8.7
    assert rec0["rotor_rpm"] == 13.5
    assert rec0["blade_pitch_deg"] == 3.2
    assert rec0["kW"] == 2100.0
    assert rec0["kVAr"] == 300.0
    assert rec0["kWh"] == pytest.approx(2100.0 * (10.0 / 60.0))


def test_siemens_gamesa_warning(fixtures_dir):
    transformer = SiemensGamesaTransformer()
    records = transformer.transform(
        fixtures_dir / "siemens_gamesa_sample.csv",
        interval_minutes=10,
    )

    rec1 = records[1]
    assert rec1["error_type"] == "warning"
    assert rec1["wind_speed_ms"] == 5.2
    assert rec1["kW"] == 800.0


def test_siemens_gamesa_offline(fixtures_dir):
    transformer = SiemensGamesaTransformer()
    records = transformer.transform(
        fixtures_dir / "siemens_gamesa_sample.csv",
        interval_minutes=10,
    )

    rec2 = records[2]
    assert rec2["error_type"] == "offline"
    # wind_speed_nacelle and wind_speed_metmast are empty in the fixture
    assert "wind_speed_ms" not in rec2


def test_siemens_gamesa_via_transform_dispatch(fixtures_dir):
    records = transform(
        fixtures_dir / "siemens_gamesa_sample.csv",
        source="siemens_gamesa",
        interval_minutes=10,
    )
    assert len(records) == 3


def test_siemens_gamesa_empty_payload():
    transformer = SiemensGamesaTransformer()
    records = transformer.transform("timestamp,active_power_kw,availability_status\n")
    assert records == []


# ---------------------------------------------------------------------------
# Nordex Control
# ---------------------------------------------------------------------------

def test_nordex_production(fixtures_dir):
    transformer = NordexTransformer()
    records = transformer.transform(
        fixtures_dir / "nordex_control_sample.csv",
        interval_minutes=10,
        asset_id="za-globeleq:wind:nordex-001",
    )

    assert len(records) == 3

    rec0 = records[0]
    assert rec0["asset_id"] == "za-globeleq:wind:nordex-001"
    assert rec0["timestamp"] == "2026-06-27T10:00:00+00:00"
    assert rec0["error_type"] == "normal"
    assert rec0["wind_speed_ms"] == 7.8
    assert rec0["rotor_rpm"] == 12.5
    assert rec0["blade_pitch_deg"] == 5.0
    assert rec0["kW"] == 1500.0
    assert rec0["kWh"] == pytest.approx(1500.0 * (10.0 / 60.0))


def test_nordex_paused(fixtures_dir):
    transformer = NordexTransformer()
    records = transformer.transform(
        fixtures_dir / "nordex_control_sample.csv",
        interval_minutes=10,
    )

    rec1 = records[1]
    assert rec1["error_type"] == "standby"
    assert rec1["kWh"] == 0.0
    assert rec1["wind_speed_ms"] == 3.0


def test_nordex_fault(fixtures_dir):
    transformer = NordexTransformer()
    records = transformer.transform(
        fixtures_dir / "nordex_control_sample.csv",
        interval_minutes=10,
    )

    rec2 = records[2]
    assert rec2["error_type"] == "fault"
    assert rec2["kWh"] == 0.0
    assert rec2["rotor_rpm"] == 0.0


def test_nordex_via_transform_dispatch(fixtures_dir):
    records = transform(
        fixtures_dir / "nordex_control_sample.csv",
        source="nordex",
        interval_minutes=10,
    )
    assert len(records) == 3


def test_nordex_empty_payload():
    transformer = NordexTransformer()
    records = transformer.transform("timestamp,active_power_kw,turbine_status\n")
    assert records == []


# ---------------------------------------------------------------------------
# Schema validation of transformer output
# ---------------------------------------------------------------------------

def test_wind_output_schema_valid(fixtures_dir):
    for fixture_name, source in [
        ("vestas_online_sample.csv", "vestas"),
        ("siemens_gamesa_sample.csv", "siemens_gamesa"),
        ("nordex_control_sample.csv", "nordex"),
    ]:
        records = transform(
            fixtures_dir / fixture_name,
            source=source,
            interval_minutes=10,
        )
        for rec in records:
            result = validate(rec)
            assert not result.errors, f"{source}: Schema errors: {result.errors}"


# ---------------------------------------------------------------------------
# wind_scada conformance profile
# ---------------------------------------------------------------------------

def test_wind_scada_profile_registered():
    assert "wind_scada" in PROFILES


def test_wind_scada_profile_valid(fixtures_dir):
    records = transform(
        fixtures_dir / "vestas_online_sample.csv",
        source="vestas",
        interval_minutes=10,
    )
    # First two records have wind_speed_ms; third (fault) also has it
    for rec in records:
        result = validate(rec, profile="wind_scada")
        assert not result.errors, f"Profile errors: {result.errors}"


def test_wind_scada_profile_missing_wind_speed():
    rec = {
        "timestamp": "2026-06-27T10:00:00Z",
        "kWh": 300.0,
        "error_type": "normal",
        "rotor_rpm": 14.2,
    }
    result = validate(rec, profile="wind_scada")
    codes = [e.code for e in result.errors]
    assert "PROFILE_FIELD_MISSING" in codes


# ---------------------------------------------------------------------------
# Wind field bounds
# ---------------------------------------------------------------------------

def test_wind_speed_bounds():
    rec = {
        "timestamp": "2026-06-27T10:00:00Z",
        "kWh": 300.0,
        "error_type": "normal",
        "wind_speed_ms": -1.5,
    }
    result = validate(rec)
    codes = [e.code for e in result.errors]
    assert "OUT_OF_BOUNDS" in codes


def test_nacelle_direction_bounds():
    rec = {
        "timestamp": "2026-06-27T10:00:00Z",
        "kWh": 300.0,
        "error_type": "normal",
        "nacelle_direction_deg": 370.0,
    }
    result = validate(rec)
    codes = [e.code for e in result.errors]
    assert "OUT_OF_BOUNDS" in codes


def test_rotor_rpm_bounds():
    rec = {
        "timestamp": "2026-06-27T10:00:00Z",
        "kWh": 300.0,
        "error_type": "normal",
        "rotor_rpm": -5.0,
    }
    result = validate(rec)
    codes = [e.code for e in result.errors]
    assert "OUT_OF_BOUNDS" in codes

"""Tests for Terraco SCADA historian transformer — SEP-021."""

import json
import pytest
from pathlib import Path

from odse.transformer import transform, TerracoTransformer
from odse.validator import validate


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# JSON mode (REST API response)
# ---------------------------------------------------------------------------

def test_terraco_json_production(fixtures_dir):
    transformer = TerracoTransformer()
    records = transformer.transform(
        fixtures_dir / "terraco_rest_sample.json",
        interval_minutes=10,
        asset_id="za-globeleq:wind:jbay-001",
    )

    assert len(records) == 3

    rec0 = records[0]
    assert rec0["asset_id"] == "za-globeleq:wind:jbay-001"
    assert rec0["timestamp"] == "2026-06-27T10:00:00+02:00"
    assert rec0["error_type"] == "normal"
    assert rec0["kW"] == 1800.0
    assert rec0["kWh"] == 300.0
    assert rec0["temperature"] == 45.2
    assert rec0["voltage_ac"] == 400.0
    assert rec0["current_ac"] == 12.5
    assert rec0["frequency"] == 50.0
    assert rec0["kVAr"] == 300.0
    assert rec0["PF"] == 0.98


def test_terraco_json_standby(fixtures_dir):
    transformer = TerracoTransformer()
    records = transformer.transform(
        fixtures_dir / "terraco_rest_sample.json",
        interval_minutes=10,
    )

    rec1 = records[1]
    assert rec1["error_type"] == "standby"
    assert rec1["kWh"] == 0.0
    assert rec1["kW"] == 0.0


def test_terraco_json_fault(fixtures_dir):
    transformer = TerracoTransformer()
    records = transformer.transform(
        fixtures_dir / "terraco_rest_sample.json",
        interval_minutes=10,
    )

    rec2 = records[2]
    assert rec2["error_type"] == "fault"
    assert rec2["kWh"] == 0.0


# ---------------------------------------------------------------------------
# CSV mode (export)
# ---------------------------------------------------------------------------

def test_terraco_csv_production(fixtures_dir):
    transformer = TerracoTransformer()
    records = transformer.transform(
        fixtures_dir / "terraco_csv_sample.csv",
        interval_minutes=10,
        asset_id="za-globeleq:wind:jbay-001",
    )

    assert len(records) == 3

    rec0 = records[0]
    assert rec0["asset_id"] == "za-globeleq:wind:jbay-001"
    assert rec0["timestamp"] == "2026-06-27T10:00:00+02:00"
    assert rec0["error_type"] == "normal"
    assert rec0["kW"] == 1800.0
    assert rec0["kWh"] == 300.0
    assert rec0["temperature"] == 45.2
    assert rec0["voltage_ac"] == 400.0
    assert rec0["current_ac"] == 12.5
    assert rec0["frequency"] == 50.0
    assert rec0["kVAr"] == 300.0
    assert rec0["PF"] == 0.98


def test_terraco_csv_standby(fixtures_dir):
    transformer = TerracoTransformer()
    records = transformer.transform(
        fixtures_dir / "terraco_csv_sample.csv",
        interval_minutes=10,
    )

    rec1 = records[1]
    assert rec1["error_type"] == "standby"
    assert rec1["kWh"] == 0.0


def test_terraco_csv_fault(fixtures_dir):
    transformer = TerracoTransformer()
    records = transformer.transform(
        fixtures_dir / "terraco_csv_sample.csv",
        interval_minutes=10,
    )

    rec2 = records[2]
    assert rec2["error_type"] == "fault"
    assert rec2["kWh"] == 0.0


# ---------------------------------------------------------------------------
# Dispatcher routing
# ---------------------------------------------------------------------------

def test_terraco_via_transform_dispatch_json(fixtures_dir):
    records = transform(
        fixtures_dir / "terraco_rest_sample.json",
        source="terraco",
        interval_minutes=10,
    )
    assert len(records) == 3
    assert {r["error_type"] for r in records} == {"normal", "standby", "fault"}


def test_terraco_via_transform_dispatch_csv(fixtures_dir):
    records = transform(
        fixtures_dir / "terraco_csv_sample.csv",
        source="terraco",
        interval_minutes=10,
    )
    assert len(records) == 3


def test_terraco_historian_alias(fixtures_dir):
    records = transform(
        fixtures_dir / "terraco_rest_sample.json",
        source="terraco-historian",
        interval_minutes=10,
    )
    assert len(records) == 3


# ---------------------------------------------------------------------------
# Empty payload handling
# ---------------------------------------------------------------------------

def test_terraco_empty_json():
    transformer = TerracoTransformer()
    records = transformer.transform('{"data": []}')
    assert records == []


def test_terraco_empty_csv():
    transformer = TerracoTransformer()
    records = transformer.transform(
        "timestamp,JBAY.ActivePower,JBAY.Status\n"
    )
    assert records == []


# ---------------------------------------------------------------------------
# Tag pattern matching
# ---------------------------------------------------------------------------

def test_terraco_tag_patterns_different_prefixes():
    """Various asset prefixes should all map correctly via suffix matching."""
    transformer = TerracoTransformer()
    payload = json.dumps({
        "data": [
            {
                "timestamp": "2026-06-27T10:00:00+02:00",
                "values": {
                    "SOLARPK.ActivePower": 2500.0,
                    "SOLARPK.ActiveEnergy": 416.7,
                    "SOLARPK.Status": 1,
                },
            }
        ]
    })
    records = transformer.transform(payload, interval_minutes=10)
    assert len(records) == 1
    rec = records[0]
    assert rec["kW"] == 2500.0
    assert rec["kWh"] == 416.7
    assert rec["error_type"] == "normal"


def test_terraco_tag_patterns_case_insensitive():
    """Tag suffixes should match case-insensitively."""
    transformer = TerracoTransformer()
    payload = json.dumps({
        "data": [
            {
                "timestamp": "2026-06-27T10:00:00+02:00",
                "values": {
                    "JBAY.activepower": 1800.0,
                    "JBAY.ACTIVEENERGY": 300.0,
                    "JBAY.status": 1,
                },
            }
        ]
    })
    records = transformer.transform(payload, interval_minutes=10)
    assert len(records) == 1
    rec = records[0]
    assert rec["kW"] == 1800.0
    assert rec["kWh"] == 300.0
    assert rec["error_type"] == "normal"


def test_terraco_kw_alias_tag():
    """The 'kW' tag suffix should map to ODS-E kW field."""
    transformer = TerracoTransformer()
    payload = json.dumps({
        "data": [
            {
                "timestamp": "2026-06-27T10:00:00+02:00",
                "values": {
                    "JBAY.kW": 1800.0,
                    "JBAY.kWh": 300.0,
                    "JBAY.State": 1,
                },
            }
        ]
    })
    records = transformer.transform(payload, interval_minutes=10)
    assert len(records) == 1
    rec = records[0]
    assert rec["kW"] == 1800.0
    assert rec["kWh"] == 300.0
    assert rec["error_type"] == "normal"


# ---------------------------------------------------------------------------
# kWh fallback from power × interval
# ---------------------------------------------------------------------------

def test_terraco_kwh_fallback_from_power():
    """When ActiveEnergy is absent, kWh should be computed from power × interval."""
    transformer = TerracoTransformer()
    payload = json.dumps({
        "data": [
            {
                "timestamp": "2026-06-27T10:00:00+02:00",
                "values": {
                    "JBAY.ActivePower": 1800.0,
                    "JBAY.Status": 1,
                },
            }
        ]
    })
    records = transformer.transform(payload, interval_minutes=10)
    assert len(records) == 1
    rec = records[0]
    assert rec["kW"] == 1800.0
    # 1800 kW * (10/60) h = 300 kWh
    assert rec["kWh"] == pytest.approx(1800.0 * (10.0 / 60.0))


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_terraco_output_schema_valid(fixtures_dir):
    for fixture_name in ["terraco_rest_sample.json", "terraco_csv_sample.csv"]:
        records = transform(
            fixtures_dir / fixture_name,
            source="terraco",
            interval_minutes=10,
        )
        for rec in records:
            result = validate(rec)
            assert not result.errors, f"{fixture_name}: Schema errors: {result.errors}"

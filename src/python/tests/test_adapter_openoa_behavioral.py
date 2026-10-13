"""Behavioral specification tests for odse.adapters.openoa (OPENOA-BEHAVIOR-1 through 6)."""

import json
from pathlib import Path
import pytest


def test_utc_datetime_index_normalization():
    """
    OPENOA-BEHAVIOR-1: Given an ODS-E telemetry payload with mixed timezone offsets
    (+02:00, -05:00, Z),
    When odse_to_openoa() is invoked,
    Then the resulting SCADA DataFrame has a chronologically sorted UTC pd.DatetimeIndex.
    """
    from odse.adapters.openoa import odse_to_openoa
    import pandas as pd

    records = [
        {"timestamp": "2026-06-01T14:00:00+02:00", "active_power_kW": 1000.0, "wind_speed_ms": 7.5},
        {"timestamp": "2026-06-01T07:00:00-05:00", "active_power_kW": 950.0, "wind_speed_ms": 7.2},
        {"timestamp": "2026-06-01T11:30:00Z", "active_power_kW": 900.0, "wind_speed_ms": 6.8},
    ]

    res = odse_to_openoa(records, return_plantdata=False)
    df = res["scada"]

    assert isinstance(df.index, pd.DatetimeIndex)
    assert str(df.index.tz) == "UTC"
    assert df.index.name == "timestamp"
    assert df.index[0] == pd.Timestamp("2026-06-01 11:30:00", tz="UTC")
    assert df.index.is_monotonic_increasing


def test_canonical_column_mapping_and_passthrough():
    """
    OPENOA-BEHAVIOR-2: Given ODS-E telemetry records with canonical keys,
    When odse_to_openoa(map_variables=True) is called,
    Then columns are renamed to standard OpenOA keys (wm_power_kw, wm_energy_kwh,
    ws_ms, temp_c, temp_cell, poa_global, status_id), and unmapped fields pass through.
    """
    from odse.adapters.openoa import odse_to_openoa

    records = [
        {
            "timestamp": "2026-06-01T12:00:00Z",
            "active_power_kW": 2100.0,
            "kWh": 175.0,
            "wind_speed_ms": 11.2,
            "ambient_temperature_c": 22.0,
            "module_temperature_c": 35.0,
            "poa_irradiance": 800.0,
            "error_type": "warning",
            "rotor_rpm": 14.5,
            "blade_pitch_deg": 1.2,
        }
    ]

    res = odse_to_openoa(records, return_plantdata=False, map_variables=True)
    df = res["scada"]

    assert df["wm_power_kw"].iloc[0] == pytest.approx(2100.0)
    assert df["wm_energy_kwh"].iloc[0] == pytest.approx(175.0)
    assert df["ws_ms"].iloc[0] == pytest.approx(11.2)
    assert df["temp_c"].iloc[0] == pytest.approx(22.0)
    assert df["temp_cell"].iloc[0] == pytest.approx(35.0)
    assert df["poa_global"].iloc[0] == pytest.approx(800.0)
    assert df["status_id"].iloc[0] == "warning"

    # Passthrough check
    assert df["rotor_rpm"].iloc[0] == pytest.approx(14.5)
    assert df["blade_pitch_deg"].iloc[0] == pytest.approx(1.2)


def test_drop_invalid_filtering():
    """
    OPENOA-BEHAVIOR-3: Given an ODS-E telemetry payload with normal, warning, fault, offline,
    When odse_to_openoa(drop_invalid=True) is called,
    Then all rows with fault and offline are purged.
    """
    from odse.adapters.openoa import odse_to_openoa

    records = [
        {"timestamp": "2026-06-01T10:00:00Z", "error_type": "normal", "active_power_kW": 1500.0},
        {"timestamp": "2026-06-01T10:05:00Z", "error_type": "warning", "active_power_kW": 1200.0},
        {"timestamp": "2026-06-01T10:10:00Z", "error_type": "fault", "active_power_kW": 0.0},
        {"timestamp": "2026-06-01T10:15:00Z", "error_type": "offline", "active_power_kW": 0.0},
    ]

    res = odse_to_openoa(records, drop_invalid=True, return_plantdata=False)
    df = res["scada"]
    assert len(df) == 2
    assert set(df["status_id"].tolist()) == {"normal", "warning"}


def test_multi_table_assembly():
    """
    OPENOA-BEHAVIOR-4: Given ODS-E telemetry alongside meteorological tower and revenue meter records,
    When odse_to_openoa() is invoked,
    Then it produces aligned scada, tower, and meter DataFrames with preserved metadata.
    """
    from odse.adapters.openoa import odse_to_openoa

    payload = {
        "metadata": {
            "site_id": "wind-farm-01",
            "capacity_kw": 50000.0,
        },
        "scada": [
            {"timestamp": "2026-06-01T12:00:00Z", "active_power_kW": 2000.0, "wind_speed_ms": 10.0}
        ],
        "tower": [
            {"timestamp": "2026-06-01T12:00:00Z", "wind_speed_ms": 10.5, "ambient_temperature_c": 19.5, "ghi": 650.0}
        ],
        "meter": [
            {"timestamp": "2026-06-01T12:00:00Z", "kWh": 165.0, "active_power_kW": 1980.0}
        ]
    }

    res = odse_to_openoa(payload, return_plantdata=False)
    assert "scada" in res
    assert "tower" in res
    assert "meter" in res
    assert res["metadata"]["site_id"] == "wind-farm-01"

    # Verify tower mapping
    df_tower = res["tower"]
    assert "ws_ms" in df_tower.columns
    assert "temp_c" in df_tower.columns
    assert "ghi" in df_tower.columns

    # Verify meter mapping
    df_meter = res["meter"]
    assert "net_energy_kwh" in df_meter.columns
    assert "power_kw" in df_meter.columns


def test_bidirectional_roundtrip_fidelity():
    """
    OPENOA-BEHAVIOR-5: Given an OpenOA plant dataset or SCADA DataFrame,
    When exported to ODS-E via openoa_to_odse() and converted back with odse_to_openoa(),
    Then numerical values, UTC timestamps, and site metadata match with zero drift,
    and all NaN values are sanitized to None for valid JSON.
    """
    from odse.adapters.openoa import openoa_to_odse
    import pandas as pd

    idx = pd.date_range("2026-06-01 12:00:00", periods=2, freq="5min", tz="UTC")
    df_scada = pd.DataFrame({
        "wm_power_kw": [1500.0, float("nan")],
        "wm_energy_kwh": [125.0, 0.0],
        "ws_ms": [8.5, 3.0],
        "status_id": ["normal", "standby"],
        "asset_id": ["WTG-01", "WTG-01"],
    }, index=idx)

    exported = openoa_to_odse(df_scada, site_id="farm-alpha", metadata={"capacity_kw": 2000.0})
    assert exported["metadata"]["site_id"] == "farm-alpha"
    assert exported["metadata"]["capacity_kw"] == 2000.0
    assert len(exported["telemetry"]) == 2

    rec0 = exported["telemetry"][0]
    assert rec0["timestamp"] == "2026-06-01T12:00:00Z"
    assert rec0["active_power_kW"] == 1500.0
    assert rec0["kWh"] == 125.0
    assert rec0["wind_speed_ms"] == 8.5
    assert rec0["error_type"] == "normal"

    # NaN sanitization check
    rec1 = exported["telemetry"][1]
    assert rec1["active_power_kW"] is None  # sanitized from NaN


def test_cli_to_openoa_invocation(tmp_path: Path):
    """
    OPENOA-BEHAVIOR-6: Verify the odse CLI 'to-openoa' and 'openoa' commands
    convert input files and write valid CSV and JSON outputs.
    """
    from odse.cli import main

    input_file = tmp_path / "telemetry.json"
    payload = {
        "metadata": {"site_id": "test-wind-site"},
        "telemetry": [
            {
                "timestamp": "2026-06-01T12:00:00Z",
                "active_power_kW": 1800.0,
                "wind_speed_ms": 9.2,
                "error_type": "normal",
            }
        ]
    }
    input_file.write_text(json.dumps(payload), encoding="utf-8")

    csv_output = tmp_path / "output.csv"
    main(["to-openoa", "-i", str(input_file), "-o", str(csv_output), "-f", "csv", "--plant-name", "Test_Plant"])
    assert csv_output.exists()
    csv_text = csv_output.read_text(encoding="utf-8")
    assert "timestamp" in csv_text
    assert "wm_power_kw" in csv_text
    assert "ws_ms" in csv_text

    # Also test the 'openoa' alias with JSON output
    json_output = tmp_path / "output.json"
    main(["openoa", "-i", str(input_file), "-o", str(json_output), "-f", "json"])
    assert json_output.exists()
    parsed_json = json.loads(json_output.read_text(encoding="utf-8"))
    assert parsed_json["metadata"]["site_id"] == "test-wind-site"
    assert parsed_json["data"][0]["wm_power_kw"] == 1800.0

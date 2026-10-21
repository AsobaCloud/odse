"""Behavioral specification tests for odse.adapters.pvlib (PVLIB-BEHAVIOR-1 through 6)."""

import json
from pathlib import Path
import pytest


def test_utc_datetime_index_normalization(tmp_path: Path):
    """
    PVLIB-BEHAVIOR-1: Given an ODS-E telemetry payload containing timestamps
    with varying timezone offsets (+02:00, -05:00, Z),
    When odse_to_pvlib() is invoked,
    Then it returns a pd.DataFrame with a UTC DatetimeIndex sorted chronologically.
    """
    from odse.adapters.pvlib import odse_to_pvlib

    records = [
        {"timestamp": "2026-06-01T14:00:00+02:00", "active_power_kW": 10.0},
        {"timestamp": "2026-06-01T07:00:00-05:00", "active_power_kW": 9.0},
        {"timestamp": "2026-06-01T11:30:00Z", "active_power_kW": 8.0},
    ]
    # In UTC:
    # 2026-06-01T14:00:00+02:00 = 12:00:00 UTC
    # 2026-06-01T07:00:00-05:00 = 12:00:00 UTC (tied/same)
    # 2026-06-01T11:30:00Z       = 11:30:00 UTC (earliest)

    df, meta = odse_to_pvlib(records)

    import pandas as pd
    assert isinstance(df.index, pd.DatetimeIndex)
    assert str(df.index.tz) == "UTC"
    assert df.index.name == "timestamp"
    # Ensure sorted order
    assert df.index[0] == pd.Timestamp("2026-06-01 11:30:00", tz="UTC")
    assert df.index.is_monotonic_increasing


def test_column_mapping_accuracy_and_passthrough():
    """
    PVLIB-BEHAVIOR-2: Given ODS-E records containing canonical keys,
    When odse_to_pvlib(map_variables=True) is invoked,
    Then all 11 defined keys map to standard pvlib column names,
    and unmapped custom fields pass through without loss.
    """
    from odse.adapters.pvlib import odse_to_pvlib

    records = [
        {
            "timestamp": "2026-06-01T12:00:00Z",
            "active_power_kW": 12.5,
            "kWh": 1.04,
            "poa_irradiance": 850.0,
            "ghi": 900.0,
            "dni": 750.0,
            "dhi": 150.0,
            "ambient_temperature_c": 26.5,
            "module_temperature_c": 48.2,
            "wind_speed_ms": 3.2,
            "dc_voltage_v": 620.0,
            "dc_current_a": 20.1,
            # Custom / unmapped field
            "custom_string_id": "INV-A-1",
            "soc": 95.0,
        }
    ]

    df, meta = odse_to_pvlib(records, map_variables=True)

    expected_mappings = {
        "p_mp": 12.5,
        "ac_energy": 1.04,
        "poa_global": 850.0,
        "ghi": 900.0,
        "dni": 750.0,
        "dhi": 150.0,
        "temp_air": 26.5,
        "temp_cell": 48.2,
        "wind_speed": 3.2,
        "v_dc": 620.0,
        "i_dc": 20.1,
    }

    for col, val in expected_mappings.items():
        assert col in df.columns, f"Expected column {col} missing from mapped DataFrame"
        assert df[col].iloc[0] == pytest.approx(val)

    # Verify passthrough of unmapped columns
    assert "custom_string_id" in df.columns
    assert df["custom_string_id"].iloc[0] == "INV-A-1"
    assert "soc" in df.columns
    assert df["soc"].iloc[0] == 95.0


def test_drop_invalid_fault_offline_filtering():
    """
    PVLIB-BEHAVIOR-3: Given an ODS-E payload with normal, warning, fault, offline records,
    When odse_to_pvlib(drop_invalid=True) is invoked,
    Then rows with 'fault' or 'offline' are purged, while 'normal' and 'warning' remain.
    """
    from odse.adapters.pvlib import odse_to_pvlib

    records = [
        {"timestamp": "2026-06-01T10:00:00Z", "error_type": "normal", "active_power_kW": 10.0},
        {"timestamp": "2026-06-01T10:05:00Z", "error_type": "warning", "active_power_kW": 8.0},
        {"timestamp": "2026-06-01T10:10:00Z", "error_type": "fault", "active_power_kW": 0.0},
        {"timestamp": "2026-06-01T10:15:00Z", "error_type": "offline", "active_power_kW": 0.0},
    ]

    df, _ = odse_to_pvlib(records, drop_invalid=True)
    assert len(df) == 2
    assert set(df["error_type"].tolist()) == {"normal", "warning"}


def test_e2e_pvlib_pvsyst_cell_temperature_model():
    """
    PVLIB-BEHAVIOR-4: Given realistic ODS-E solar irradiance and ambient temperature data,
    When converted via odse_to_pvlib() and passed directly to pvlib.temperature.pvsyst_cell,
    Then cell temperatures are calculated accurately without runtime exceptions.
    """
    pvlib = pytest.importorskip("pvlib")
    from odse.adapters.pvlib import odse_to_pvlib

    records = [
        {
            "timestamp": f"2026-06-01T1{hour}:00:00Z",
            "poa_irradiance": poa,
            "ambient_temperature_c": temp,
            "wind_speed_ms": wind,
        }
        for hour, (poa, temp, wind) in enumerate([
            (200.0, 20.0, 1.5),
            (600.0, 25.0, 2.0),
            (950.0, 30.0, 2.5),
            (700.0, 29.0, 3.0),
        ])
    ]

    df, _ = odse_to_pvlib(records, map_variables=True)

    cell_temp = pvlib.temperature.pvsyst_cell(
        poa_global=df["poa_global"],
        temp_air=df["temp_air"],
        wind_speed=df["wind_speed"],
    )

    assert len(cell_temp) == 4
    # Cell temp under 950 W/m2 and 30C ambient must exceed ambient temperature
    assert cell_temp.iloc[2] > 30.0
    assert cell_temp.iloc[2] < 75.0


def test_bidirectional_roundtrip_fidelity():
    """
    PVLIB-BEHAVIOR-5: Given an ODS-E envelope dict,
    When converted to pvlib DataFrame and back to ODS-E via pvlib_to_odse(),
    Then field values, chronological timestamps, and site metadata match with zero drift.
    """
    from odse.adapters.pvlib import odse_to_pvlib, pvlib_to_odse

    original_payload = {
        "metadata": {
            "site_id": "solar-park-01",
            "capacity_kw": 5000.0,
        },
        "telemetry": [
            {
                "timestamp": "2026-06-01T12:00:00Z",
                "active_power_kW": 4500.0,
                "kWh": 375.0,
                "poa_irradiance": 920.0,
                "ambient_temperature_c": 28.5,
                "module_temperature_c": 52.0,
            },
            {
                "timestamp": "2026-06-01T12:05:00Z",
                "active_power_kW": 4550.0,
                "kWh": 379.0,
                "poa_irradiance": 930.0,
                "ambient_temperature_c": 28.8,
                "module_temperature_c": 52.5,
            },
        ],
    }

    df, meta = odse_to_pvlib(original_payload)
    assert meta["site_id"] == "solar-park-01"

    exported = pvlib_to_odse(df, site_id="solar-park-01", metadata=meta)

    assert exported["metadata"]["site_id"] == "solar-park-01"
    assert exported["metadata"]["schema_version"] == "ODS-E-1.0"
    assert exported["metadata"]["capacity_kw"] == 5000.0
    assert len(exported["telemetry"]) == 2

    # Check first record fidelity
    rec0 = exported["telemetry"][0]
    assert rec0["timestamp"] == "2026-06-01T12:00:00Z"
    assert rec0["kW"] == 4500.0
    assert rec0["kWh"] == 375.0
    assert rec0["poa_irradiance"] == 920.0
    assert rec0["ambient_temperature_c"] == 28.5
    assert rec0["module_temperature_c"] == 52.0


def test_pvlib_to_odse_unnamed_datetimeindex():
    """
    Verify pvlib_to_odse works cleanly even when the DataFrame DatetimeIndex has no name.
    """
    from odse.adapters.pvlib import pvlib_to_odse
    import pandas as pd

    idx = pd.date_range("2026-06-01 10:00:00", periods=3, freq="5min", tz="UTC")
    df = pd.DataFrame({
        "p_mp": [10.0, 11.0, 12.0],
        "poa_global": [500.0, 550.0, 600.0],
    }, index=idx)
    assert df.index.name is None

    result = pvlib_to_odse(df, site_id="site-test")
    assert "telemetry" in result
    assert len(result["telemetry"]) == 3
    assert result["telemetry"][0]["timestamp"] == "2026-06-01T10:00:00Z"
    assert result["telemetry"][0]["kW"] == 10.0
    assert result["telemetry"][0]["poa_irradiance"] == 500.0


def test_cli_to_pvlib_command(tmp_path: Path):
    """
    PVLIB-BEHAVIOR-6: Verify the odse CLI 'to-pvlib' and 'pvlib' commands
    convert input files and write valid CSV and JSON outputs.
    """
    from odse.cli import main

    input_file = tmp_path / "input.json"
    payload = {
        "metadata": {"site_id": "cli-test"},
        "telemetry": [
            {
                "timestamp": "2026-06-01T12:00:00Z",
                "active_power_kW": 15.0,
                "poa_irradiance": 800.0,
                "ambient_temperature_c": 25.0,
            }
        ]
    }
    input_file.write_text(json.dumps(payload), encoding="utf-8")

    csv_output = tmp_path / "output.csv"
    main(["to-pvlib", "-i", str(input_file), "-o", str(csv_output), "-f", "csv"])
    assert csv_output.exists()
    csv_content = csv_output.read_text(encoding="utf-8")
    assert "timestamp" in csv_content
    assert "p_mp" in csv_content
    assert "poa_global" in csv_content
    assert "temp_air" in csv_content

    # Also test the 'pvlib' alias with JSON output
    json_output = tmp_path / "output.json"
    main(["pvlib", "-i", str(input_file), "-o", str(json_output), "-f", "json"])
    assert json_output.exists()
    parsed_json = json.loads(json_output.read_text(encoding="utf-8"))
    assert parsed_json["metadata"]["site_id"] == "cli-test"
    assert len(parsed_json["data"]) == 1
    assert parsed_json["data"][0]["p_mp"] == 15.0



def test_legacy_input_keys_emit_deprecation_warning():
    """
    SEP-050: Given an ODS-E telemetry payload using legacy input keys
    (`active_power_kW`, `dc_voltage_v`, `dc_current_a`),
    When odse_to_pvlib() is invoked,
    Then each legacy key is still mapped (back-compat) AND a
    DeprecationWarning naming the keys is emitted; canonical-key payloads
    emit no DeprecationWarning.
    """
    import warnings as _warnings
    from odse.adapters.pvlib import odse_to_pvlib

    legacy_records = [
        {
            "timestamp": "2026-06-01T12:00:00Z",
            "active_power_kW": 10.0,
            "dc_voltage_v": 600.0,
            "dc_current_a": 16.7,
        }
    ]
    with _warnings.catch_warnings(record=True) as caught:
        _warnings.simplefilter("always")
        df, _meta = odse_to_pvlib(legacy_records)
    dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert dep, "legacy keys must emit a DeprecationWarning"
    msg = str(dep[0].message)
    for key in ("active_power_kW", "dc_voltage_v", "dc_current_a"):
        assert key in msg
    # Back-compat: legacy keys still mapped to pvlib columns
    assert "p_mp" in df.columns
    assert "v_dc" in df.columns
    assert "i_dc" in df.columns

    canonical_records = [
        {
            "timestamp": "2026-06-01T12:00:00Z",
            "kW": 10.0,
            "voltage_dc": 600.0,
            "current_dc": 16.7,
        }
    ]
    with _warnings.catch_warnings(record=True) as caught:
        _warnings.simplefilter("always")
        df, _meta = odse_to_pvlib(canonical_records)
    dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not dep, "canonical keys must not emit a DeprecationWarning"
    assert "p_mp" in df.columns and "v_dc" in df.columns and "i_dc" in df.columns

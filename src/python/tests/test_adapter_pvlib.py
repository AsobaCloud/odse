"""Unit tests for odse.adapters.pvlib component functionality."""

import json
from pathlib import Path
import pytest


def test_missing_pandas_dependency_guard(monkeypatch):
    """Verify ImportError is raised when pandas is not installed."""
    import odse.adapters.pvlib as pvlib_adapter

    monkeypatch.setattr(pvlib_adapter, "HAS_PANDAS", False)

    with pytest.raises(ImportError, match="pip install 'odse\\[pvlib\\]'"):
        pvlib_adapter._check_dependencies()

    with pytest.raises(ImportError, match="pip install 'odse\\[pvlib\\]'"):
        pvlib_adapter.odse_to_pvlib([{"timestamp": "2026-06-01T00:00:00Z"}])

    with pytest.raises(ImportError, match="pip install 'odse\\[pvlib\\]'"):
        pvlib_adapter.pvlib_to_odse(None, site_id="site-1")


def test_missing_timestamp_key_error():
    """Verify KeyError is raised when telemetry records lack 'timestamp'."""
    from odse.adapters.pvlib import odse_to_pvlib

    records = [{"active_power_kW": 10.0}]
    with pytest.raises(KeyError, match="missing the mandatory 'timestamp' field"):
        odse_to_pvlib(records)


def test_invalid_source_type():
    """Verify TypeError is raised for invalid source types."""
    from odse.adapters.pvlib import odse_to_pvlib

    with pytest.raises(TypeError, match="Invalid source type"):
        odse_to_pvlib(12345)  # integers not allowed


def test_empty_records_returns_empty_dataframe():
    """Verify empty input returns an empty DataFrame and empty/extracted metadata."""
    from odse.adapters.pvlib import odse_to_pvlib
    import pandas as pd

    df, meta = odse_to_pvlib([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert meta == {}

    df2, meta2 = odse_to_pvlib({"metadata": {"site_id": "s1"}, "telemetry": []})
    assert df2.empty
    assert meta2 == {"site_id": "s1"}


def test_read_from_json_file_path(tmp_path: Path):
    """Verify odse_to_pvlib reads directly from file paths (str and Path)."""
    from odse.adapters.pvlib import odse_to_pvlib

    file_path = tmp_path / "telemetry.json"
    payload = {
        "metadata": {"site_id": "site-from-file"},
        "telemetry": [
            {"timestamp": "2026-06-01T10:00:00Z", "active_power_kW": 5.0}
        ]
    }
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    # Pass as Path object
    df, meta = odse_to_pvlib(file_path)
    assert meta["site_id"] == "site-from-file"
    assert len(df) == 1
    assert "p_mp" in df.columns

    # Pass as str
    df_str, meta_str = odse_to_pvlib(str(file_path))
    assert meta_str["site_id"] == "site-from-file"
    assert len(df_str) == 1


def test_read_from_json_string():
    """Verify odse_to_pvlib parses raw JSON strings."""
    from odse.adapters.pvlib import odse_to_pvlib

    raw_json = json.dumps([
        {"timestamp": "2026-06-01T12:00:00Z", "active_power_kW": 25.0}
    ])
    df, meta = odse_to_pvlib(raw_json)
    assert len(df) == 1
    assert df["p_mp"].iloc[0] == 25.0


def test_read_from_jsonl_file(tmp_path: Path):
    """Verify odse_to_pvlib handles newline-delimited JSON (JSONL)."""
    from odse.adapters.pvlib import odse_to_pvlib

    jsonl_path = tmp_path / "records.jsonl"
    lines = [
        json.dumps({"timestamp": "2026-06-01T12:00:00Z", "active_power_kW": 10.0}),
        json.dumps({"timestamp": "2026-06-01T12:05:00Z", "active_power_kW": 11.0}),
    ]
    jsonl_path.write_text("\n".join(lines), encoding="utf-8")

    df, meta = odse_to_pvlib(jsonl_path)
    assert len(df) == 2
    assert df["p_mp"].tolist() == [10.0, 11.0]


def test_pvlib_to_odse_non_datetime_index_raises():
    """Verify TypeError when DataFrame index is not DatetimeIndex."""
    from odse.adapters.pvlib import pvlib_to_odse
    import pandas as pd

    df = pd.DataFrame({"p_mp": [1.0, 2.0]})
    with pytest.raises(TypeError, match="DataFrame index must be a DatetimeIndex"):
        pvlib_to_odse(df, site_id="site-1")


def test_pvlib_to_odse_does_not_mutate_input_metadata():
    """Verify user metadata dict is not mutated in place."""
    from odse.adapters.pvlib import pvlib_to_odse
    import pandas as pd

    idx = pd.date_range("2026-06-01", periods=2, freq="5min", tz="UTC")
    df = pd.DataFrame({"p_mp": [1.0, 2.0]}, index=idx)

    user_meta = {"custom_key": "custom_val"}
    user_meta_copy = dict(user_meta)

    result = pvlib_to_odse(df, site_id="site-xyz", metadata=user_meta)
    assert user_meta == user_meta_copy  # not modified in place
    assert result["metadata"]["site_id"] == "site-xyz"
    assert result["metadata"]["custom_key"] == "custom_val"

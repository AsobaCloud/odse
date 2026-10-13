"""Unit tests for odse.adapters.openoa component functionality."""

import json
from pathlib import Path
import pytest


def test_missing_pandas_dependency_guard(monkeypatch):
    """Verify ImportError is raised when pandas is not installed."""
    import odse.adapters.openoa as openoa_adapter

    monkeypatch.setattr(openoa_adapter, "HAS_PANDAS", False)

    with pytest.raises(ImportError, match="pip install 'odse\\[openoa\\]'"):
        openoa_adapter._check_dependencies()

    with pytest.raises(ImportError, match="pip install 'odse\\[openoa\\]'"):
        openoa_adapter.odse_to_openoa([{"timestamp": "2026-06-01T00:00:00Z"}])

    with pytest.raises(ImportError, match="pip install 'odse\\[openoa\\]'"):
        openoa_adapter.openoa_to_odse(None, site_id="site-1")


def test_missing_timestamp_key_error():
    """Verify KeyError is raised when telemetry records lack 'timestamp'."""
    from odse.adapters.openoa import odse_to_openoa

    records = [{"active_power_kW": 1000.0}]
    with pytest.raises(KeyError, match="missing mandatory 'timestamp' field"):
        odse_to_openoa(records)


def test_invalid_source_type():
    """Verify TypeError is raised for invalid source types."""
    from odse.adapters.openoa import odse_to_openoa

    with pytest.raises(TypeError, match="Invalid source type"):
        odse_to_openoa(12345)


def test_empty_records_returns_empty_dataframe():
    """Verify empty input returns empty DataFrames and metadata."""
    from odse.adapters.openoa import odse_to_openoa
    import pandas as pd

    res = odse_to_openoa([], return_plantdata=False)
    assert isinstance(res["scada"], pd.DataFrame)
    assert res["scada"].empty
    assert res["metadata"] == {"plant_name": "ODSE_Plant"}


def test_read_from_json_file_path(tmp_path: Path):
    """Verify odse_to_openoa reads directly from file paths (str and Path)."""
    from odse.adapters.openoa import odse_to_openoa

    file_path = tmp_path / "telemetry.json"
    payload = {
        "metadata": {"site_id": "file-site"},
        "telemetry": [
            {"timestamp": "2026-06-01T10:00:00Z", "active_power_kW": 500.0}
        ]
    }
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    res = odse_to_openoa(file_path, return_plantdata=False)
    assert res["metadata"]["site_id"] == "file-site"
    assert len(res["scada"]) == 1
    assert "wm_power_kw" in res["scada"].columns


def test_read_from_jsonl_file(tmp_path: Path):
    """Verify odse_to_openoa handles newline-delimited JSON (JSONL)."""
    from odse.adapters.openoa import odse_to_openoa

    jsonl_path = tmp_path / "records.jsonl"
    lines = [
        json.dumps({"timestamp": "2026-06-01T12:00:00Z", "active_power_kW": 1000.0}),
        json.dumps({"timestamp": "2026-06-01T12:05:00Z", "active_power_kW": 1100.0}),
    ]
    jsonl_path.write_text("\n".join(lines), encoding="utf-8")

    res = odse_to_openoa(jsonl_path, return_plantdata=False)
    assert len(res["scada"]) == 2
    assert res["scada"]["wm_power_kw"].tolist() == [1000.0, 1100.0]


def test_openoa_to_odse_non_datetime_index_raises():
    """Verify TypeError when DataFrame index is not DatetimeIndex."""
    from odse.adapters.openoa import openoa_to_odse
    import pandas as pd

    df = pd.DataFrame({"wm_power_kw": [1000.0, 2000.0]})
    with pytest.raises(TypeError, match="OpenOA DataFrame index must be a pandas.DatetimeIndex"):
        openoa_to_odse(df, site_id="site-1")


def test_openoa_to_odse_does_not_mutate_metadata():
    """Verify caller metadata dict is not mutated in place."""
    from odse.adapters.openoa import openoa_to_odse
    import pandas as pd

    idx = pd.date_range("2026-06-01", periods=2, freq="5min", tz="UTC")
    df = pd.DataFrame({"wm_power_kw": [100.0, 200.0]}, index=idx)

    user_meta = {"custom_tag": "val1"}
    user_meta_copy = dict(user_meta)

    res = openoa_to_odse(df, site_id="site-xyz", metadata=user_meta)
    assert user_meta == user_meta_copy
    assert res["metadata"]["site_id"] == "site-xyz"

"""Behavioral tests for Level 2 heuristic detectors (SEP-053 DET-1..5)."""

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

import pandas as pd

from odse.detectors import (
    BinaryDropoutDetector,
    PhysicalHeuristicDetector,
    RollingCUSUMDetector,
    ThermalDivergenceDetector,
)
from odse.physics import inject_physical_residuals


EVENT_COLS = [
    "timestamp",
    "asset_id",
    "detector_type",
    "severity",
    "residual_value",
    "rule_triggered",
]


def test_binary_dropout_midday_zero_fn():
    """
    DET-1: Given enriched midday row G=800, delta_p_norm=-1.0,
    When BinaryDropoutDetector.detect,
    Then exactly one binary_dropout event (zero false-negative).
    """
    df = pd.DataFrame(
        {
            "timestamp": ["2026-06-01T12:00:00Z"],
            "asset_id": ["INV-A"],
            "irradiance": [800.0],
            "delta_p_norm": [-1.0],
        }
    )
    events = BinaryDropoutDetector().detect(df)
    assert len(events) == 1
    assert events.iloc[0]["detector_type"] == "binary_dropout"
    assert events.iloc[0]["severity"] == "critical"


def test_binary_dropout_no_false_alarm_small_residual():
    """
    DET-2: Given G=800, delta_p_norm=-0.1,
    When BinaryDropoutDetector.detect,
    Then no event.
    """
    df = pd.DataFrame(
        {
            "timestamp": ["2026-06-01T12:00:00Z"],
            "asset_id": ["INV-A"],
            "irradiance": [800.0],
            "delta_p_norm": [-0.1],
        }
    )
    events = BinaryDropoutDetector().detect(df)
    assert len(events) == 0


def test_thermal_requires_three_consecutive():
    """
    DET-3: Given ΔT sequence [10,16,16,16,10] with tau=15,
    When ThermalDivergenceDetector(min_consecutive=3).detect,
    Then events only on the sustained run (3 rows), not single spikes.
    """
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-06-01T12:00:00Z", periods=5, freq="5min"),
            "asset_id": ["INV-A"] * 5,
            "delta_t_divergence": [10.0, 16.0, 16.0, 16.0, 10.0],
        }
    )
    events = ThermalDivergenceDetector(tau=15.0, min_consecutive=3).detect(df)
    assert len(events) == 3
    assert set(events["detector_type"]) == {"thermal_divergence"}

    # Single spike above tau must not alert
    spike = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-06-01T12:00:00Z", periods=3, freq="5min"),
            "asset_id": ["INV-A"] * 3,
            "delta_t_divergence": [10.0, 20.0, 10.0],
        }
    )
    assert len(ThermalDivergenceDetector(tau=15.0, min_consecutive=3).detect(spike)) == 0


def test_rolling_cusum_triggers_on_pr_drift():
    """
    DET-4: Given gradual PR decline under G>100,
    When RollingCUSUMDetector.detect,
    Then S_t increases and events appear after S_t > h.
    """
    n = 80
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-06-01T08:00:00Z", periods=n, freq="5min"),
            "asset_id": ["INV-A"] * n,
            "irradiance": [600.0] * n,
            "power": [100.0] * n,  # well below expected ~180+ kW
            "p_expected": [200.0] * n,
        }
    )
    det = RollingCUSUMDetector(k_sigma=0.5, h_threshold=4.0, g_min=100.0)
    cusum = det._cusum_series(df)
    assert cusum.iloc[-1] > cusum.iloc[0]
    events = det.detect(df)
    assert len(events) > 0
    assert (events["detector_type"] == "rolling_cusum").all()


def test_physical_heuristic_event_schema():
    """
    DET-5: Given enriched DF with a midday dropout,
    When PhysicalHeuristicDetector.detect,
    Then output columns match the SEP event schema and include ≥1 component row.
    """
    df = pd.DataFrame(
        {
            "timestamp": ["2026-06-01T12:00:00Z", "2026-06-01T12:05:00Z"],
            "asset_id": ["INV-A", "INV-A"],
            "power": [0.0, 250.0],
            "irradiance": [800.0, 800.0],
            "ambient_temperature_c": [28.0, 28.0],
            "wind_speed": [1.0, 1.0],
            "temperature": [45.0, 45.0],
        }
    )
    enriched = inject_physical_residuals(df, rated_capacity_kw=330.0)
    events = PhysicalHeuristicDetector().detect(enriched)
    assert list(events.columns) == EVENT_COLS
    assert len(events) >= 1
    assert "binary_dropout" in set(events["detector_type"])

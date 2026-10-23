"""Analytical unit tests for odse.physics residuals (SEP-053 PHYS-1..4)."""

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

import numpy as np
import pandas as pd

from odse.physics import (
    compute_expected_ac_power,
    compute_faiman_cell_temp,
    inject_physical_residuals,
)


def test_faiman_sandia_vector():
    """
    PHYS-1: Given G=1000, T_amb=25, v=1, u0=25, u1=6.84,
    When compute_faiman_cell_temp runs,
    Then T_cell = 25 + 1000/(25+6.84) within ±0.05°C.
    """
    expected = 25.0 + 1000.0 / (25.0 + 6.84)
    result = compute_faiman_cell_temp(1000.0, 25.0, 1.0)
    assert float(result) == pytest.approx(expected, abs=0.05)
    assert float(result) == pytest.approx(56.407, abs=0.05)


def test_inject_creates_residual_columns_and_matches_faiman():
    """
    PHYS-1 (inject): Given ambient/POA/wind/power DF,
    When inject_physical_residuals runs,
    Then residual columns exist and t_cell_expected matches Faiman.
    """
    df = pd.DataFrame(
        {
            "power": [200.0],
            "irradiance": [1000.0],
            "ambient_temperature_c": [25.0],
            "wind_speed": [1.0],
            "temperature": [50.0],
        }
    )
    out = inject_physical_residuals(df, rated_capacity_kw=330.0)
    assert "t_cell_expected" in out.columns
    assert "p_expected" in out.columns
    assert "delta_p_norm" in out.columns
    expected_t = 25.0 + 1000.0 / (25.0 + 6.84)
    assert out["t_cell_expected"].iloc[0] == pytest.approx(expected_t, abs=0.05)


def test_delta_t_divergence():
    """
    PHYS-2: Given inverter temperature present,
    When inject runs,
    Then delta_t_divergence == temperature - t_cell_expected.
    """
    df = pd.DataFrame(
        {
            "power": [100.0],
            "irradiance": [800.0],
            "ambient_temperature_c": [20.0],
            "wind_speed_ms": [2.0],
            "temperature": [60.0],
        }
    )
    out = inject_physical_residuals(df, rated_capacity_kw=330.0)
    assert "delta_t_divergence" in out.columns
    expected = out["temperature"] - out["t_cell_expected"]
    np.testing.assert_allclose(
        out["delta_t_divergence"].to_numpy(),
        expected.to_numpy(),
        rtol=0,
        atol=1e-9,
    )


def test_european_eta_peak():
    """
    PHYS-3: Given G=1000, T_cell=25, P_rated=330,
    When compute_expected_ac_power runs,
    Then p_expected / 330 ≈ 0.986 (±0.002).
    """
    p = float(compute_expected_ac_power(1000.0, 25.0, p_rated_kw=330.0))
    eta = p / 330.0
    assert eta == pytest.approx(0.986, abs=0.002)


def test_missing_ambient_raises():
    """
    PHYS-4: Given missing ambient column,
    When inject_physical_residuals runs,
    Then ValueError is raised (no silent proxy).
    """
    df = pd.DataFrame(
        {
            "power": [100.0],
            "irradiance": [800.0],
            "wind_speed": [1.0],
            "temperature": [40.0],
        }
    )
    with pytest.raises(ValueError, match="ambient"):
        inject_physical_residuals(df, rated_capacity_kw=330.0)


def test_midday_zero_power_strongly_negative_residual():
    """Midday zero AC power yields strongly negative delta_p_norm."""
    df = pd.DataFrame(
        {
            "kW": [0.0],
            "poa_irradiance": [800.0],
            "ambient_temperature_c": [28.0],
            "wind_speed_ms": [1.5],
        }
    )
    out = inject_physical_residuals(df, rated_capacity_kw=330.0)
    assert out["delta_p_norm"].iloc[0] < -0.50


def test_adapters_pvlib_reexports_inject():
    """SEP SDK path: from odse.adapters.pvlib import inject_physical_residuals."""
    from odse.adapters.pvlib import inject_physical_residuals as inj

    assert inj is inject_physical_residuals

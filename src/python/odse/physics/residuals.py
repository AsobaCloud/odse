"""Deterministic physical residuals (SEP-053).

Closed-form Faiman cell temperature, expected AC power, and normalized
residuals. Pure NumPy/Pandas — does not import the pvlib package.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple, Union

try:
    import numpy as np
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


POWER_CANDIDATES: Tuple[str, ...] = (
    "kW",
    "active_power_kW",
    "p_mp",
    "power_kw",
    "power",
)
IRRADIANCE_CANDIDATES: Tuple[str, ...] = (
    "poa_irradiance",
    "poa_global",
    "irradiance",
    "ghi",
)
AMBIENT_CANDIDATES: Tuple[str, ...] = (
    "ambient_temperature_c",
    "temp_air",
    "ambient_temp_c",
)
WIND_CANDIDATES: Tuple[str, ...] = ("wind_speed_ms", "wind_speed")
INVERTER_TEMP_CANDIDATES: Tuple[str, ...] = (
    "temperature",
    "temperature_c",
    "temp_inv",
)


def _check_dependencies() -> None:
    if not HAS_PANDAS:
        raise ImportError(
            "pandas (and numpy) are required for odse.physics residuals. "
            "Install optional dependencies using: pip install 'odse[dataframe]'"
        )


def _resolve_col(df: Any, candidates: Sequence[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def compute_faiman_cell_temp(
    g: Union[float, Any],
    t_amb: Union[float, Any],
    v_wind: Union[float, Any] = 1.0,
    u0: float = 25.0,
    u1: float = 6.84,
) -> Any:
    """Faiman module/cell temperature (°C).

    T_cell = T_amb + G / (u0 + u1 * v_wind)

    Defaults u0=25.0, u1=6.84 match open-rack crystalline silicon
    (IEC 61853 / pvlib.temperature.faiman defaults) without importing pvlib.
    """
    _check_dependencies()
    g_arr = np.asanyarray(g, dtype=float)
    t_arr = np.asanyarray(t_amb, dtype=float)
    v_arr = np.asanyarray(v_wind, dtype=float)
    denominator = u0 + u1 * np.maximum(v_arr, 0.0)
    return t_arr + (np.maximum(g_arr, 0.0) / denominator)


def compute_expected_ac_power(
    g: Union[float, Any],
    t_cell: Union[float, Any],
    p_rated_kw: float = 330.0,
    gamma: float = -0.0035,
    t_ref: float = 25.0,
    g_ref: float = 1000.0,
) -> Any:
    """Expected AC power (kW) with temperature derate and European η curve.

    η_inv ≈ 0.986 at high load (utility string inverter approximation).
    """
    _check_dependencies()
    g_arr = np.asanyarray(g, dtype=float)
    t_arr = np.asanyarray(t_cell, dtype=float)

    irr_ratio = np.maximum(g_arr, 0.0) / g_ref
    temp_derate = 1.0 + gamma * (t_arr - t_ref)
    p_dc_expected = p_rated_kw * irr_ratio * np.maximum(temp_derate, 0.5)

    load_ratio = np.clip(p_dc_expected / p_rated_kw, 0.0, 1.0)
    eta_inv = np.where(
        load_ratio > 0.05,
        0.986 - 0.02 * np.exp(-15.0 * load_ratio),
        0.90,
    )
    p_ac = np.clip(p_dc_expected * eta_inv, 0.0, p_rated_kw)
    return np.where(g_arr < 5.0, 0.0, p_ac)


def inject_physical_residuals(
    df: Any,
    rated_capacity_kw: float,
    temp_coeff: float = -0.0035,
    u0: float = 25.0,
    u1: float = 6.84,
) -> Any:
    """Enrich telemetry with t_cell_expected, p_expected, delta_p_norm[, delta_t_divergence].

    Requires an ambient temperature column (ambient_temperature_c / temp_air /
    ambient_temp_c). Does not apply a silent nighttime proxy.
    """
    _check_dependencies()
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    out = df.copy()

    power_col = _resolve_col(out, POWER_CANDIDATES)
    irr_col = _resolve_col(out, IRRADIANCE_CANDIDATES)
    amb_col = _resolve_col(out, AMBIENT_CANDIDATES)
    wind_col = _resolve_col(out, WIND_CANDIDATES)
    inv_temp_col = _resolve_col(out, INVERTER_TEMP_CANDIDATES)

    if power_col is None:
        raise ValueError(
            "inject_physical_residuals requires a power column "
            f"(one of {POWER_CANDIDATES})"
        )
    if irr_col is None:
        raise ValueError(
            "inject_physical_residuals requires an irradiance column "
            f"(one of {IRRADIANCE_CANDIDATES})"
        )
    if amb_col is None:
        raise ValueError(
            "inject_physical_residuals requires ambient temperature "
            f"(one of {AMBIENT_CANDIDATES}). Join weather or supply "
            "ambient_temperature_c; silent night-proxy is not applied."
        )

    g = out[irr_col].to_numpy(dtype=float)
    t_amb = out[amb_col].to_numpy(dtype=float)
    if wind_col is not None:
        v_wind = out[wind_col].to_numpy(dtype=float)
    else:
        v_wind = np.full(len(out), 1.0, dtype=float)

    t_cell = compute_faiman_cell_temp(g, t_amb, v_wind, u0=u0, u1=u1)
    p_expected = compute_expected_ac_power(
        g,
        t_cell,
        p_rated_kw=rated_capacity_kw,
        gamma=temp_coeff,
    )
    p_ac = out[power_col].to_numpy(dtype=float)

    out["t_cell_expected"] = t_cell
    out["p_expected"] = p_expected
    out["delta_p_norm"] = (p_ac - p_expected) / float(rated_capacity_kw)

    if inv_temp_col is not None:
        out["delta_t_divergence"] = (
            out[inv_temp_col].to_numpy(dtype=float) - t_cell
        )

    return out

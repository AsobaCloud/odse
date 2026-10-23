"""Level 2 non-deep physical heuristic detectors (SEP-053)."""

from __future__ import annotations

from typing import Any, List, Optional

from .base import BaseDetector, _check_dependencies

try:
    import numpy as np
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

EVENT_COLUMNS = [
    "timestamp",
    "asset_id",
    "detector_type",
    "severity",
    "residual_value",
    "rule_triggered",
]

IRRADIANCE_CANDIDATES = (
    "poa_irradiance",
    "poa_global",
    "irradiance",
    "ghi",
)
POWER_CANDIDATES = ("kW", "active_power_kW", "p_mp", "power_kw", "power")


def _resolve_col(df: Any, candidates: tuple) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _timestamp_series(df: Any) -> Any:
    if "timestamp" in df.columns:
        return pd.to_datetime(df["timestamp"], utc=True)
    if isinstance(df.index, pd.DatetimeIndex):
        return df.index
    return pd.Series([None] * len(df), index=df.index)


def _asset_series(df: Any) -> Any:
    if "asset_id" in df.columns:
        return df["asset_id"].astype(str)
    return pd.Series(["unknown"] * len(df), index=df.index)


def _empty_events() -> Any:
    return pd.DataFrame(columns=EVENT_COLUMNS)


def _events_from_mask(
    df: Any,
    mask: Any,
    detector_type: str,
    severity: str,
    residual_values: Any,
    rule_triggered: str,
) -> Any:
    if not mask.any():
        return _empty_events()
    flagged = df.loc[mask]
    residual = residual_values.loc[mask] if hasattr(residual_values, "loc") else residual_values[mask]
    return pd.DataFrame(
        {
            "timestamp": _timestamp_series(flagged).values,
            "asset_id": _asset_series(flagged).values,
            "detector_type": detector_type,
            "severity": severity,
            "residual_value": residual.values if hasattr(residual, "values") else residual,
            "rule_triggered": rule_triggered,
        }
    )


class BinaryDropoutDetector(BaseDetector):
    """Flag midday generation dropouts: G > g_min and delta_p_norm < -tau."""

    def __init__(self, tau: float = 0.50, g_min: float = 200.0):
        self.tau = float(tau)
        self.g_min = float(g_min)

    def fit(self, telemetry_df: Any) -> "BinaryDropoutDetector":
        _check_dependencies()
        return self

    def score(self, telemetry_df: Any) -> Any:
        _check_dependencies()
        if "delta_p_norm" not in telemetry_df.columns:
            raise ValueError(
                "BinaryDropoutDetector requires delta_p_norm; "
                "call inject_physical_residuals first"
            )
        irr_col = _resolve_col(telemetry_df, IRRADIANCE_CANDIDATES)
        if irr_col is None:
            raise ValueError(
                "BinaryDropoutDetector requires an irradiance column "
                f"(one of {IRRADIANCE_CANDIDATES})"
            )
        g = telemetry_df[irr_col]
        delta = telemetry_df["delta_p_norm"]
        flagged = (g > self.g_min) & (delta < -self.tau)
        return flagged.astype(float)

    def detect(self, telemetry_df: Any) -> Any:
        scores = self.score(telemetry_df)
        mask = scores > 0.0
        rule = f"delta_p_norm<-{self.tau}&G>{self.g_min}"
        return _events_from_mask(
            telemetry_df,
            mask,
            detector_type="binary_dropout",
            severity="critical",
            residual_values=telemetry_df["delta_p_norm"],
            rule_triggered=rule,
        )


class ThermalDivergenceDetector(BaseDetector):
    """Flag sustained heatsink vs Faiman cell divergence."""

    def __init__(self, tau: float = 15.0, min_consecutive: int = 3):
        self.tau = float(tau)
        self.min_consecutive = int(min_consecutive)

    def fit(self, telemetry_df: Any) -> "ThermalDivergenceDetector":
        _check_dependencies()
        return self

    def _sustained_mask(self, df: Any) -> Any:
        if "delta_t_divergence" not in df.columns:
            return pd.Series(False, index=df.index)

        mask = pd.Series(False, index=df.index)
        above = df["delta_t_divergence"] > self.tau

        if "asset_id" in df.columns:
            group_iter = df.groupby("asset_id", sort=False).groups.items()
        else:
            group_iter = [("all", df.index)]

        for _asset, idx in group_iter:
            # Preserve chronological order within asset
            idx = pd.Index(idx)
            above_arr = above.loc[idx].to_numpy(dtype=bool)
            local_mask = np.zeros(len(idx), dtype=bool)
            i = 0
            n = len(idx)
            while i < n:
                if not above_arr[i]:
                    i += 1
                    continue
                j = i + 1
                while j < n and above_arr[j]:
                    j += 1
                if (j - i) >= self.min_consecutive:
                    local_mask[i:j] = True
                i = j
            mask.loc[idx] = local_mask
        return mask

    def score(self, telemetry_df: Any) -> Any:
        _check_dependencies()
        if "delta_t_divergence" not in telemetry_df.columns:
            return pd.Series(0.0, index=telemetry_df.index)
        return self._sustained_mask(telemetry_df).astype(float)

    def detect(self, telemetry_df: Any) -> Any:
        scores = self.score(telemetry_df)
        mask = scores > 0.0
        if "delta_t_divergence" not in telemetry_df.columns:
            return _empty_events()
        rule = f"delta_t_divergence>{self.tau}x{self.min_consecutive}"
        return _events_from_mask(
            telemetry_df,
            mask,
            detector_type="thermal_divergence",
            severity="warning",
            residual_values=telemetry_df["delta_t_divergence"],
            rule_triggered=rule,
        )


class RollingCUSUMDetector(BaseDetector):
    """IEC 61724-style rolling PR CUSUM for progressive drift."""

    def __init__(
        self,
        k_sigma: float = 0.5,
        h_threshold: float = 4.0,
        g_min: float = 100.0,
    ):
        self.k_sigma = float(k_sigma)
        self.h_threshold = float(h_threshold)
        self.g_min = float(g_min)

    def fit(self, telemetry_df: Any) -> "RollingCUSUMDetector":
        _check_dependencies()
        return self

    def _cusum_series(self, df: Any) -> Any:
        irr_col = _resolve_col(df, IRRADIANCE_CANDIDATES)
        power_col = _resolve_col(df, POWER_CANDIDATES)
        if irr_col is None or power_col is None or "p_expected" not in df.columns:
            raise ValueError(
                "RollingCUSUMDetector requires irradiance, power, and p_expected"
            )

        if "asset_id" in df.columns:
            asset_ids = df["asset_id"].astype(str).to_numpy()
        else:
            asset_ids = np.array(["unknown"] * len(df))

        g = df[irr_col].to_numpy(dtype=float)
        p_act = df[power_col].to_numpy(dtype=float)
        p_exp = df["p_expected"].to_numpy(dtype=float)
        valid = g > self.g_min
        pr = np.where(valid, p_act / np.maximum(p_exp, 1.0), 1.0)
        pr_clean = np.clip(pr, 0.0, 1.2)

        allowance = self.k_sigma * 0.05
        cusum = np.zeros(len(df), dtype=float)
        state: dict = {}
        for i in range(len(df)):
            asset = asset_ids[i]
            s_pos = state.get(asset, 0.0)
            if valid[i]:
                deviation = 1.0 - pr_clean[i]
                s_pos = max(0.0, s_pos + deviation - allowance)
            state[asset] = s_pos
            cusum[i] = s_pos
        return pd.Series(cusum, index=df.index, name="cusum_s")

    def score(self, telemetry_df: Any) -> Any:
        _check_dependencies()
        cusum = self._cusum_series(telemetry_df)
        return (cusum > self.h_threshold).astype(float)

    def detect(self, telemetry_df: Any) -> Any:
        cusum = self._cusum_series(telemetry_df)
        mask = cusum > self.h_threshold
        rule = f"PR_CUSUM>{self.h_threshold}"
        return _events_from_mask(
            telemetry_df,
            mask,
            detector_type="rolling_cusum",
            severity="warning",
            residual_values=cusum,
            rule_triggered=rule,
        )


class PhysicalHeuristicDetector(BaseDetector):
    """Composite Level 2 detector: dropout + thermal + PR CUSUM."""

    def __init__(
        self,
        rated_capacity_kw: Optional[float] = None,
        temp_coeff: float = -0.0035,
        tau_dropout: float = 0.50,
        g_min_dropout: float = 200.0,
        tau_thermal: float = 15.0,
        min_consecutive: int = 3,
        k_sigma: float = 0.5,
        h_threshold: float = 4.0,
        g_min_cusum: float = 100.0,
    ):
        self.rated_capacity_kw = rated_capacity_kw
        self.temp_coeff = temp_coeff
        self.dropout = BinaryDropoutDetector(tau=tau_dropout, g_min=g_min_dropout)
        self.thermal = ThermalDivergenceDetector(
            tau=tau_thermal, min_consecutive=min_consecutive
        )
        self.cusum = RollingCUSUMDetector(
            k_sigma=k_sigma, h_threshold=h_threshold, g_min=g_min_cusum
        )

    def fit(self, telemetry_df: Any) -> "PhysicalHeuristicDetector":
        _check_dependencies()
        enriched = self._maybe_enrich(telemetry_df)
        self.dropout.fit(enriched)
        self.thermal.fit(enriched)
        self.cusum.fit(enriched)
        return self

    def _maybe_enrich(self, telemetry_df: Any) -> Any:
        if "delta_p_norm" in telemetry_df.columns and "p_expected" in telemetry_df.columns:
            return telemetry_df
        if self.rated_capacity_kw is None:
            raise ValueError(
                "PhysicalHeuristicDetector requires pre-enriched residuals "
                "or rated_capacity_kw to call inject_physical_residuals"
            )
        from odse.physics import inject_physical_residuals

        return inject_physical_residuals(
            telemetry_df,
            rated_capacity_kw=self.rated_capacity_kw,
            temp_coeff=self.temp_coeff,
        )

    def score(self, telemetry_df: Any) -> Any:
        _check_dependencies()
        enriched = self._maybe_enrich(telemetry_df)
        scores = [
            self.dropout.score(enriched),
            self.thermal.score(enriched),
            self.cusum.score(enriched),
        ]
        stacked = pd.concat(scores, axis=1)
        return stacked.max(axis=1)

    def detect(self, telemetry_df: Any) -> Any:
        _check_dependencies()
        enriched = self._maybe_enrich(telemetry_df)
        frames: List[Any] = [
            self.dropout.detect(enriched),
            self.thermal.detect(enriched),
            self.cusum.detect(enriched),
        ]
        nonempty = [f for f in frames if len(f) > 0]
        if not nonempty:
            return _empty_events()
        return pd.concat(nonempty, ignore_index=True)

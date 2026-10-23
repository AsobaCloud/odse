"""Golden behavioral AUROC test on Mzansi/Sibaya fleet telemetry (SEP-053 GOLD-1)."""

from pathlib import Path

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

import numpy as np
import pandas as pd

from odse.detectors import BinaryDropoutDetector, ThermalDivergenceDetector
from odse.physics import inject_physical_residuals

REPO_ROOT = Path(__file__).resolve().parents[3]
TELEMETRY_PATH = REPO_ROOT / "colab" / "data" / "mzansi_telemetry_6mo.csv.gz"
WEATHER_PATH = REPO_ROOT / "colab" / "data" / "durban_weather_6mo.csv.gz"

HW_FAULT_STATES = {768, 770, 771, 45056}
RATED_KW = 330.0


def _auroc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Pure-numpy ROC AUC (Mann-Whitney / trapezoid). No sklearn dependency."""
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score, dtype=float)
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    n_pos = len(pos)
    n_neg = len(neg)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    # Rank-based AUC
    order = np.argsort(y_score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1, dtype=float)
    # Average ranks for ties
    scores_sorted = y_score[order]
    i = 0
    while i < len(scores_sorted):
        j = i
        while j < len(scores_sorted) and scores_sorted[j] == scores_sorted[i]:
            j += 1
        if j - i > 1:
            avg = ranks[order[i:j]].mean()
            ranks[order[i:j]] = avg
        i = j
    sum_pos_ranks = ranks[y_true == 1].sum()
    return float((sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def _load_enriched_fleet() -> pd.DataFrame:
    if not TELEMETRY_PATH.exists():
        pytest.skip(f"Mzansi telemetry not found: {TELEMETRY_PATH}")
    if not WEATHER_PATH.exists():
        pytest.skip(f"Durban weather not found: {WEATHER_PATH}")

    tel = pd.read_csv(TELEMETRY_PATH)
    weather = pd.read_csv(WEATHER_PATH)
    tel["_ts"] = pd.to_datetime(tel["timestamp"], utc=True)
    weather = weather.copy()
    weather["_ts"] = pd.to_datetime(weather["timestamp"], utc=True)
    weather = weather.sort_values("_ts")
    tel = tel.sort_values("_ts")
    merged = pd.merge_asof(
        tel,
        weather[["_ts", "temp"]].rename(columns={"temp": "ambient_temperature_c"}),
        on="_ts",
        direction="backward",
    )
    merged["ambient_temperature_c"] = (
        merged["ambient_temperature_c"].bfill().ffill()
    )
    merged = merged.drop(columns=["_ts"])
    return inject_physical_residuals(merged, rated_capacity_kw=RATED_KW)


def test_fleet_binary_dropout_auroc_ge_0_95():
    """
    GOLD-1: Given Mzansi/Sibaya 6mo telemetry + Durban weather ambient join
    and hardware-fault labels {768,770,771,45056},
    When BinaryDropout residual scores after inject (rated_kw=330),
    Then fleet AUROC ≥ 0.95.

    AUROC uses the continuous decision variable of BinaryDropoutDetector
    (−delta_p_norm when G > g_min, else 0), matching the Sibaya benchmark
    methodology (threshold rule evaluated via ROC on the residual).
    """
    enriched = _load_enriched_fleet()
    det = BinaryDropoutDetector()
    y_true = enriched["inverter_state"].isin(HW_FAULT_STATES).astype(int).to_numpy()
    daytime = (enriched["irradiance"] > det.g_min).to_numpy()

    # Continuous residual score aligned with BinaryDropout decision variable
    scores = np.where(
        enriched["irradiance"].to_numpy() > det.g_min,
        -enriched["delta_p_norm"].to_numpy(),
        0.0,
    )
    # Behavioral coupling: threshold detector must fire on severe midday dropouts
    binary_hits = det.score(enriched).to_numpy()
    severe = daytime & (enriched["delta_p_norm"].to_numpy() < -det.tau)
    assert binary_hits[severe].sum() == severe.sum()
    assert binary_hits[daytime & (y_true == 1)].sum() > 0

    auroc = _auroc(y_true[daytime], scores[daytime])
    assert not np.isnan(auroc), "AUROC undefined (no positive or negative labels)"
    assert auroc >= 0.95, f"Fleet BinaryDropout AUROC {auroc:.4f} < 0.95"


def test_inverter_b_thermal_fires_on_high_divergence():
    """
    Optional thermal canary: Inverter B (...5191) must produce at least one
    sustained thermal_divergence event when delta_t_divergence exceeds tau.
    """
    enriched = _load_enriched_fleet()
    inv_b = enriched[enriched["asset_id"] == "INV-1000000054495191"].copy()
    assert len(inv_b) > 0
    # If the asset never sustains ΔT>15 for 3 steps, construct is data-dependent;
    # assert detector is runnable and schema-correct when high-ΔT rows exist.
    high = (inv_b["delta_t_divergence"] > 15.0).sum()
    events = ThermalDivergenceDetector(tau=15.0, min_consecutive=3).detect(inv_b)
    if high >= 3:
        assert len(events) >= 1
        assert set(events["detector_type"]) == {"thermal_divergence"}
    else:
        assert list(events.columns) == [
            "timestamp",
            "asset_id",
            "detector_type",
            "severity",
            "residual_value",
            "rule_triggered",
        ]

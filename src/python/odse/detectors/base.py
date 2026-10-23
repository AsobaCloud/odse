"""Base detector interface for ODS-E Level 2 anomaly detectors (SEP-053)."""

from __future__ import annotations

from typing import Any

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def _check_dependencies() -> None:
    if not HAS_PANDAS:
        raise ImportError(
            "pandas is required for odse.detectors. "
            "Install optional dependencies using: pip install 'odse[dataframe]'"
        )


class BaseDetector:
    """Standard fit / score / detect API for Level 2 detectors."""

    def fit(self, telemetry_df: Any) -> "BaseDetector":
        """Optional calibration against historical telemetry. Default: no-op."""
        _check_dependencies()
        return self

    def score(self, telemetry_df: Any) -> Any:
        """Return a float anomaly score Series aligned to telemetry_df index."""
        raise NotImplementedError

    def detect(self, telemetry_df: Any) -> Any:
        """Return an anomaly-events DataFrame for flagged rows."""
        raise NotImplementedError

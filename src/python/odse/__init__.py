"""
ODS-E: Open Data Schema for Energy

A Python library for validating and transforming energy asset data
using the ODS-E specification.
"""

__version__ = "0.5.0"

from .validator import (
    validate,
    validate_file,
    validate_batch,
    BatchValidationResult,
    PROFILES,
)
from .transformer import transform, transform_stream
from .enrichment import enrich
from .io import to_csv, to_dataframe, to_json, to_parquet
from .regulatory import REGULATORY_EVENT_SCHEMA_VERSION, normalize_regulatory_events

__all__ = [
    "validate",
    "validate_file",
    "validate_batch",
    "BatchValidationResult",
    "PROFILES",
    "transform",
    "transform_stream",
    "enrich",
    "REGULATORY_EVENT_SCHEMA_VERSION",
    "normalize_regulatory_events",
    "to_json",
    "to_csv",
    "to_parquet",
    "to_dataframe",
]

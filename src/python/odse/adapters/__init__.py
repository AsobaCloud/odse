"""ODS-E Adapters.

Third-party scientific and modeling ecosystem adapters (pvlib, etc.).
"""

from .pvlib import (
    inject_physical_residuals,
    odse_to_pvlib,
    pvlib_to_odse,
)
from .openoa import odse_to_openoa, openoa_to_odse

__all__ = [
    "odse_to_pvlib",
    "pvlib_to_odse",
    "inject_physical_residuals",
    "odse_to_openoa",
    "openoa_to_odse",
]

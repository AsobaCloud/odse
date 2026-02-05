"""
ODS-E Transformer

Transforms OEM-specific data formats to ODS-E schema.
"""

from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union


def transform(
    data: Union[str, Path],
    source: str,
    asset_id: Optional[str] = None,
    timezone: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Transform OEM data to ODS-E format.

    Args:
        data: Path to data file or data string
        source: OEM source identifier (e.g., "huawei", "enphase", "solarman")
        asset_id: Optional asset identifier to include in output
        timezone: Optional timezone for timestamp conversion

    Returns:
        List of ODS-E formatted records
    """
    transformer = _get_transformer(source)
    return transformer.transform(data, asset_id=asset_id, timezone=timezone)


def transform_stream(
    data: Union[str, Path],
    source: str,
    **kwargs,
) -> Iterator[Dict[str, Any]]:
    """
    Stream transform OEM data to ODS-E format.

    Useful for large files where loading all records into memory
    is not practical.

    Args:
        data: Path to data file
        source: OEM source identifier
        **kwargs: Additional arguments passed to transformer

    Yields:
        ODS-E formatted records one at a time
    """
    transformer = _get_transformer(source)
    yield from transformer.transform_stream(data, **kwargs)


def _get_transformer(source: str):
    """Get the appropriate transformer for the source."""
    transformers = {
        "huawei": HuaweiTransformer(),
        "enphase": EnphaseTransformer(),
        "solarman": SolarmanTransformer(),
    }

    source_lower = source.lower()
    if source_lower not in transformers:
        raise ValueError(
            f"Unknown source '{source}'. "
            f"Supported sources: {list(transformers.keys())}"
        )

    return transformers[source_lower]


class BaseTransformer:
    """Base class for OEM transformers."""

    def transform(
        self,
        data: Union[str, Path],
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Transform data to ODS-E format."""
        raise NotImplementedError

    def transform_stream(
        self,
        data: Union[str, Path],
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """Stream transform data to ODS-E format."""
        # Default implementation: yield from transform()
        yield from self.transform(data, **kwargs)


class HuaweiTransformer(BaseTransformer):
    """Transform Huawei FusionSolar data to ODS-E."""

    ERROR_CODES = {
        "normal": [0, 1, 2, 3, 256, 512, 1025, 1026, 1280, 1281, 1536, 1792, 2048, 2304, 40960, 49152],
        "warning": [513, 514, 772, 773, 774],
        "critical": [768, 770, 771, 45056],
        "fault": [769, 1024],
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        # Placeholder implementation
        return []

    def _map_error_code(self, code: int) -> str:
        for error_type, codes in self.ERROR_CODES.items():
            if code in codes:
                return error_type
        return "unknown"


class EnphaseTransformer(BaseTransformer):
    """Transform Enphase Envoy data to ODS-E."""

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        # Placeholder implementation
        return []


class SolarmanTransformer(BaseTransformer):
    """Transform Solarman Logger data to ODS-E."""

    STATE_MAPPING = {
        "Normal": "normal",
        "Operating": "normal",
        "Warning": "warning",
        "Fault": "fault",
        "Error": "fault",
        "Offline": "offline",
        "Standby": "standby",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        # Placeholder implementation
        return []

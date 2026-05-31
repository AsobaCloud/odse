"""
ODS-E Connectors

Specialized connectors for OEM-specific data formats and protocols.
"""

from .scl import SCLParser, SCLMetadataExtractor

__all__ = ["SCLParser", "SCLMetadataExtractor"]

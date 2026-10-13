# ODS-E Adapters (`odse.adapters`)

This package provides adapters connecting ODS-E (Open Data Schema for Energy) data structures with third-party scientific, machine learning, and modeling ecosystems.

## Available Adapters

### `odse.adapters.pvlib`
Bridges ODS-E normalized telemetry records with `pvlib-python` structures:
- `odse_to_pvlib()`: Converts ODS-E JSON/JSONL into a UTC-indexed `pd.DataFrame` and metadata dictionary conforming to `pvlib.iotools` conventions.
- `pvlib_to_odse()`: Converts simulated pvlib `pd.DataFrame` back into canonical ODS-E JSON dictionary payloads.

For full specification, mapping tables, and the troubleshooting guide for edge cases, see:
- [pvlib Integration Specification & Troubleshooting Guide](../../../../spec/pvlib-integration.md)

### `odse.adapters.openoa`
Bridges ODS-E normalized telemetry and operational payloads with NREL's OpenOA (Open Operational Assessment) structures:
- `odse_to_openoa()`: Converts ODS-E JSON/JSONL into UTC-indexed `pd.DataFrame` tables (`scada`, `tower`, `meter`) or OpenOA `PlantData` objects.
- `openoa_to_odse()`: Converts OpenOA analysis `pd.DataFrame` back into canonical ODS-E JSON payloads.

For full specification, mapping tables, and the troubleshooting guide for edge cases, see:
- [OpenOA Integration Specification & Troubleshooting Guide](../../../../spec/openoa-integration.md)


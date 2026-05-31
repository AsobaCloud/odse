# IEC 61850 / SCADA Integration Guide

ODS-E provides first-class support for IEC 61850 substation data through its SCL (Substation Configuration Language) connector.

## 1. Asset Discovery (SCL)

Instead of manually defining assets, you can point ODSE to an `.scd` or `.cid` file to automatically generate your `asset-metadata.json`.

```python
from odse.connectors.scl import SCLMetadataExtractor

extractor = SCLMetadataExtractor("substation.scd")
metadata = extractor.extract_all()

# Save for use in validation
extractor.save_metadata("schemas/substation-metadata.json")
```

The parser extracts the following hierarchy:
`Substation` -> `VoltageLevel` -> `Bay` -> `IED`

## 2. Measurement Mappings

The SCL connector automatically identifies ODS-E measurement points by inspecting Logical Nodes:

- **MMTR**: Maps `TotWh` to ODS-E `kWh`.
- **MMXU**: Maps `W` (kW), `V` (voltage_ac), `A` (current_ac), `PF` (PF), and `Hz` (frequency).

## 3. Telemetry Ingest

Once the assets are discovered, you can use the generated XPaths to route real-time MMS (Manufacturing Message Specification) data into ODS-E records.

For example, a `TotWh` value from an IED named `INV_01` is mapped with the stable XPath:
`.//IED[@name='INV_01']//LN[@lnClass='MMTR']//DOI[@name='TotWh']`

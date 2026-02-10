# ODS-E: Open Data Schema for Energy

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

ODS-E is an open specification for standardizing energy asset data from IoT devices, enabling interoperability across the renewable energy ecosystem.

## Why ODS-E?

- **No Vendor Lock-in**: Your data works with any ODS-E compatible system
- **Faster Integrations**: Pre-built transforms for common OEMs (Huawei, Enphase, Solarman, Switch, SolaX, FIMER)
- **Analytics-Ready**: Standardized error taxonomy and semantic validation
- **Future-Proof**: CC-BY-SA licensed specification ensures extensions stay open

## Quick Start

```bash
pip install odse
```

```python
from ods_e import validate, transform

# Validate ODS-E data
result = validate("production_data.json")

# Transform Huawei CSV rows to ODS-E records
ods_data = transform("huawei_export.csv", source="huawei")

# Transform Switch meter CSV rows
switch_data = transform("switch_meter.csv", source="switch")

# Transform SolaXCloud realtime JSON payload
solax_data = transform("solax_realtime.json", source="solaxcloud")
```

## Repository Structure

```
ona-protocol/
├── LICENSE-SPEC.md       # CC-BY-SA 4.0 (specification, schemas, transforms)
├── LICENSE-CODE.md       # Apache 2.0 (reference implementation, tools)
├── spec/                 # Specification documents
├── schemas/              # JSON Schema definitions
├── transforms/           # OEM transform specifications
├── src/                  # Reference implementation
└── tools/                # CLI tools
```

## Core Schema

```json
{
  "timestamp": "2026-02-05T14:00:00Z",
  "kWh": 847.5,
  "error_type": "normal",
  "PF": 0.98
}
```

**Required fields:**
- `timestamp` - ISO 8601 with timezone
- `kWh` - Active energy (≥ 0)
- `error_type` - One of: `normal`, `warning`, `critical`, `fault`, `offline`, `standby`, `unknown`

## Supported OEMs

| OEM | Format | Status |
|-----|--------|--------|
| Huawei FusionSolar | CSV, API | ✅ Included |
| Enphase Envoy | JSON, API | ✅ Included |
| Solarman Logger | CSV | ✅ Included |
| SolarEdge | JSON API | ✅ Included |
| Fronius | JSON API | ✅ Included |
| Switch Energy | CSV | ✅ Included |
| SMA | JSON API | ✅ Included (Spec) |
| FIMER Aurora Vision | JSON API | ✅ Included (Spec) |
| SolisCloud | JSON API | ✅ Included (Spec) |
| SolaX Cloud | JSON API | ✅ Included (Spec) |

## License

- **Specification, Schemas, Transforms**: [CC-BY-SA 4.0](LICENSE-SPEC.md)
- **Reference Implementation, Tools**: [Apache 2.0](LICENSE-CODE.md)

## Documentation

- [Full Documentation](https://docs.asoba.co/ona-protocol/overview)
- [Schema Reference](https://docs.asoba.co/ona-protocol/schemas)
- [Transform Guide](https://docs.asoba.co/ona-protocol/transforms)
- [Inverter API Access Setup](spec/inverter-api-access.md)
- [Launch Kit](spec/launch-kit.md)
- [Governance](GOVERNANCE.md)

## Transform Harness

Run all OEM transform functions using fixtures:

```bash
PYTHONPATH=src/python python3 tools/transform_harness.py --mode fixture
```

Run mixed mode (live for OEMs configured in `.env`, fixture fallback for others):

```bash
cp .env.example .env
PYTHONPATH=src/python python3 tools/transform_harness.py --mode mixed
```

Run live-only checks for selected OEMs:

```bash
PYTHONPATH=src/python python3 tools/transform_harness.py --mode live --oems enphase,sma,fronius
```

Live mode quick config (`.env`):

```env
ODS_LIVE_ENPHASE_URL=https://api.enphaseenergy.com/api/v4/systems/<system_id>/telemetry/production_micro?start_at=2026-02-09T12:00:00Z&end_at=2026-02-09T12:15:00Z
ODS_LIVE_ENPHASE_METHOD=GET
ODS_LIVE_ENPHASE_HEADERS={"Authorization":"Bearer <enphase_access_token>"}
ODS_LIVE_ENPHASE_TRANSFORM_KWARGS={"expected_devices":10}

ODS_LIVE_SMA_URL=https://sandbox.smaapis.de/monitoring/<endpoint-returning-normalized-payload>
ODS_LIVE_SMA_METHOD=GET
ODS_LIVE_SMA_HEADERS={"Authorization":"Bearer <sma_access_token>"}

FRONIUS_HOST=192.168.1.50
```

If you see `live config missing`, it means the required `ODS_LIVE_<OEM>_URL` (or `FRONIUS_HOST`) is not set in `.env`.

## Contributing

Contributions are welcome. Schema and transform contributions must be licensed under CC-BY-SA 4.0.

---

Maintained by [Asoba Corporation](https://asoba.co)

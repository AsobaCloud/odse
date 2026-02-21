# Sample Data Fixtures

Synthetic but realistic energy data for tutorials and QA testing. All data is generated — no real customer data.

## OEM-Specific Fixtures

| File | Source | Rows | Interval | System | Data Quality Issue |
|------|--------|------|----------|--------|--------------------|
| `huawei_fusionsolar_24h.csv` | Huawei FusionSolar | 264 | 5-min | ~8 kW residential | 2-hour gap (10:00–11:55), 1 warning at 15:00 |
| `enphase_enlighten_24h.csv` | Enphase Enlighten | 288 | 5-min | 12 microinverters | 30-min zero-devices (07:00–07:25), partial reporting (13:00–13:10) |
| `solaredge_monitoring_24h.csv` | SolarEdge Monitoring | 288 | 5-min | 10 kW string inverter | Timezone inconsistency: first 12h have +02:00, rest have none |

## Generic Historian Fixture

| File | Rows | Interval | Notes |
|------|------|----------|-------|
| `generic_historian_7d.csv` | 2016 | 5-min | 7-day export with non-standard columns, cumulative energy counter, 3 fault events on day 3 |
| `generic_mapping.yaml` | — | — | Column mapping file for use with `source="csv"` |

## Column Formats

**Huawei:** `timestamp, power, inverter_state, run_state` — standard FusionSolar CSV export format.

**Enphase:** `end_at, wh_del, devices_reporting` — epoch timestamps, watt-hours, microinverter count.

**SolarEdge:** `date, totalActivePower, inverterMode, operationMode, apparentPower, reactivePower, cosPhi` — flattened monitoring API response.

**Generic:** `Timestamp, ActiveEnergy_kWh, ReactivePower_kVAr, SiteTag, InvStatus` — deliberately non-standard to demonstrate column mapping.

## Usage

```python
from odse import transform

# OEM-specific transform
rows = transform("examples/data/huawei_fusionsolar_24h.csv", source="huawei")

# Generic CSV with mapping
rows = transform("examples/data/generic_historian_7d.csv", source="csv",
                 mapping="examples/data/generic_mapping.yaml")
```

```bash
# CLI
odse transform --source huawei --input examples/data/huawei_fusionsolar_24h.csv
```

# BESS Transforms (SEP-026)

Status: Draft
Last updated: 2026-06-27

## Purpose

Battery energy storage systems (BESS) produce fundamentally different telemetry from solar or wind: charge/discharge cycles, state of charge, cell-level temperature and voltage, degradation metrics, and dispatch commands. ODS-E added `soc` and `soh` in v0.7.0 but had no BESS transformers, no cell-level fields, and no dispatch-mode representation.

This SEP defines:

1. Eight new optional schema fields for BESS dispatch telemetry.
2. Two transformer classes (Sungrow PowerTitan, BYD BatteryBox).
3. A `bess_dispatch` conformance profile for dispatch validation.

## Context

Globeleq's Red Sands project (153 MW / 612 MWh, Northern Cape, South Africa) is Africa's largest standalone BESS, using Sungrow PowerTitan 2.0 with a 15-year O&M service agreement. BYD is the other dominant BESS supplier in the South African market. Battery dispatch optimization requires standardized data covering charge/discharge cycles against spot pricing, grid congestion signals, and degradation curves.

## Scope

**Affected surfaces:** runtime, transforms, schemas.

**Decision class:** Normative (adds optional schema fields; no existing fields changed). Requires 2 maintainer approvals + 7-day public comment window per [GOVERNANCE.md](../GOVERNANCE.md).

## New Schema Fields

All fields are optional and additive. Existing records remain valid.

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| `charge_kWh` | number | min 0 | Energy charged into the battery during this interval (kWh). |
| `discharge_kWh` | number | min 0 | Energy discharged from the battery during this interval (kWh). |
| `cycle_count` | number | min 0 | Cumulative number of charge/discharge cycles completed. |
| `cell_temp_min_c` | number | — | Minimum cell temperature observed this interval (°C). |
| `cell_temp_max_c` | number | — | Maximum cell temperature observed this interval (°C). |
| `cell_voltage_min_v` | number | min 0 | Minimum cell voltage observed this interval (V). |
| `cell_voltage_max_v` | number | min 0 | Maximum cell voltage observed this interval (V). |
| `dispatch_mode` | string | enum: `charging`, `discharging`, `standby`, `balancing` | Battery dispatch state for this interval. |

The existing `soc` (state of charge, 0-100) and `soh` (state of health, 0-100) fields — added in v0.7.0 — are reused for BESS records. No duplicate `*_pct` fields are introduced.

## Transformers

### Sungrow PowerTitan (`sungrow_bess`)

- **Source key:** `sungrow_bess` (aliases: `sungrow-bess`, `powertitan`)
- **Class:** `SungrowBESSTransformer`
- **Input:** iSolarCloud BESS telemetry JSON (device_telemetry-style payload with BESS-specific tags)
- **Transform spec:** [`transforms/sungrow-powertitan.yaml`](../transforms/sungrow-powertitan.yaml)

Maps Sungrow-specific tags to ODS-E fields:

| iSolarCloud tag | ODS-E field |
|-----------------|-------------|
| `soc` | `soc` |
| `soh` | `soh` |
| `charge_power` (W) | `charge_kWh` (via power × interval) |
| `discharge_power` (W) | `discharge_kWh` (via power × interval) |
| `cycle_count` | `cycle_count` |
| `min_cell_temp` | `cell_temp_min_c` |
| `max_cell_temp` | `cell_temp_max_c` |
| `min_cell_voltage` | `cell_voltage_min_v` |
| `max_cell_voltage` | `cell_voltage_max_v` |
| `run_mode` (0/1/2/3) | `dispatch_mode` (standby/charging/discharging/balancing) |
| `status_code` | `error_type` (via status mapping) |
| `active_power` (W) | `kW` (W → kW) |

Power sign convention: `active_power < 0` = charging, `active_power > 0` = discharging. When both `charge_power` and `discharge_power` are present, they take precedence over sign-based inference.

### BYD BatteryBox (`byd_bess`)

- **Source key:** `byd_bess` (aliases: `byd-bess`, `byd`)
- **Class:** `BYDBESSTransformer`
- **Input:** BYD BatteryBox / BMS CSV export
- **Transform spec:** [`transforms/byd-bess.yaml`](../transforms/byd-bess.yaml)

Maps BYD BMS CSV columns to ODS-E fields:

| BYD column | ODS-E field |
|------------|-------------|
| `soc` | `soc` |
| `soh` | `soh` |
| `charge_power_kw` | `charge_kWh` (via power × interval) |
| `discharge_power_kw` | `discharge_kWh` (via power × interval) |
| `cycle_count` | `cycle_count` |
| `cell_temp_min` | `cell_temp_min_c` |
| `cell_temp_max` | `cell_temp_max_c` |
| `cell_voltage_min` | `cell_voltage_min_v` |
| `cell_voltage_max` | `cell_voltage_max_v` |
| `dispatch_mode` | `dispatch_mode` (inferred from power flow if absent/invalid) |
| `bms_status` (0-4) | `error_type` (normal/standby/warning/fault/offline) |

The BYD CSV uses power in kilowatts (not watts, unlike Sungrow). The `interval_minutes` parameter (default 15) controls kWh computation.

## Conformance Profile: `bess_dispatch`

A validator-level conformance profile layered on top of the schema. Does not change the schema itself.

### Required Fields

| Field | Value Constraint |
|-------|-----------------|
| `dispatch_mode` | must be one of `charging`, `discharging`, `standby`, `balancing` |
| `soc` | — |

### Usage

```python
from odse import validate

result = validate(record, profile="bess_dispatch")
```

Profile validation runs after schema validation passes. Error codes follow the existing profile convention (`UNKNOWN_PROFILE`, `PROFILE_FIELD_MISSING`, `PROFILE_VALUE_MISMATCH`).

## Compatibility Impact

**Normative — additive only.** All new fields are optional. No existing fields are changed, removed, or renamed. Existing records (solar, wind, meter, regulatory) remain valid without modification. The `bess_dispatch` profile is opt-in and does not affect default validation.

## Out of Scope

- Degradation modeling / SOH prediction (Ona IP).
- Dispatch optimization against spot pricing (Ona IP).
- Thermal management analytics.

## Related Docs

- [Conformance Profiles](conformance-profiles.md) — profile validation framework (SEP-002)
- [Schema: energy-timeseries](../schemas/energy-timeseries.json)
- [Governance](../GOVERNANCE.md) — SEP lifecycle and approval thresholds

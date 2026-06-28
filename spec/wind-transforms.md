# Wind Turbine SCADA Transforms (SEP-025)

Status: Draft
Last updated: 2026-06-27

## Purpose

Wind turbines produce fundamentally different telemetry from solar inverters or battery storage: wind speed, rotor RPM, blade pitch angles, and nacelle orientation. ODS-E had 10 solar inverter transforms and 2 BESS transforms but zero wind turbine transforms. This SEP adds wind-specific schema fields and three transformer classes for the dominant wind turbine OEMs in the African IPP market.

This SEP defines:

1. Four new optional schema fields for wind turbine telemetry.
2. Three transformer classes (Vestas, Siemens Gamesa, Nordex).
3. A `wind_scada` conformance profile for wind record validation.

## Context

Globeleq manages 1,794 MW of generation capacity including significant wind across multiple African countries. The three dominant wind turbine OEMs in the African IPP market are Vestas, Siemens Gamesa, and Nordex. Their SCADA systems export different tag naming conventions, status codes, and data structures. Adding wind transforms extends ODS-E from a solar-and-storage tool to a full renewable energy data standard.

## Scope

**Affected surfaces:** runtime, transforms, schemas.

**Decision class:** Normative (adds optional schema fields; no existing fields changed). Requires 2 maintainer approvals + 7-day public comment window per [GOVERNANCE.md](../GOVERNANCE.md).

## New Schema Fields

All fields are optional and additive. Existing records remain valid.

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| `wind_speed_ms` | number | min 0 | Wind speed in meters per second. |
| `rotor_rpm` | number | min 0 | Rotor revolutions per minute. |
| `blade_pitch_deg` | number | — | Blade pitch angle in degrees. |
| `nacelle_direction_deg` | number | 0–360 | Nacelle orientation in degrees (compass bearing). |

These fields capture the fundamental wind telemetry that has no equivalent in solar or BESS schemas. Wind speed is the primary driver of production; rotor RPM and blade pitch indicate turbine operating state; nacelle direction enables yaw alignment analysis.

## Transformers

### Vestas (`vestas`)

- **Source key:** `vestas` (aliases: `vestas-online`)
- **Class:** `VestasTransformer`
- **Input:** Vestas Online Business SCADA CSV export
- **Transform spec:** [`transforms/vestas-online.yaml`](../transforms/vestas-online.yaml)

Maps Vestas SCADA CSV columns to ODS-E fields:

| Vestas column | ODS-E field |
|---------------|-------------|
| `active_power_kw` | `kW`, `kWh` (via power × interval) |
| `wind_speed` | `wind_speed_ms` |
| `rotor_rpm` | `rotor_rpm` |
| `nacelle_position` | `nacelle_direction_deg` |
| `blade_pitch` | `blade_pitch_deg` |
| `generator_temp` | `temperature` |
| `grid_frequency` | `frequency` |
| `turbine_state` (0–5) | `error_type` (via state mapping) |

Turbine state mapping:

| Code | State | ODS-E error_type |
|------|-------|-----------------|
| 0 | Offline | `offline` |
| 1 | Standby | `standby` |
| 2 | Normal | `normal` |
| 3 | Warning | `warning` |
| 4 | Fault | `fault` |
| 5 | Maintenance | `warning` |

The default `interval_minutes` is 10, matching the standard Vestas SCADA 10-minute reporting interval.

### Siemens Gamesa (`siemens_gamesa`)

- **Source key:** `siemens_gamesa` (aliases: `siemens-gamesa`, `sgre`)
- **Class:** `SiemensGamesaTransformer`
- **Input:** Siemens Gamesa Diagnostic System SCADA CSV export
- **Transform spec:** [`transforms/siemens-gamesa-diagnostic.yaml`](../transforms/siemens-gamesa-diagnostic.yaml)

Maps Siemens Gamesa SCADA CSV columns to ODS-E fields:

| SGRE column | ODS-E field |
|-------------|-------------|
| `active_power_kw` | `kW`, `kWh` (via power × interval) |
| `reactive_power_kvar` | `kVAr` |
| `wind_speed_nacelle` | `wind_speed_ms` (fallback: `wind_speed_metmast`) |
| `rotor_speed` | `rotor_rpm` |
| `pitch_angle` | `blade_pitch_deg` |
| `bearing_temp` | `temperature` |
| `availability_status` | `error_type` (via status mapping) |

Availability status mapping:

| Status | ODS-E error_type |
|--------|-----------------|
| `full` | `normal` |
| `limited` | `warning` |
| `standstill` | `standby` |
| `error` | `fault` |
| `offline` | `offline` |
| `maintenance` | `warning` |

Wind speed is measured at two locations: the nacelle-mounted anemometer (`wind_speed_nacelle`) and the met mast (`wind_speed_metmast`). The transformer prefers the nacelle reading and falls back to the met mast when the nacelle value is absent.

### Nordex (`nordex`)

- **Source key:** `nordex` (aliases: `nordex-control`)
- **Class:** `NordexTransformer`
- **Input:** Nordex Control SCADA CSV export
- **Transform spec:** [`transforms/nordex-control.yaml`](../transforms/nordex-control.yaml)

Maps Nordex SCADA CSV columns to ODS-E fields:

| Nordex column | ODS-E field |
|---------------|-------------|
| `active_power_kw` | `kW`, `kWh` (via power × interval) |
| `wind_speed` | `wind_speed_ms` |
| `rotor_speed` | `rotor_rpm` |
| `blade_angle` | `blade_pitch_deg` |
| `generator_temp` | `temperature` |
| `turbine_status` | `error_type` (via status mapping) |

Turbine status mapping:

| Status | ODS-E error_type |
|--------|-----------------|
| `running` | `normal` |
| `standby` | `standby` |
| `paused` | `standby` |
| `warning` | `warning` |
| `error` | `fault` |
| `offline` | `offline` |
| `maintenance` | `warning` |

The `paused` state is mapped to `standby` as it represents an intentional temporary stop (e.g., waiting for wind), distinct from a manual `standby` hold.

## Conformance Profile: `wind_scada`

A validator-level conformance profile layered on top of the schema. Does not change the schema itself.

### Required Fields

| Field | Value Constraint |
|-------|-----------------|
| `wind_speed_ms` | — |

### Usage

```python
from odse import validate

result = validate(record, profile="wind_scada")
```

Profile validation runs after schema validation passes. Error codes follow the existing profile convention (`UNKNOWN_PROFILE`, `PROFILE_FIELD_MISSING`, `PROFILE_VALUE_MISMATCH`).

## Compatibility Impact

**Normative — additive only.** All new fields are optional. No existing fields are changed, removed, or renamed. Existing records (solar, BESS, meter, regulatory) remain valid without modification. The `wind_scada` profile is opt-in and does not affect default validation.

## Out of Scope

- Live SCADA API clients (only CSV/JSON export transforms).
- Turbine-specific analytics (power curves, wake modeling).
- Met mast data transforms (met mast wind speed is used only as a fallback for nacelle wind speed).
- Curtailed energy estimation for wind (existing `curtailed_kWh` field applies).

## Related Docs

- [Conformance Profiles](conformance-profiles.md) — profile validation framework (SEP-002)
- [BESS Transforms](bess-transforms.md) — BESS schema fields and transformers (SEP-026)
- [Schema: energy-timeseries](../schemas/energy-timeseries.json)
- [Governance](../GOVERNANCE.md) — SEP lifecycle and approval thresholds

# Market Context Extensions (Settlement, Tariff, Topology)

This document defines additive ODS-E conventions for market settlement context, tariff context, and municipal/grid topology.

These fields are optional and non-breaking. They are intended to support wheeling, bilateral trading, municipal process standardization, and market-ready analytics.

## 1) Canonical ID Model

ODS-E defines canonical identifier *formats*. Issuance authority remains external (regulator, market operator, municipality, network utility, or licensed participant).

### 1.1 Party IDs

Pattern:

`<authority>:<type>:<id>`

Examples:

- `za-nersa:trader:ETANA-001`
- `za-city-capetown:municipality:CCT`
- `za-eskom:network_operator:WC-01`

### 1.2 Tariff Schedule IDs

Pattern:

`<authority>:<municipality>:<code>:v<version>`

Examples:

- `za-city-capetown:cpt:LT-MD-2026:v1`
- `za-eskom:national:TOU-2026:v3`

### 1.3 Municipality IDs

Pattern:

`za.<province>.<municipality>`

Examples:

- `za.wc.city_of_cape_town`
- `za.ec.nelson_mandela_bay`

## 2) Energy Timeseries Extensions

The following optional fields are added to `schemas/energy-timeseries.json`:

Settlement:

- `seller_party_id`
- `buyer_party_id`
- `network_operator_id`
- `wheeling_agent_id`
- `settlement_period_start`
- `settlement_period_end`
- `loss_factor`
- `contract_reference`

Tariff:

- `tariff_schedule_id`
- `tariff_period` (`peak`, `standard`, `off_peak`, `critical_peak`)
- `tariff_currency` (ISO 4217)
- `tariff_version_effective_at`
- `energy_charge_component`
- `network_charge_component`

## 3) Asset Metadata Topology Extensions

The following optional fields are added to `location` in `schemas/asset-metadata.json`:

- `country_code` (ISO 3166-1 alpha-2)
- `municipality_id`
- `municipality_name`
- `distribution_zone`
- `feeder_id`
- `voltage_level` (`LV`, `MV`, `HV`, `EHV`)
- `meter_id`
- `connection_point_id`
- `licensed_service_area`

## 4) Compatibility and Migration

- These changes are additive and optional.
- Existing valid payloads remain valid.
- No existing required fields are changed.
- Implementers can adopt these fields incrementally by workflow.

## 5) Example

```json
{
  "timestamp": "2026-02-17T12:00:00+02:00",
  "kWh": 124.6,
  "error_type": "normal",
  "direction": "generation",
  "seller_party_id": "za-nersa:trader:ETANA-001",
  "buyer_party_id": "za-city-capetown:offtaker:SITE-9921",
  "network_operator_id": "za-eskom:network_operator:WC-01",
  "settlement_period_start": "2026-02-17T12:00:00+02:00",
  "settlement_period_end": "2026-02-17T12:30:00+02:00",
  "loss_factor": 0.03,
  "tariff_schedule_id": "za-city-capetown:cpt:LT-MD-2026:v1",
  "tariff_period": "standard",
  "tariff_currency": "ZAR",
  "energy_charge_component": 358.22,
  "network_charge_component": 62.91
}
```

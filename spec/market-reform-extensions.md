# Market Reform Extensions

Status: Draft
Last updated: 2026-02-17

## Purpose

This document defines additive ODS-E schema extensions addressing data interoperability gaps identified in the SAETA "Policy to Power" report (February 2026). Each extension maps to specific reform actions needed for South Africa's transition to a competitive, multi-market electricity system.

All fields are optional and non-breaking. Existing valid payloads remain valid. Implementers can adopt these fields incrementally by workflow.

These extensions build on the foundation established in [Market Context Extensions](market-context.md), which introduced settlement party IDs, tariff components, and municipal/grid topology.

## 1) Wheeling Transaction Envelope

**SAETA context**: Three wheeling models are active in South Africa -- traditional (physical delivery on a single network), virtual (financial settlement across Eskom Distribution or municipal connections), and portfolio (multi-to-multi under a single arrangement). The report identifies fragmented data exchange, manual reconciliation, and inconsistent treatment across networks as barriers to scaling wheeling (Actions 7, 8). It calls for "standardised and automated reconciliation and billing" and "modern digital systems for data exchange, energy accounting and financial settlement."

### Timeseries Fields

| Field | Type | Description |
|-------|------|-------------|
| `wheeling_type` | enum: `traditional`, `virtual`, `portfolio` | Wheeling model for this transaction |
| `injection_point_id` | string | Grid injection point identifier for the wheeling path |
| `offtake_point_id` | string | Grid offtake point identifier for the wheeling path |
| `wheeling_status` | enum: `provisional`, `confirmed`, `reconciled`, `disputed` | Reconciliation status of this wheeling record |
| `wheeling_path_id` | string | Reference to a registered wheeling path or schedule |

### Notes

- `injection_point_id` and `offtake_point_id` use free-form strings because point naming conventions vary across Eskom, municipal, and cross-border networks. Implementers should document their naming convention.
- For virtual wheeling, the injection and offtake points represent financial settlement boundaries, not physical electron flow.
- `wheeling_status` tracks the lifecycle of a wheeling record through reconciliation. Records typically move from `provisional` (initial meter read) to `confirmed` (validated against counter-party) to `reconciled` (financially settled).
- These fields complement the existing `wheeling_agent_id`, `seller_party_id`, and `buyer_party_id` from the market context extensions.

### Example

```json
{
  "timestamp": "2026-02-17T14:00:00+02:00",
  "kWh": 87.3,
  "error_type": "normal",
  "direction": "generation",
  "seller_party_id": "za-nersa:trader:ENPOWER-001",
  "buyer_party_id": "za-city-capetown:offtaker:METRO-4401",
  "wheeling_agent_id": "za-nersa:trader:ENPOWER-001",
  "network_operator_id": "za-eskom:network_operator:WC-01",
  "wheeling_type": "virtual",
  "injection_point_id": "NCAPE-SOLAR-GEN-12",
  "offtake_point_id": "CCT-DIST-MV-BELLVILLE-03",
  "wheeling_status": "confirmed",
  "wheeling_path_id": "WP-2026-ENPOWER-CCT-003",
  "loss_factor": 0.032,
  "contract_reference": "PPA-ENPOWER-CCT-2025-017"
}
```

## 2) Tariff Component Granularity

**SAETA context**: NERSA has separated Eskom's generation, transmission, and distribution charges for the first time under MYPD6. The Electricity Pricing Policy (EPP) revision aims to align regulated pricing with a competitive market. The report describes the need for cost-reflective, unbundled tariffs that distinguish fixed from variable costs and make non-bypassable charges transparent (Action 2). Tariffs rose 937% between 2007 and 2024.

### Timeseries Fields

| Field | Type | Description |
|-------|------|-------------|
| `generation_charge_component` | number >= 0 | Unbundled generation charge for this interval |
| `transmission_charge_component` | number >= 0 | Transmission use-of-system charge |
| `distribution_charge_component` | number >= 0 | Distribution network charge |
| `ancillary_service_charge_component` | number >= 0 | Ancillary services levy (frequency control, reserves) |
| `non_bypassable_charge_component` | number >= 0 | Non-bypassable charges (cross-subsidies, FBE contributions) |
| `environmental_levy_component` | number >= 0 | Environmental or carbon levy |

### Relationship to Existing Fields

The existing `energy_charge_component` and `network_charge_component` from the market context extensions represent a two-part split. These new fields provide a finer decomposition:

- `energy_charge_component` ≈ `generation_charge_component` + `ancillary_service_charge_component`
- `network_charge_component` ≈ `transmission_charge_component` + `distribution_charge_component`
- `non_bypassable_charge_component` and `environmental_levy_component` are additional line items

Implementers may use either the two-part split or the granular decomposition. If both are present, the granular fields take precedence. The two-part fields remain valid for systems that do not yet unbundle further.

### Example

```json
{
  "timestamp": "2026-02-17T08:00:00+02:00",
  "kWh": 250.0,
  "error_type": "normal",
  "direction": "consumption",
  "tariff_schedule_id": "za-eskom:national:TOU-2026:v3",
  "tariff_period": "peak",
  "tariff_currency": "ZAR",
  "generation_charge_component": 425.00,
  "transmission_charge_component": 87.50,
  "distribution_charge_component": 112.75,
  "ancillary_service_charge_component": 18.25,
  "non_bypassable_charge_component": 32.50,
  "environmental_levy_component": 9.75
}
```

## 3) Curtailment Event Tracking

**SAETA context**: The GCAR congestion curtailment mechanism (capped at 4%) is active in the Western and Eastern Cape. Over 100 curtailment events were recorded this financial year, up from fewer than 30 the prior year. IPPs are compensated through existing ancillary-services frameworks, with recoverable costs capped under MYPD6. Curtailment is a material risk for IPPs and traders and a core operational constraint for the NTCSA (Action 5, Action 8).

### Timeseries Fields

| Field | Type | Description |
|-------|------|-------------|
| `curtailment_flag` | boolean | Whether generation was curtailed during this interval |
| `curtailment_type` | enum: `congestion`, `frequency`, `voltage`, `instruction`, `other` | Reason for curtailment |
| `curtailed_kWh` | number >= 0 | Estimated generation lost to curtailment during this interval |
| `curtailment_instruction_id` | string | Reference to the system operator dispatch instruction |

### Notes

- `curtailed_kWh` represents estimated lost production, not metered output. It is typically derived from forecasted or rated output minus actual metered generation. The estimation method should be documented by the implementer.
- `curtailment_type` values:
  - `congestion` -- network capacity constraint (the GCAR mechanism)
  - `frequency` -- system frequency management
  - `voltage` -- local voltage regulation
  - `instruction` -- direct system operator dispatch instruction
  - `other` -- any other cause
- When `curtailment_flag` is `true`, the `kWh` field reflects actual metered output (reduced), while `curtailed_kWh` reflects the estimated shortfall.

### Example

```json
{
  "timestamp": "2026-02-17T12:30:00+02:00",
  "kWh": 62.1,
  "error_type": "normal",
  "direction": "generation",
  "curtailment_flag": true,
  "curtailment_type": "congestion",
  "curtailed_kWh": 41.4,
  "curtailment_instruction_id": "NTCSA-GCAR-2026-02-17-0034"
}
```

## 4) BRP / Imbalance Settlement Context

**SAETA context**: The SAWEM introduces Balance Responsible Parties (BRPs) who must forecast supply/demand and settle imbalances. All generators >= 10MW are automatically BRPs. The Market Operator manages the Day-Ahead Market, Intra-Day Market, and Balancing Market. Market participants submit hourly bids (MW and price) and are settled against actual delivery. Imbalance costs incentivize forecast accuracy and are a core pricing signal in the wholesale market (Action 9).

### Timeseries Fields

| Field | Type | Description |
|-------|------|-------------|
| `balance_responsible_party_id` | string (party ID pattern) | The BRP assigned for this connection point and interval |
| `forecast_kWh` | number | Nominated/scheduled volume for this interval |
| `settlement_type` | enum: `bilateral`, `sawem_day_ahead`, `sawem_intra_day`, `balancing`, `ancillary` | Market segment for settlement |
| `imbalance_kWh` | number | Difference between forecast and actual (positive = over-delivery, negative = under-delivery) |

### Notes

- `balance_responsible_party_id` follows the canonical party ID pattern (`authority:type:id`). Example: `za-nersa:brp:ETANA-BRP-01`.
- `forecast_kWh` represents the nominated or scheduled volume the BRP committed to for this interval, as submitted to the Market Operator.
- `imbalance_kWh` = `kWh` - `forecast_kWh`. It can be positive (over-delivery/under-consumption) or negative (under-delivery/over-consumption).
- `settlement_type` identifies which market segment governs settlement for this record:
  - `bilateral` -- settled under bilateral contract outside the SAWEM
  - `sawem_day_ahead` -- settled via the Day-Ahead Market
  - `sawem_intra_day` -- settled via the Intra-Day Market
  - `balancing` -- settled via the Balancing Market (residual imbalances)
  - `ancillary` -- ancillary services (reserves, frequency control)

### Example

```json
{
  "timestamp": "2026-02-17T15:00:00+02:00",
  "kWh": 312.5,
  "error_type": "normal",
  "direction": "generation",
  "balance_responsible_party_id": "za-nersa:brp:ETANA-BRP-01",
  "forecast_kWh": 320.0,
  "settlement_type": "sawem_day_ahead",
  "imbalance_kWh": -7.5,
  "settlement_period_start": "2026-02-17T15:00:00+02:00",
  "settlement_period_end": "2026-02-17T15:30:00+02:00"
}
```

## 5) Municipal Reconciliation

**SAETA context**: Municipal distributors manage about 40% of the grid. Arrears to Eskom exceed R105bn. Distribution Agency Agreements (DAAs) are being deployed for 14 high-arrears municipalities, with Eskom acting as agent for billing, collections, and maintenance. The EDI reform roadmap defines 3 pathways based on municipal capacity. Only 10 municipalities have adopted wheeling policies; only 7 have approved tariffs. "Performance-based regulation, systematic benchmarking and credible consequence management are critical to the success of EDI reform" (Action 6).

### Timeseries Fields

| Field | Type | Description |
|-------|------|-------------|
| `billing_period` | string | Billing cycle reference (e.g., `2026-02` for monthly, `2026-W07` for weekly) |
| `billed_kWh` | number >= 0 | Billed quantity for this interval (may differ from metered kWh due to adjustments, estimates, or loss allocation) |
| `billing_status` | enum: `metered`, `estimated`, `adjusted`, `disputed` | Data quality/origin of the billed quantity |
| `daa_reference` | string | Distribution Agency Agreement reference, if the municipality is under a DAA with Eskom Distribution |

### Notes

- `billing_period` uses ISO 8601 partial date formats. Monthly: `2026-02`. Weekly: `2026-W07`. This is a grouping key, not a date range.
- `billed_kWh` may differ from the metered `kWh` for several reasons: estimated reads, loss adjustments, theft adjustments, or billing corrections. The `billing_status` field indicates why.
- `billing_status` values:
  - `metered` -- directly from a validated meter read
  - `estimated` -- no meter read available; estimated from historical profile
  - `adjusted` -- metered but adjusted for losses, corrections, or audits
  - `disputed` -- under dispute between parties
- `daa_reference` is relevant for the 14+ municipalities where Eskom Distribution acts as agent under a DAA. It links the record to the governance arrangement.

### Example

```json
{
  "timestamp": "2026-02-17T10:00:00+02:00",
  "kWh": 45.2,
  "error_type": "normal",
  "direction": "consumption",
  "buyer_party_id": "za-city-emfuleni:municipality:EMF",
  "network_operator_id": "za-eskom:distribution:GT-01",
  "billing_period": "2026-02",
  "billed_kWh": 44.8,
  "billing_status": "adjusted",
  "daa_reference": "DAA-ESKOM-EMFULENI-2025-001"
}
```

## 6) Grid Capacity / Connection Status

**SAETA context**: Grid access is the binding constraint on new generation. The GCAR introduces 3 milestones (pre-feasibility, capacity reservation, capacity allocation) to structure the queue and prevent speculative lock-up. The NTCSA must add 14,500km of new lines and 210 transformers by 2034. Eskom's discretion in determining "readiness" creates barriers for traders and IPPs. Non-discriminatory grid access is foundational to the SAWEM (Actions 5, 8).

### Asset Metadata Fields (under `location`)

| Field | Type | Description |
|-------|------|-------------|
| `connection_status` | enum: `applied`, `pre_feasibility`, `reserved`, `allocated`, `connected`, `decommissioned` | Current status in the grid connection lifecycle |
| `allocated_capacity_kw` | number >= 0 | Grid capacity allocated to this asset |
| `connection_agreement_ref` | string | Connection or use-of-system agreement reference |
| `grid_access_queue_date` | string (date) | Date the asset entered the capacity allocation queue |
| `gcar_milestone` | enum: `pre_feasibility`, `capacity_reservation`, `capacity_allocation` | Current GCAR milestone achieved |

### Notes

- `connection_status` tracks the full lifecycle:
  - `applied` -- application submitted, not yet assessed
  - `pre_feasibility` -- pre-feasibility study completed (GCAR milestone 1)
  - `reserved` -- capacity reserved pending construction readiness (GCAR milestone 2)
  - `allocated` -- capacity formally allocated (GCAR milestone 3)
  - `connected` -- physically connected and energized
  - `decommissioned` -- disconnected from the grid
- `gcar_milestone` specifically tracks the NERSA GCAR framework. It may overlap with `connection_status` but provides the regulatory-specific reference.
- `allocated_capacity_kw` may differ from `capacity_kw` (nameplate) if the grid allocation is constrained below nameplate rating.
- `grid_access_queue_date` establishes priority under the "first ready, first served" principle.

### Example

```json
{
  "asset_id": "NCAPE-SOLAR-GEN-12",
  "location": {
    "latitude": -31.42,
    "longitude": 19.08,
    "timezone": "Africa/Johannesburg",
    "country_code": "ZA",
    "municipality_id": "za.nc.hantam",
    "voltage_level": "MV",
    "connection_point_id": "ESKOM-TX-KLEINZEE-33KV-F04",
    "connection_status": "allocated",
    "allocated_capacity_kw": 75000,
    "connection_agreement_ref": "COSA-NTCSA-2025-NCape-0172",
    "grid_access_queue_date": "2024-06-15",
    "gcar_milestone": "capacity_allocation"
  },
  "capacity_kw": 80000,
  "oem": "LONGi",
  "asset_type": "solar_pv",
  "commissioning_date": "2026-09-01"
}
```

## 7) Green Attribute / Certificate Tracking

**SAETA context**: Access to lower-carbon electricity through wheeling is becoming "a commercial and compliance necessity." The report highlights EU CBAM, carbon tax, carbon budgets, and NDC targets as drivers. Traders offer "green power with renewable tradable attributes" and the report mentions "tradable electricity tokens" as a virtual wheeling concept. Energy-intensive exporters need verifiable clean-energy provenance for CBAM compliance and competitiveness (Actions 7, 8).

### Timeseries Fields

| Field | Type | Description |
|-------|------|-------------|
| `renewable_attribute_id` | string | Certificate or credit identifier (e.g., I-REC tracking number) |
| `certificate_standard` | enum: `i_rec`, `rego`, `go`, `rec`, `tigr`, `other` | Certificate scheme under which the attribute is issued |
| `verification_status` | enum: `pending`, `issued`, `retired`, `cancelled` | Lifecycle status of the renewable attribute |
| `carbon_intensity_gCO2_per_kWh` | number >= 0 | Carbon intensity of the generation source in grams CO2e per kWh |

### Notes

- ODS-E carries attribute references; it does not act as a registry. Issuance, tracking, retirement, and verification remain with the certificate registry (e.g., I-REC, Evident).
- `certificate_standard` values:
  - `i_rec` -- International REC Standard (dominant in South Africa)
  - `rego` -- Renewable Energy Guarantees of Origin (UK)
  - `go` -- Guarantees of Origin (EU)
  - `rec` -- Renewable Energy Certificates (US)
  - `tigr` -- Tradable Instruments for Global Renewables (APX/Evident)
  - `other` -- any other scheme
- `verification_status` tracks the lifecycle:
  - `pending` -- generation recorded, certificate not yet issued
  - `issued` -- certificate issued by the registry
  - `retired` -- certificate retired on behalf of an end consumer (claimed)
  - `cancelled` -- certificate voided or expired
- `carbon_intensity_gCO2_per_kWh` enables CBAM-relevant calculations. For solar PV this is typically 0 (operational) or a lifecycle value (20-50 gCO2/kWh). The accounting methodology should be documented by the implementer.
- This field boundary follows the same pattern as `tariff_schedule_id`: ODS-E references external systems without replacing them.

### Example

```json
{
  "timestamp": "2026-02-17T11:00:00+02:00",
  "kWh": 156.8,
  "error_type": "normal",
  "direction": "generation",
  "seller_party_id": "za-nersa:generator:NCAPE-SOLAR-12",
  "renewable_attribute_id": "ZA-IREC-2026-0041822",
  "certificate_standard": "i_rec",
  "verification_status": "issued",
  "carbon_intensity_gCO2_per_kWh": 0
}
```

## 8) Compatibility and Migration

- All changes are additive and optional.
- Existing valid payloads remain valid.
- No existing required fields are changed.
- No existing enum values are modified or removed.
- Implementers can adopt these fields incrementally by workflow.
- These extensions complement (do not replace) the fields defined in [Market Context Extensions](market-context.md).

## 9) SAETA Action Mapping

| Extension | SAETA Actions | Primary Stakeholders |
|-----------|--------------|---------------------|
| Wheeling transaction envelope | 7, 8 | Traders, IPPs, Eskom Distribution, municipalities |
| Tariff component granularity | 2 | NERSA, Eskom, municipalities, consumers |
| Curtailment event tracking | 5, 8 | IPPs, NTCSA, system operator |
| BRP / imbalance settlement | 9 | Market operator, BRPs, generators, traders |
| Municipal reconciliation | 6 | Municipalities, Eskom Distribution, NT |
| Grid capacity / connection status | 5, 8 | IPPs, traders, NTCSA, GAU |
| Green attribute tracking | 7, 8 | Traders, exporters, certificate registries |

## Related Docs

- [Market Context Extensions](market-context.md) -- settlement, tariff, and topology foundations
- [ComStock/ResStock Integration](comstock-integration.md) -- building benchmark joins
- [Municipal Emissions Modeling](municipal-emissions-modeling.md) -- US jurisdiction modeling
- [Schema: energy-timeseries](../schemas/energy-timeseries.json)
- [Schema: asset-metadata](../schemas/asset-metadata.json)

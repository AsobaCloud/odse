# SA Trading Conformance Profiles (SEP-002)

Status: Draft
Last updated: 2026-02-18

## Purpose

The `energy-timeseries` schema defines ~50 properties, of which only 3 are required (`timestamp`, `kWh`, `error_type`). All SA trading fields — party IDs, settlement, wheeling, BRP, municipal billing — are optional. This is correct for schema flexibility, but real trading workflows need minimum field sets enforced.

This document defines 4 **conformance profiles** that specify which fields must be present (and, in some cases, which values are allowed) for a record to be valid within a given operating context. Profiles are a validator-level concept layered on top of the schema; they do not change the schema itself.

These profiles map to SAETA reform actions defined in [Market Reform Extensions](market-reform-extensions.md):

| Profile | SAETA Actions | Use Case |
|---------|--------------|----------|
| `bilateral` | 7, 8 | PPA / bilateral trades |
| `wheeling` | 7, 8 | Wheeled energy across networks |
| `sawem_brp` | 9 | Wholesale market settlement |
| `municipal_recon` | 6 | Municipal billing / reconciliation |

## 1) Profile: `bilateral`

PPA and bilateral trade settlement. Both trading parties, the settlement window, the contract reference, and the settlement type must be present.

### Required Fields

| Field | Value Constraint |
|-------|-----------------|
| `seller_party_id` | — |
| `buyer_party_id` | — |
| `settlement_period_start` | — |
| `settlement_period_end` | — |
| `contract_reference` | — |
| `settlement_type` | must be `"bilateral"` |

### Example

```json
{
  "timestamp": "2026-02-18T14:00:00+02:00",
  "kWh": 87.3,
  "error_type": "normal",
  "direction": "generation",
  "seller_party_id": "nersa:gen:SOLARPK-001",
  "buyer_party_id": "nersa:offtaker:MUN042",
  "settlement_period_start": "2026-02-18T14:00:00+02:00",
  "settlement_period_end": "2026-02-18T14:30:00+02:00",
  "contract_reference": "PPA-SOLARPK-MUN042-2025-003",
  "settlement_type": "bilateral"
}
```

## 2) Profile: `wheeling`

Wheeled energy across networks. A superset of `bilateral` — all bilateral fields are required, plus the wheeling-specific fields that identify the network operator, wheeling model, injection/offtake points, reconciliation status, and loss factor.

### Required Fields

| Field | Value Constraint |
|-------|-----------------|
| `seller_party_id` | — |
| `buyer_party_id` | — |
| `settlement_period_start` | — |
| `settlement_period_end` | — |
| `contract_reference` | — |
| `settlement_type` | must be `"bilateral"` |
| `network_operator_id` | — |
| `wheeling_type` | — |
| `injection_point_id` | — |
| `offtake_point_id` | — |
| `wheeling_status` | — |
| `loss_factor` | — |

### Example

```json
{
  "timestamp": "2026-02-18T14:00:00+02:00",
  "kWh": 87.3,
  "error_type": "normal",
  "direction": "generation",
  "seller_party_id": "nersa:trader:ENPOWER-001",
  "buyer_party_id": "za-city-capetown:offtaker:METRO-4401",
  "settlement_period_start": "2026-02-18T14:00:00+02:00",
  "settlement_period_end": "2026-02-18T14:30:00+02:00",
  "contract_reference": "PPA-ENPOWER-CCT-2025-017",
  "settlement_type": "bilateral",
  "network_operator_id": "nersa:dso:eskom-tx",
  "wheeling_type": "virtual",
  "injection_point_id": "NCAPE-SOLAR-GEN-12",
  "offtake_point_id": "CCT-DIST-MV-BELLVILLE-03",
  "wheeling_status": "confirmed",
  "loss_factor": 0.032
}
```

## 3) Profile: `sawem_brp`

Wholesale market (SAWEM) settlement for Balance Responsible Parties. Requires the seller, the BRP, the settlement type (constrained to SAWEM-related values), the forecast volume, and the settlement window.

### Required Fields

| Field | Value Constraint |
|-------|-----------------|
| `seller_party_id` | — |
| `balance_responsible_party_id` | — |
| `settlement_type` | must be one of `"sawem_day_ahead"`, `"sawem_intra_day"`, `"balancing"`, `"ancillary"` |
| `forecast_kWh` | — |
| `settlement_period_start` | — |
| `settlement_period_end` | — |

### Example

```json
{
  "timestamp": "2026-02-18T15:00:00+02:00",
  "kWh": 312.5,
  "error_type": "normal",
  "direction": "generation",
  "seller_party_id": "nersa:gen:WINDCO-007",
  "balance_responsible_party_id": "nersa:brp:BRP-01",
  "settlement_type": "sawem_day_ahead",
  "forecast_kWh": 320.0,
  "settlement_period_start": "2026-02-18T15:00:00+02:00",
  "settlement_period_end": "2026-02-18T15:30:00+02:00",
  "imbalance_kWh": -7.5
}
```

## 4) Profile: `municipal_recon`

Municipal billing and reconciliation. Requires the buyer (municipality), billing period, billed quantity, and billing data quality status.

### Required Fields

| Field | Value Constraint |
|-------|-----------------|
| `buyer_party_id` | — |
| `billing_period` | — |
| `billed_kWh` | — |
| `billing_status` | — |

### Example

```json
{
  "timestamp": "2026-02-18T10:00:00+02:00",
  "kWh": 45.2,
  "error_type": "normal",
  "direction": "consumption",
  "buyer_party_id": "za-city-emfuleni:municipality:EMF",
  "billing_period": "2026-02",
  "billed_kWh": 44.8,
  "billing_status": "adjusted",
  "daa_reference": "DAA-ESKOM-EMFULENI-2025-001"
}
```

## 5) Cross-Reference Matrix

Rows are fields, columns are profiles. **R** = required (no value constraint), **V:x** = required with value constraint, **—** = not required by this profile.

| Field | `bilateral` | `wheeling` | `sawem_brp` | `municipal_recon` |
|-------|:-----------:|:----------:|:-----------:|:-----------------:|
| `seller_party_id` | R | R | R | — |
| `buyer_party_id` | R | R | — | R |
| `settlement_period_start` | R | R | R | — |
| `settlement_period_end` | R | R | R | — |
| `contract_reference` | R | R | — | — |
| `settlement_type` | V:`bilateral` | V:`bilateral` | V:`sawem_day_ahead`, `sawem_intra_day`, `balancing`, `ancillary` | — |
| `network_operator_id` | — | R | — | — |
| `wheeling_type` | — | R | — | — |
| `injection_point_id` | — | R | — | — |
| `offtake_point_id` | — | R | — | — |
| `wheeling_status` | — | R | — | — |
| `loss_factor` | — | R | — | — |
| `balance_responsible_party_id` | — | — | R | — |
| `forecast_kWh` | — | — | R | — |
| `billing_period` | — | — | — | R |
| `billed_kWh` | — | — | — | R |
| `billing_status` | — | — | — | R |

## 6) Validation Behaviour

Profile validation is invoked by passing a `profile` parameter to the `validate()` function:

```python
from odse import validate

result = validate(record, profile="bilateral")
```

### Error Codes

| Code | Meaning |
|------|---------|
| `UNKNOWN_PROFILE` | The profile name is not one of the 4 defined profiles |
| `PROFILE_FIELD_MISSING` | A field required by the profile is not present in the record |
| `PROFILE_VALUE_MISMATCH` | A field is present but its value does not satisfy the profile's value constraint |

### Gating

Profile validation runs **after** schema validation passes. If schema validation produces errors, profile validation is skipped. This prevents duplicate or confusing error messages when required base fields (like `timestamp`) are missing.

When no profile is specified, validation behaves exactly as before — only schema (and optionally semantic) checks run.

## Related Docs

- [Market Context Extensions](market-context.md) — settlement, tariff, and topology foundations
- [Market Reform Extensions](market-reform-extensions.md) — wheeling, curtailment, BRP, certificates
- [Schema: energy-timeseries](../schemas/energy-timeseries.json)

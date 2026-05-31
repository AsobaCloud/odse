# Eskom Data Ingest Guide

This guide covers the two primary ways to ingest South African energy data into the ODS-E ecosystem.

## 1. Eskom AMR (NRS 049 Standard)

For per-meter billing and wheeling reconciliation, ODSE supports the NRS 049 CSV export format.

### Key Fields
- `MeterNumber`: Used to generate the `asset_id` (prefix: `za-eskom:meter:`).
- `billing_status`: Mandatory for Eskom compliance (`metered`, `estimated`, `adjusted`, `disputed`).
- `kWh_Import` / `kWh_Export`: Tracked separately for net metering support.

### Usage
```bash
odse transform --source eskom_amr --input meter_reads.csv --output out.jsonl
```

## 2. Eskom Data Portal (National Aggregated Data)

The Eskom Data Portal (eskom.co.za/dataportal) provides wide-format CSVs via its "Data Request Form".

### Automatic "Melting"
The `EskomPortalTransformer` automatically "melts" the wide columns (one per station type) into ODS-E long format:
- `Thermal Generation` -> `za-eskom:generation:thermal`
- `Renewable Generation` -> `za-eskom:generation:renewable`
- `System Frequency` -> `za-eskom:grid:frequency`

### Usage
```bash
odse transform --source eskom --input portal_export.csv --output national_metrics.jsonl
```

## 3. Compliance & Validation

When using the `za-eskom` profile, the ODS-E validator enforces South African regulatory requirements:
- Presence of `billing_status`.
- Logical consistency between Import/Export and Net kWh.
- (Planned) Verification of `daa_reference` for municipal DAA portfolios.

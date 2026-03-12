# Regulatory Event Normalization

This document defines an additive normalization contract for regulatory notices, decisions, and procurement updates that sit outside the core ODS-E `energy-timeseries` and `asset-metadata` schemas.

## Scope

The contract is intended for application-layer ingestion of regulatory records across:

- United States (`US`)
- South Africa (`ZA`)
- Zimbabwe (`ZW`)

The normalized output schema is [`schemas/regulatory-event.json`](../schemas/regulatory-event.json). The reference transform mapping is [`transforms/regulatory-events-unified.yaml`](../transforms/regulatory-events-unified.yaml).

## Canonical Fields

Every normalized record must provide:

- `jurisdiction`
- `regulator`
- `event_type`
- `title`
- `published_date`
- `source_url`
- `source_system`
- `source_record_id`
- `schema_version`
- `transform_version`

Optional fields:

- `summary`
- `effective_date`
- `deadline_date`

## Source Adapters

The initial adapters are:

- `us_manual`: manually curated or already-structured US regulatory records
- `nersa`: NERSA homepage decision/news records
- `ippo`: South African IPP Office press-release feed
- `zera_seed`: Seeded ZERA publication catalog entries used when the official site blocks direct machine access

The `zera_seed` path is intentionally additive and explicit. It keeps Zimbabwe records in the shared contract while preserving the distinction between the canonical normalized schema and the source acquisition method.

## Conformance Notes

- This normalization is application-layer and does not modify the existing ODS-E `energy-timeseries` or `asset-metadata` contracts.
- `schema_version` is fixed at `regulatory-event.v1`.
- `transform_version` is source-specific and must change when source-field semantics change.

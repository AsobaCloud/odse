# Municipal Emissions Modeling Guide (US Jurisdictions)

Status: Draft guide for implementers
Last updated: 2026-02-17

## Purpose

This guide documents the recently added ODS-E integration hooks for leveraging NREL ComStock and ResStock data to help US municipal governments disaggregate emissions in their jurisdictions via modeling.

This is an application-layer implementation pattern. It does not change the core ODS-E schema.

## What Changed

ODS-E now includes documented hooks that make jurisdiction-level modeling easier when paired with ComStock/ResStock benchmark cohorts:

- Building metadata compatibility fields in `asset-metadata.json` for cohort joins.
- Consumption and net metering support in `energy-timeseries.json` (`direction`, `fuel_type`, `end_use`).
- Reference join pattern and benchmark ratio workflow in `spec/comstock-integration.md`.

Together, these enable municipal teams to estimate and compare energy/emissions intensity by building cohort, geography, and end use.

## Scope and Assumptions

- Focus: US municipal and county workflows.
- Typical use cases: climate action planning, ordinance reporting, neighborhood targeting, retrofit prioritization.
- Modeling outputs are estimates; they depend on source data quality, meter coverage, and cohort matching quality.

## Required Inputs

### 1) ODS-E asset metadata

At minimum, for each modeled asset/building:

- `asset_id`
- `building.building_type`
- `building.climate_zone`
- `building.vintage`
- `building.floor_area_sqm`
- `building.state`
- `building.county` (or local jurisdiction mapping equivalent)

### 2) ODS-E timeseries

At minimum:

- `timestamp`
- `kWh`
- `error_type`

For municipal emissions disaggregation, strongly recommended:

- `direction` (`consumption` for load accounting)
- `fuel_type` (electricity and optional non-electric fuels)
- `end_use` (for sector/end-use decomposition)

### 3) Jurisdiction mapping layer

A local mapping table is required to allocate assets to reporting boundaries.

Example columns:

- `asset_id`
- `city_name`
- `county_name`
- `tract_id` (optional)
- `district_id` (optional)

### 4) Benchmark cohorts

- ComStock and/or ResStock cohort datasets from NREL/OEDI.
- Cohort keys aligned to ODS-E building metadata fields.

## How-To 1: Build a Citywide Baseline

1. Ingest and validate ODS-E timeseries for a full reporting year.
2. Filter to `direction = 'consumption'` for demand-side accounting.
3. Aggregate annual kWh by `asset_id`.
4. Join each asset to building metadata.
5. Join assets to benchmark cohorts (ComStock/ResStock) on building type, climate zone, vintage, and state.
6. Compute baseline intensity metrics per cohort and city total.

Output:

- Citywide annual modeled energy/emissions baseline
- Cohort-level baseline table for policy analysis

## How-To 2: Disaggregate by Neighborhood or District

1. Start from the citywide baseline dataset.
2. Join `asset_id` to jurisdiction mapping (`district_id`, `tract_id`, or `neighborhood`).
3. Aggregate modeled kWh/emissions by geography and building cohort.
4. Rank areas by intensity gap vs benchmark median.

Output:

- District/neighborhood scorecard with modeled emissions intensity
- Priority map input table for interventions

## How-To 3: End-Use Opportunity Modeling

1. Restrict records to assets with populated `end_use`.
2. Aggregate consumption by `end_use` and geography.
3. Compare each end-use segment to matched benchmark cohorts.
4. Identify dominant contributors (for example, cooling-heavy districts).

Output:

- End-use decomposition for municipal action planning
- Ranked intervention candidates by potential modeled impact

## How-To 4: Reporting Export for Municipal Stakeholders

1. Prepare yearly summary tables with clear cohort definitions.
2. Include coverage metrics (assets included, floor area covered, missingness).
3. Include uncertainty notes for unmatched cohorts.
4. Export CSV/Parquet and a one-page methodology note.

Output:

- Reproducible reporting pack for city sustainability teams

## Project Starters

### Starter A: SQL Warehouse Starter

Best for teams with Snowflake/BigQuery/Postgres analytics workflows.

Initial structure:

- `odse_assets` (normalized asset metadata)
- `odse_timeseries` (validated ODS-E records)
- `jurisdiction_map` (asset-to-city/district mapping)
- `comstock` / `resstock` benchmark tables
- `municipal_emissions_model_v1` (materialized output)

First sprint checklist:

1. Load one city and one full year.
2. Reproduce EUI ratio logic from `spec/comstock-integration.md`.
3. Add district rollups.
4. Publish QA checks for coverage and null join rate.

### Starter B: Notebook Starter

Best for policy teams prototyping assumptions quickly.

Suggested notebook sections:

1. Data ingestion and validation summary
2. Cohort matching diagnostics
3. Citywide baseline charts
4. District disaggregation charts
5. End-use decomposition
6. Export tables for reporting

First sprint checklist:

1. Validate one sample jurisdiction.
2. Produce baseline + district outputs.
3. Document assumptions in markdown cells.

### Starter C: dbt-Style Transformation Starter

Best for teams running governed analytics pipelines.

Suggested model layers:

- `stg_odse_assets`
- `stg_odse_timeseries`
- `int_asset_annual_consumption`
- `int_asset_benchmark_match`
- `mart_municipal_emissions_disagg`

First sprint checklist:

1. Implement schema tests for required join keys.
2. Track model freshness and source coverage.
3. Version methodology in model docs.

## Quality Guardrails

- Track unmatched cohort rate by jurisdiction.
- Separate measured vs modeled fields in outputs.
- Version emission factors and conversion constants.
- Publish assumptions with each reporting run.

## Related Docs

- [ComStock/ResStock Integration Guide](comstock-integration.md)
- [Inverter API Access Setup](inverter-api-access.md)
- [Launch Kit](launch-kit.md)
- [Schema: energy-timeseries](../schemas/energy-timeseries.json)
- [Schema: asset-metadata](../schemas/asset-metadata.json)

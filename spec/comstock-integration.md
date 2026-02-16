# ComStock/ResStock Integration Guide

Status: Stub (field mapping + example query)
Last updated: 2026-02-16

## Purpose

This document shows how ODS-E building metadata can be joined to NREL ComStock and ResStock benchmark datasets. This is an **application-layer pattern**, not part of the core ODS-E schema. It enables partners to build benchmark and compliance products on top of ODS-E data.

## ODS-E Building Metadata Fields

The `building` object in `asset-metadata.json` contains fields designed for ComStock/ResStock compatibility:

| ODS-E Field | ComStock Column | ResStock Column | Notes |
|-------------|----------------|-----------------|-------|
| building.building_type | in.comstock_building_type | in.geometry_building_type_recs | 22-value enum covers both |
| building.climate_zone | in.ashrae_iecc_climate_zone_2006 | in.ashrae_iecc_climate_zone_2006 | ASHRAE/IECC zone string |
| building.vintage | in.vintage | in.vintage | Building age / code era |
| building.floor_area_sqm | in.floor_area (convert to sqft) | in.geometry_floor_area (convert to sqft) | ODS-E stores metric; ComStock/ResStock use sqft |
| building.state | in.state_abbreviation | in.state | Postal code |
| building.county | in.county_name | in.county | Name or FIPS |

## Example: JOIN ODS-E Asset to ComStock Benchmark

The following SQL shows how a partner would join ODS-E asset data to a ComStock baseline to compute an energy-use-intensity (EUI) benchmark ratio.

Assumes:
- `odse_assets` table: ODS-E asset-metadata records (one row per asset)
- `odse_timeseries` table: ODS-E energy-timeseries records
- `comstock` table: NREL ComStock annual results (available via OEDI data lake)

```sql
-- Step 1: Aggregate actual consumption from ODS-E timeseries
WITH actual AS (
    SELECT
        t.asset_id,
        SUM(t.kwh)                           AS annual_kwh,
        a.building_type,
        a.climate_zone,
        a.vintage,
        a.floor_area_sqm,
        a.state
    FROM odse_timeseries  t
    JOIN odse_assets       a ON a.asset_id = t.asset_id
    WHERE t.direction    = 'consumption'
      AND t.fuel_type    = 'electricity'
      AND t.timestamp   >= '2025-01-01'
      AND t.timestamp    < '2026-01-01'
    GROUP BY t.asset_id, a.building_type, a.climate_zone,
             a.vintage, a.floor_area_sqm, a.state
),

-- Step 2: Find the ComStock median EUI for matching building cohort
benchmark AS (
    SELECT
        "in.comstock_building_type"           AS building_type,
        "in.ashrae_iecc_climate_zone_2006"    AS climate_zone,
        "in.vintage"                          AS vintage,
        "in.state_abbreviation"               AS state,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY "out.site_energy_intensity_kbtu_per_sqft"
        )                                     AS median_eui_kbtu_sqft
    FROM comstock
    GROUP BY 1, 2, 3, 4
)

-- Step 3: Compare actual vs benchmark
SELECT
    ac.asset_id,
    ac.annual_kwh,
    ac.floor_area_sqm,
    -- Convert actual kWh to kBtu/sqft for apples-to-apples comparison
    (ac.annual_kwh * 3.412)
        / (ac.floor_area_sqm * 10.7639)      AS actual_eui_kbtu_sqft,
    bm.median_eui_kbtu_sqft,
    ROUND(
        ((ac.annual_kwh * 3.412) / (ac.floor_area_sqm * 10.7639))
        / NULLIF(bm.median_eui_kbtu_sqft, 0),
        2
    )                                         AS eui_ratio
FROM actual    ac
JOIN benchmark bm
  ON  ac.building_type = bm.building_type
  AND ac.climate_zone  = bm.climate_zone
  AND ac.vintage       = bm.vintage
  AND ac.state         = bm.state;
```

### Reading the Result

- `eui_ratio < 1.0` — building uses less energy than its ComStock benchmark cohort (better than median).
- `eui_ratio > 1.0` — building uses more energy than its benchmark cohort (candidate for efficiency intervention).

## What This Is Not

- This is **not** part of the core ODS-E schema. The core schema defines `building` fields; this document shows one way to use them.
- ComStock/ResStock data is published by NREL under its own license. Partners are responsible for complying with NREL data terms.
- The JOIN keys above are illustrative. Real-world matching may require fuzzy matching on vintage ranges or building-type synonyms.

## Data Sources

- ComStock datasets: https://data.openei.org/submissions/4520
- ResStock datasets: https://data.openei.org/submissions/4520
- NREL End Use Load Profiles: https://www.nrel.gov/buildings/end-use-load-profiles.html

# ODS-E Colab Kit

Self-contained demo notebooks for Google Colab — kit datasets are served from this
directory over GitHub raw URLs and the `odse` runtime comes from PyPI, so nothing
needs to be cloned.

| Demo | Story |
|---|---|
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/sibaya_colab_demo.ipynb) **Sibaya Distribution-Grid Demo** | Transform → validate → fault-classify → energy balance on real Durban site data |
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/winter_storm_fern_colab_demo.ipynb) **Winter Storm Fern Demo** | Storm blackout → validate → NREL ResStock join → neighborhood vulnerability map |

---

## Sibaya Distribution-Grid Demo

Run a real-world ODS-E workflow — transform → validate → fault-classify → energy balance —
in Google Colab with nothing but `pip install odse`.

### Contents

| File | Description |
|---|---|
| `sibaya_colab_demo.ipynb` | Self-contained demo notebook (runs in Colab via `odse` from PyPI) |
| `data/sibaya_telemetry_6mo.csv.gz` | 5-min inverter telemetry × 7 Huawei inverters, Mar–Sep 2026 (372k rows, gzip) |
| `data/durban_weather_6mo.csv.gz` | Hourly Durban weather, same window |
| `data/sibaya_meter_6mo.json` | IEC 62056 (OBIS) billing-meter daily registers, meter 10253148 |
| `data/root_cause_summary.csv` | Site fault root-cause rollup |
| `data/cost_impact_by_inverter.csv` | ZAR cost impact per inverter |
| `data/energy_balance.csv` | Daily generation vs grid purchases |
| `data/performance_ratio_daily.csv` | Daily PR |
| `data/sibaya-consumption-monthly-agg.csv` | Monthly consumption aggregates |
| `data/Tariff*.csv`, `data/Net Billing Rates.csv` | Eskom-style tariff rates |

The notebook fetches datasets from this directory over GitHub raw URLs — no clone needed.

### Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install odse pandas matplotlib
  jupyter lab colab/sibaya_colab_demo.ipynb
  ```

### Provenance

Data derived from the Sibaya C&I site study ("Sibaya faults on a distribution grid"),
the driving consumer of ODSE SEPs 049–052: per-phase electrical fields, canonical
vocabulary, Huawei electrical-KPI ingest, and the IEC 62056 meter transform.

---

## Winter Storm Fern Demo

Reproduces the [ODS-E blog analysis](https://opendataschema.energy/articles/winter-storm-fern-solar-whiteout-demand-forecasting.html):
when Winter Storm Fern blacks out a 5 MW solar farm (fictional Bayou Solar Farm, Harris County TX),
which neighborhoods see the biggest demand swing? ODS-E-normalized SMA production data is joined to
**NREL ResStock** building-stock simulations and Census TIGER 2020 PUMA boundaries to map storm demand
vulnerability by neighborhood.

Pipeline: **transform → validate → storm impact → ResStock join → vulnerability map.**

### Contents

| File | Description |
|---|---|
| `winter_storm_fern_colab_demo.ipynb` | Self-contained demo notebook (runs in Colab via `odse` from PyPI) |
| `data/bayou_solar_farm_sma_export.csv.gz` | 5-min SMA Sunny Portal export, Jan 20–29 2026 (incl. storm window), gzip |
| *(downloaded in-notebook)* [NREL ResStock 2024 R2](https://data.openei.org/submissions/4520) | TX residential baseline, ~130 MB from OEDI S3 — free, no credentials |
| *(downloaded in-notebook)* Census TIGER 2020 PUMA shapefile | TX PUMA boundaries, ~5 MB |

### Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install odse pandas matplotlib geopandas requests
  jupyter lab colab/winter_storm_fern_colab_demo.ipynb
  ```

### Provenance

Solar data synthesized for the blog narrative (SMA Sunny Portal export shape). Building data is
NREL ResStock 2024 R2 (TX baseline) from the OEDI data lake; boundaries are Census TIGER 2020.
The transform maps the raw export onto `energy-timeseries` fields that became canonical in
ODS-E 0.11.0 — `kW` and `frequency` (SEP-049), plus `asset_id` (SEP-052) — and the whole batch
is validated through the `odse` runtime (`validate_batch`, strict SEP-049 vocabulary).
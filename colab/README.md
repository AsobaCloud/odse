# ODS-E Colab Kit

Self-contained demo notebooks for Google Colab — kit datasets are served from this
directory over GitHub raw URLs and the `odse` runtime comes from PyPI, so nothing
needs to be cloned.

| Demo | Story |
|---|---|
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/mzansi_colab_demo.ipynb) **Mzansi Distribution-Grid Demo** | Transform → validate → fault-classify → energy balance on real Durban site data |
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/mzansi_erp_colab_demo.ipynb) **Mzansi ERP Enrichment Demo** | 7 ERP schemas → equipment register → PR underperformance triage → financial impact |
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/mzansi_forecasting_colab_demo.ipynb) **Mzansi Solar Forecasting Demo** | Energy balance → ODS-E timeseries → SARIMAX 30-day forecast → grid purchase planning |
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/winter_storm_fern_colab_demo.ipynb) **Winter Storm Fern Demo** | Storm blackout → validate → NREL ResStock join → neighborhood vulnerability map |
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/durban_feeder_grid_colab_demo.ipynb) **Durban Feeder Grid Modeling Demo** | Multi-site 11 kV feeder → pvlib clear-sky physics → -1.66 MW backfeed detection → BESS dispatch & TOU arbitrage |
| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/thokoza_level2_detector_colab_demo.ipynb) **Thokoza Level 2 Detector Demo** | Physical residuals + BinaryDropout / Thermal / heuristic detectors on 1.2 MW logistics-park PV (SEP-053) |

---

## Mzansi Distribution-Grid Demo

Run a real-world ODS-E workflow — transform → validate → fault-classify → energy balance —
in Google Colab with nothing but `pip install odse`.

### Contents

| File | Description |
|---|---|
| `mzansi_colab_demo.ipynb` | Self-contained demo notebook (runs in Colab via `odse` from PyPI) |
| `data/mzansi_telemetry_6mo.csv.gz` | 5-min inverter telemetry × 7 Huawei inverters, Mar–Sep 2026 (372k rows, gzip) |
| `data/durban_weather_6mo.csv.gz` | Hourly Durban weather, same window |
| `data/mzansi_meter_6mo.json` | IEC 62056 (OBIS) billing-meter daily registers, meter 10253148 |
| `data/root_cause_summary.csv` | Site fault root-cause rollup |
| `data/cost_impact_by_inverter.csv` | ZAR cost impact per inverter |
| `data/energy_balance.csv` | Daily generation vs grid purchases |
| `data/performance_ratio_daily.csv` | Daily PR |
| `data/mzansi-consumption-monthly-agg.csv` | Monthly consumption aggregates |
| `data/Tariff*.csv`, `data/Net Billing Rates.csv` | Eskom-style tariff rates |

The notebook fetches datasets from this directory over GitHub raw URLs — no clone needed.

### Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install odse pandas matplotlib
  jupyter lab colab/mzansi_colab_demo.ipynb
  ```

### Provenance

Data derived from the Mzansi C&I site study ("Mzansi faults on a distribution grid"),
the driving consumer of ODSE SEPs 049–052: per-phase electrical fields, canonical
vocabulary, Huawei electrical-KPI ingest, and the IEC 62056 meter transform.

---

## Mzansi ERP Enrichment Demo

Demonstrates the 7 ODS-E ERP enrichment schemas in Google Colab using Mzansi textile manufacturing facility assets and real underperformance data.

### Contents

| File | Description |
|---|---|
| `mzansi_erp_colab_demo.ipynb` | Colab notebook walking through schema loading, equipment register, real PR fault triage, and cost impact |
| `data/performance_ratio_daily.csv` | Daily PR and shortfall per inverter |
| `data/cost_impact_by_inverter.csv` | ZAR cost impact per inverter |
| `data/root_cause_summary.csv` | Hardware (92.6%) vs Weather (7.4%) shortfall attribution |

### Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install odse pandas matplotlib requests
  jupyter lab colab/mzansi_erp_colab_demo.ipynb
  ```

---

## Mzansi Solar Forecasting Demo

Self-contained 30-day solar production forecasting and grid purchase planning using Mzansi energy balance data and SARIMAX time-series modeling.

### Contents

| File | Description |
|---|---|
| `mzansi_forecasting_colab_demo.ipynb` | Colab notebook covering energy balance exploration, ODS-E normalization, SARIMAX(1,1,1)(0,1,1,7) forecasting, and grid purchase savings |
| `data/energy_balance.csv` | Daily building consumption, solar generation, and grid purchases |
| `data/mzansi-consumption-monthly-agg.csv` | Multi-year monthly consumption context (2023–2026) |

### Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install odse pandas matplotlib statsmodels requests
  jupyter lab colab/mzansi_forecasting_colab_demo.ipynb
  ```

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

---

## Durban Feeder Grid Modeling Demo

Simulates multi-site power flows across an 11 kV municipal distribution feeder in Durban, KZN connecting 5.55 MWp of solar PV and 3.0 MW / 6.0 MWh of BESS capacity across three C&I facilities:
1. **Thokoza Logistics Park**: 1.2 MW Solar PV + 1.0 MW / 2.0 MWh BESS
2. **Khanyisa Manufacturing Hub**: 3.6 MW Solar PV + 2.0 MW / 4.0 MWh BESS
3. **Simunye Cold Storage**: 750 kW Solar PV (no storage)

Demonstrates how `odse.adapters.pvlib` standardizes multi-inverter telemetry into `pvlib`-compatible DataFrames, calculates Ineichen clear-sky POA irradiance physics baselines, identifies severe midday reverse power flow backfeed (-1.66 MW peak, 108.8 hours), coordinates BESS charging/discharging to cut reverse flow hours by 84.7%, audits Eskom Megaflex TOU arbitrage savings (R 1.1M in 6 months), and exports modeled telemetry back to canonical ODS-E JSON via `pvlib_to_odse()`.

### Contents

| File | Description |
|---|---|
| `durban_feeder_grid_colab_demo.ipynb` | Self-contained Colab notebook modeling distribution feeder load flow and BESS dispatch |
| `data/thokoza_telemetry_6mo.csv.gz` | 5-min inverter telemetry × 5 inverters (1.2 MW PV) |
| `data/thokoza_bess_6mo.csv.gz` | 5-min BESS operational telemetry (1.0 MW / 2.0 MWh LFP) |
| `data/thokoza_grid_load_6mo.csv.gz` | 5-min building load, solar gen, BESS power, net grid draw |
| `data/khanyisa_telemetry_6mo.csv.gz` | 5-min inverter telemetry × 13 inverters (3.6 MW PV) |
| `data/khanyisa_bess_6mo.csv.gz` | 5-min BESS operational telemetry (2.0 MW / 4.0 MWh LFP) |
| `data/khanyisa_grid_load_6mo.csv.gz` | 5-min building load, solar gen, BESS power, net grid draw |
| `data/simunye_telemetry_6mo.csv.gz` | 5-min inverter telemetry × 3 inverters (750 kW PV) |
| `data/simunye_grid_load_6mo.csv.gz` | 5-min building load, solar gen, net grid draw |

### Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install odse pandas matplotlib pvlib
  jupyter lab colab/durban_feeder_grid_colab_demo.ipynb
  ```

### Provenance

Synthesized from Durban industrial feeder SCADA baselines and solar irradiance conditions in KwaZulu-Natal. Validated against the `odse.validator.validate_batch` schema checker and roundtrip-tested with the `odse.adapters.pvlib` bi-directional adapter (`odse_to_pvlib` and `pvlib_to_odse`).

---

## Thokoza Level 2 Detector Demo (SEP-053)

Zero-GPU Level 2 physical residual detection on **Thokoza Logistics Park** (1.2 MW PV on the Durban 11 kV feeder — not the Mzansi textile site). Injects Faiman / $P_{expected}$ residuals via `odse.adapters.pvlib.inject_physical_residuals`, then runs `BinaryDropoutDetector`, `ThermalDivergenceDetector`, and `PhysicalHeuristicDetector`.

### Contents

| File | Description |
|---|---|
| `thokoza_level2_detector_colab_demo.ipynb` | Colab notebook for SEP-053 Level 2 detectors |
| `data/thokoza_telemetry_6mo.csv.gz` | 5-min inverter (+ BESS) telemetry |
| `data/durban_weather_6mo.csv.gz` | Hourly ambient for Faiman cell temperature |

### Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install "odse[detectors]>=0.12.0" matplotlib
  jupyter lab colab/thokoza_level2_detector_colab_demo.ipynb
  ```

# ODS-E Colab Kit — Sibaya Distribution-Grid Demo

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AsobaCloud/odse/blob/main/colab/sibaya_colab_demo.ipynb)

Run a real-world ODS-E workflow — transform → validate → fault-classify → energy balance —
in Google Colab with nothing but `pip install odse`.

## Contents

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
| `data/Tariff*.csv`, `Net Billing Rates.csv` | Eskom-style tariff rates |

The notebook fetches datasets from this directory over GitHub raw URLs — no clone needed.

## Usage

- **Colab:** click the badge above.
- **Local:**
  ```bash
  pip install odse pandas matplotlib
  jupyter lab colab/sibaya_colab_demo.ipynb
  ```

## Provenance

Data derived from the Sibaya C&I site study ("Sibaya faults on a distribution grid"),
the driving consumer of ODSE SEPs 049–052: per-phase electrical fields, canonical
vocabulary, Huawei electrical-KPI ingest, and the IEC 62056 meter transform.
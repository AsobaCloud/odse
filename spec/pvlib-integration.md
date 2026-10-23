# ODS-E to pvlib Interoperability Specification & Guide

## 1. Overview & Architectural Role

The `odse.adapters.pvlib` module bridges Open Data Schema for Energy (ODS-E) normalized telemetry payloads directly into `pvlib-python`-compliant structures. 

Downstream clients—including `@asobacloud/odse-mcp` (MCP server), `nehanda-cli`, and energy forecasting pipelines—delegate data conversion to this module to guarantee zero schema drift between raw SCADA / inverter ingest and scientific photovoltaic performance calculations.

The adapter conforms to `pvlib.iotools` conventions:
- **`odse_to_pvlib()`** returns a two-element tuple: `(data: pd.DataFrame, metadata: dict)`.
- **`pvlib_to_odse()`** exports simulated `pvlib` DataFrames back into standard ODS-E JSON dictionary payloads.

---

## 2. Canonical Field Mapping Matrix

The adapter maps between canonical ODS-E schema attributes and standard `pvlib` column names according to the following strict bidirectional matrix:

| ODS-E Canonical Key | Target `pvlib` Column Name | Unit / Type | Description |
|---|---|---|---|
| `kW` | `p_mp` | kW (float) | AC Active Power Output |
| `kWh` | `ac_energy` | kWh (float) | Cumulative AC Energy |
| `poa_irradiance` | `poa_global` | W/m² (float) | Plane-of-Array Irradiance |
| `ghi` | `ghi` | W/m² (float) | Global Horizontal Irradiance |
| `dni` | `dni` | W/m² (float) | Direct Normal Irradiance |
| `dhi` | `dhi` | W/m² (float) | Diffuse Horizontal Irradiance |
| `ambient_temperature_c` | `temp_air` | °C (float) | Ambient Temperature |
| `module_temperature_c` | `temp_cell` | °C (float) | Module / Cell Temperature |
| `wind_speed_ms` | `wind_speed` | m/s (float) | Wind Speed |
| `voltage_dc` | `v_dc` | V (float) | Array DC Voltage |
| `current_dc` | `i_dc` | A (float) | Array DC Current |

---

## 3. Installation & Dependency Guard

`pvlib` and `pandas` are declared as optional dependencies under the `pvlib` extra:

```bash
pip install "odse[pvlib]"
```

The core `odse` library remains lightweight and importable without scientific dependencies. If `odse.adapters.pvlib` is invoked when `pandas` is not installed, it raises an actionable `ImportError`:

```
ImportError: pandas is required for the ODS-E pvlib adapter. Install optional dependencies using: pip install 'odse[pvlib]'
```

---

## 4. Usage Examples

### 4.1 Python API

```python
from odse.adapters.pvlib import odse_to_pvlib, pvlib_to_odse
import pvlib

# 1. Ingest ODS-E JSON, JSONL, Path, or dict
df, meta = odse_to_pvlib("telemetry.json")

# 2. Run scientific calculation using pvlib
cell_temp = pvlib.temperature.pvsyst_cell(
    poa_global=df["poa_global"],
    temp_air=df["temp_air"],
    wind_speed=df.get("wind_speed", 1.0)
)
df["temp_cell"] = cell_temp

# 3. Export back to ODS-E JSON format
export_payload = pvlib_to_odse(df, site_id="solar-site-01", metadata=meta)
```

### 4.2 Physical residuals (SEP-053)

Deterministic Faiman / expected-power residuals live in `odse.physics` (pure NumPy/Pandas; **does not** call the `pvlib` package). They are re-exported from this adapter for the SEP SDK path:

```python
from odse.adapters.pvlib import inject_physical_residuals

df_enriched = inject_physical_residuals(
    df,
    rated_capacity_kw=330.0,
    temp_coeff=-0.0035,
)
# adds t_cell_expected, p_expected, delta_p_norm[, delta_t_divergence]
```

Level 2 detectors (`odse.detectors`) and the `odse detect` CLI consume these residuals. See [SEP-053.md](SEP-053.md).

### 4.3 CLI Command

The ODS-E CLI provides a top-level `to-pvlib` command (also aliased as `pvlib`):

```bash
# Convert JSON to CSV with standard pvlib column names
odse to-pvlib --input telemetry.json --output pvlib_data.csv --format csv

# Convert JSONL stream from stdin, purging invalid/fault records
cat telemetry.jsonl | odse to-pvlib --input - --drop-invalid > pvlib_clean.json

# Alternatively, run directly via module invocation
python -m odse.adapters.pvlib telemetry.json --output pvlib_data.csv --format csv
```

---

## 5. Comprehensive Edge Cases & Troubleshooting Guide

When integrating telemetry pipelines with `pvlib`, discrepancies in sensor logging, OEM nomenclature, and time formatting can lead to subtle bugs. The following guide details every known edge case, its root cause, and how to troubleshoot it.

### Edge Case 1: Missing `p_mp` in pvlib Models (Energy vs. Instantaneous Power)
* **Symptom:** Downstream `pvlib.ModelChain` or inverter models fail with `KeyError: 'p_mp'`.
* **Root Cause:**
  - Many SCADA loggers and utility meters record 5-minute or 15-minute interval cumulative energy (`kWh`), but do not log instantaneous AC active power (`kW`).
  - ODS-E canonical specification strictly maps `kWh` $\rightarrow$ `ac_energy` and `kW` $\rightarrow$ `p_mp`.
  - The adapter does not guess or invent data: if `kW` is not in the source record, `p_mp` will not exist in the DataFrame.
* **Troubleshooting & Fix:**
  - If your inverter logger only outputs `kWh`, calculate active power prior to conversion:
    $$\text{active\_power\_kW} = \frac{\text{kWh}}{\text{interval\_hours}}$$
    *(e.g., for 5-minute data: `kW = kWh * 12.0`)*.
  - Ensure the key `kW` is added to your ODS-E payload before calling `odse_to_pvlib()`.

### Edge Case 2: OEM Casing & Non-Standard Key Passthrough
* **Symptom:** Columns like `active_power_kw` (lowercase `w`) or `active_power` (in Watts) remain unchanged in the DataFrame and do not become `p_mp`.
* **Root Cause:**
  - ODS-E canonical fields use explicit camelCase unit suffixes (`kW`, `voltage_dc`, `current_dc`).
  - To prevent accidental data loss, `odse_to_pvlib` preserves all unmapped or custom columns (passthrough behavior) without raising an error.
* **Troubleshooting & Fix:**
  - Check your transform configuration (`transforms/*.yaml`). Ensure the target field is named `kW`.
  - Check `df.columns`: if you see `active_power_kw` or `active_power`, your upstream transform has not yet normalized the key to canonical ODS-E.

### Edge Case 3: Plane-of-Array (`poa_irradiance`) vs. Horizontal Irradiance (`ghi`)
* **Symptom:** A pvlib function expecting `poa_global` fails because only `ghi` exists, or vice-versa.
* **Root Cause:**
  - Weather stations on solar farms vary: rooftop systems typically only have Global Horizontal Irradiance (`ghi`), while utility-scale plants with tilted pyranometers record Plane-of-Array (`poa_irradiance`).
  - The adapter maps `poa_irradiance` $\rightarrow$ `poa_global`, and `ghi` $\rightarrow$ `ghi`.
* **Troubleshooting & Fix:**
  - If only `ghi` is present in your site data, use pvlib's transposition functions (`pvlib.irradiance.get_total_irradiance`) to calculate `poa_global` using site tilt, azimuth, and solar position before passing to temperature or PR models.

### Edge Case 4: Timezone Normalization and Offsets
* **Symptom:** Solar elevation calculations are out of sync (e.g., peak solar noon occurring at midnight).
* **Root Cause:**
  - OEM CSV exports often mix timestamp representations (e.g., local time strings without offsets, or inconsistent `+02:00` offsets).
* **Adapter Behavior:**
  - `odse_to_pvlib()` enforces UTC. Any ISO timestamp with an offset (`+02:00`, `-05:00`, `Z`) is parsed to UTC and indexed as a sorted `pd.DatetimeIndex`.
  - If input timestamps lack timezone information, pandas defaults to UTC.
* **Troubleshooting & Fix:**
  - Verify that your input timestamps contain valid ISO-8601 offset notation (e.g. `2026-06-01T14:00:00+02:00` or `2026-06-01T12:00:00Z`).
  - When exporting back with `pvlib_to_odse()`, all timestamps are guaranteed to be serialized in canonical UTC ISO format: `YYYY-MM-DDTHH:MM:SSZ`.

### Edge Case 5: Missing Mandatory `timestamp`
* **Symptom:** Function raises `KeyError: "ODS-E telemetry record is missing the mandatory 'timestamp' field."`
* **Root Cause:**
  - A row or batch in the telemetry payload has an empty or missing `timestamp` key.
* **Troubleshooting & Fix:**
  - Every ODS-E telemetry record must have a valid `timestamp`. Use `odse validate --input <file>` to identify malformed records in the file.

### Edge Case 6: Handling `NaN` and Nighttime Gaps
* **Symptom:** JSON export fails or generates non-standard `NaN` values.
* **Root Cause:**
  - Photovoltaic datasets naturally contain `NaN` during nighttime hours for irradiance and active power. In standard JSON, `NaN` is not a valid literal.
* **Adapter Behavior:**
  - `pvlib_to_odse()` sanitizes all `NaN` values to `None` (which serializes cleanly to standard JSON `null`).
* **Troubleshooting & Fix:**
  - If downstream consumers cannot handle `null` values, fill missing intervals using `df.fillna(0.0)` or `df.interpolate()` before calling `pvlib_to_odse()`.

### Edge Case 7: Unnamed DatetimeIndex in Custom DataFrames
* **Symptom:** Standard conversion scripts fail with `KeyError: 'timestamp'` when calling `reset_index()`.
* **Root Cause:**
  - DataFrames constructed via `pd.date_range()` often have `df.index.name = None`. Resetting the index produces a column named `"index"`, not `"timestamp"`.
* **Adapter Behavior:**
  - `pvlib_to_odse()` explicitly handles unnamed and custom-named indexes, ensuring the exported ODS-E telemetry list always contains the canonical `"timestamp"` key.

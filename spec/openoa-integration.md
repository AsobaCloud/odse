# ODS-E to OpenOA Interoperability Specification & Guide

## 1. Overview & Architectural Role

The `odse.adapters.openoa` module bridges Open Data Schema for Energy (ODS-E) normalized telemetry and operational payloads directly into NREL's OpenOA (Open Operational Assessment) scientific library structures.

Downstream clients—including `@asobacloud/odse-mcp` (MCP server), `nehanda-cli`, automated wind yield assessment tools, and operational analytics pipelines—delegate data conversion to this module to guarantee zero schema drift between raw SCADA / wind turbine ingest and scientific wind turbine analysis (AEP estimation, wake loss modeling, yaw error evaluation, electrical losses).

The adapter conforms to OpenOA `PlantData` conventions:
- **`odse_to_openoa()`** accepts ODS-E payloads (file path, raw JSON string, or dict) and returns a structured dictionary containing DataFrames indexed by UTC timestamps (`scada`, `meter`, `tower`, `curtail` if available) and metadata. If `openoa` is installed and `return_plantdata=True`, it constructs an OpenOA `PlantData` object.
- **`openoa_to_odse()`** exports OpenOA DataFrames back into standard ODS-E JSON dictionary payloads with UTC ISO-8601 formatting and sanitized `null` values.

---

## 2. Canonical Field Mapping Matrix

OpenOA organizes wind plant datasets into distinct tables: `scada` (turbine-level high-frequency SCADA), `tower` (meteorological mast telemetry), and `meter` (revenue meter active power/energy).

### 2.1 SCADA Table Mapping

| ODS-E Canonical Key | OpenOA SCADA Column Name | Unit / Type | Description |
|---|---|---|---|
| `timestamp` | `time` / DatetimeIndex | UTC datetime | Telemetry timestamp (UTC) |
| `asset_id` | `asset_id` | string | Turbine identifier (e.g. `WTG01`) |
| `active_power_kW` | `WMET_HorWdSpd` (or active power) / `wtg_power` | kW (float) | Turbine Active Power |
| `wind_speed_ms` | `WMET_HorWdSpd` / `wtg_windspeed` | m/s (float) | Nacelle Wind Speed |
| `wind_direction_deg` | `WMET_HorWdDir` / `wtg_winddirection` | degrees (float) | Wind Direction |
| `pitch_angle_deg` | `pitch_angle` | degrees (float) | Blade Pitch Angle |
| `generator_rpm` | `generator_rpm` | RPM (float) | Generator Rotational Speed |
| `rotor_rpm` | `rotor_rpm` | RPM (float) | Rotor Rotational Speed |
| `ambient_temperature_c` | `temp_air` | °C (float) | Ambient Temperature |
| `nacelle_position_deg` | `nacelle_position` | degrees (float) | Nacelle Yaw Orientation |

### 2.2 Tower (Met Mast) Table Mapping

| ODS-E Canonical Key | OpenOA Tower Column Name | Unit / Type | Description |
|---|---|---|---|
| `timestamp` | `time` / DatetimeIndex | UTC datetime | Measurement timestamp (UTC) |
| `wind_speed_ms` | `WMET_HorWdSpd` | m/s (float) | Met Mast Wind Speed |
| `wind_direction_deg` | `WMET_HorWdDir` | degrees (float) | Met Mast Wind Direction |
| `ambient_temperature_c` | `temp_air` | °C (float) | Air Temperature |
| `surface_pressure_pa` | `pressure` | Pa (float) | Atmospheric Pressure |

### 2.3 Meter (Revenue / Grid Meter) Table Mapping

| ODS-E Canonical Key | OpenOA Meter Column Name | Unit / Type | Description |
|---|---|---|---|
| `timestamp` | `time` / DatetimeIndex | UTC datetime | Timestamp (UTC) |
| `active_power_kW` | `net_power` | kW (float) | Net Grid Active Power |
| `kWh` | `ac_energy` | kWh (float) | Cumulative Meter Energy |

---

## 3. Installation & Dependency Guard

`openoa` and `pandas` are declared as optional dependencies under the `openoa` extra:

```bash
pip install "odse[openoa]"
```

The core `odse` library remains lightweight and importable without scientific dependencies. If `odse.adapters.openoa` is invoked when `pandas` is not installed, it raises an actionable `ImportError`:

```
ImportError: pandas is required for the ODS-E OpenOA adapter. Install optional dependencies using: pip install 'odse[openoa]'
```

> [!NOTE]
> OpenOA v3.0+ on PyPI specifies Python compatibility `<3.14`. In Python 3.14+ environments, `odse.adapters.openoa` continues to function seamlessly by outputting structured DataFrames directly, or leveraging OpenOA 2.x (`operational_analysis`).

---

## 4. Usage Examples

### 4.1 Python API

```python
from odse.adapters.openoa import odse_to_openoa, openoa_to_odse

# Ingest ODS-E JSON file, string, or dict
result = odse_to_openoa("wind_telemetry.json", table_type="scada", return_plantdata=False)
df_scada = result["scada"]
metadata = result["metadata"]

# Multi-table assembly from dict of payloads
plant_data = odse_to_openoa(
    {"scada": scada_payload, "tower": met_payload},
    return_plantdata=False
)

# Export back to ODS-E JSON structure
odse_payload = openoa_to_odse(df_scada, asset_id="WTG01")
```

### 4.2 CLI Invocation

```bash
# Convert ODS-E file to OpenOA JSON/table
odse to-openoa telemetry.json --table scada --output openoa_scada.json

# Using alias
odse openoa telemetry.json --table scada --output openoa_scada.json
```

---

## 5. Exhaustive Edge Cases & Troubleshooting Guide

When bridging ODS-E telemetry into OpenOA, operational engineers and automated pipelines encounter physical and schema variations. This section details every edge case and its resolution:

### Edge Case 1: Inverter / Turbine OEM Power Casing & Custom Naming
* **Symptom:** Columns such as `active_power_kw` (lowercase `w`), `Power_kW`, or `active_power` (in Watts) remain unchanged in the DataFrame and are not recognized by OpenOA's analysis routines.
* **Root Cause:**
  - ODS-E canonical specification strictly requires camelCase unit suffixes: `active_power_kW`, `wind_speed_ms`, `pitch_angle_deg`.
  - To prevent data destruction, `odse_to_openoa()` operates on passthrough principles: unmapped columns are preserved without throwing errors.
* **Troubleshooting & Fix:**
  - Ensure upstream transform configurations (`transforms/*.yaml`) normalize OEM tags to canonical ODS-E keys (`active_power_kW`, `wind_speed_ms`).
  - Run `odse validate --input <file>` before adapter ingestion.

### Edge Case 2: Multi-Turbine `asset_id` Partitioning
* **Symptom:** In SCADA datasets containing multiple wind turbines, OpenOA analysis scripts report duplicate timestamps or invalid index structure.
* **Root Cause:**
  - OpenOA expects either a composite index `(time, asset_id)` or an explicit `asset_id` column partitioned across turbine instances.
* **Adapter Behavior:**
  - `odse_to_openoa()` checks for `asset_id`. If present in the telemetry records, it is preserved in the DataFrame column for OpenOA turbine-level grouping.
* **Troubleshooting & Fix:**
  - Always include `asset_id` (e.g. `"WTG01"`, `"WTG02"`) in ODS-E telemetry records when aggregating wind farm payloads.
  - When converting back via `openoa_to_odse(df, asset_id="WTG01")`, supply the `asset_id` parameter if the DataFrame index does not retain it.

### Edge Case 3: Negative Power (Turbine Aux Consumption) vs. Curtailment
* **Symptom:** Inverters and turbines consume small amounts of power during calm or standstill periods (station service / heating), resulting in negative active power values (`active_power_kW < 0`), or zero power during grid curtailment events.
* **Root Cause:**
  - Standard physical sensor readings can record negative values (`-2.5 kW`). If an assessment pipeline assumes power $\ge 0$, calculations may raise mathematical or filtering errors.
* **Troubleshooting & Fix:**
  - Do not drop negative values blindly; negative power represents real auxiliary consumption.
  - For wind turbine power curve fitting, filter out negative power and curtailment flags in downstream OpenOA filters:
    ```python
    df_clean = df[df["active_power_kW"] >= 0]
    ```

### Edge Case 4: Anemometer Yaw Offset and Wind Direction Wrapping
* **Symptom:** Wind direction values jump from $359^\circ$ to $0^\circ$, causing gradient anomalies or yaw alignment errors in OpenOA.
* **Root Cause:**
  - Compass wind directions wrap at $360^\circ$. Some OEM loggers output $-180^\circ$ to $+180^\circ$, while ODS-E standardizes on $0^\circ$ to $360^\circ$.
* **Troubleshooting & Fix:**
  - Ensure upstream normalization calculates modulo $360^\circ$: `(wind_direction_deg % 360)`.
  - When interpreting nacelle position relative to wind direction (yaw error), compute angular difference using circular subtraction:
    $$\text{yaw\_error} = (\text{wind\_dir} - \text{nacelle\_pos} + 180) \pmod{360} - 180$$

### Edge Case 5: Timezone Normalization and Offsets
* **Symptom:** Diurnal wind patterns (e.g. night-time thermal winds) are shifted by several hours in OpenOA assessments.
* **Root Cause:**
  - OEM SCADA files frequently record local plant time without ISO-8601 offset strings (e.g. `2026-06-01 12:00:00` instead of `2026-06-01T12:00:00+02:00`).
* **Adapter Behavior:**
  - `odse_to_openoa()` strictly enforces UTC. Parsed timestamps are converted to UTC and indexed as a sorted `pd.DatetimeIndex`.
  - Missing timezones default to UTC.
* **Troubleshooting & Fix:**
  - Provide ISO-8601 timestamps with explicit UTC offsets (`+02:00` or `Z`).
  - `openoa_to_odse()` serializes all timestamps back into standard UTC ISO format: `YYYY-MM-DDTHH:MM:SSZ`.

### Edge Case 6: Missing Mandatory `timestamp`
* **Symptom:** Adapter raises `KeyError: "ODS-E telemetry record is missing the mandatory 'timestamp' field."`
* **Root Cause:**
  - A row or batch in the telemetry payload has an empty, null, or absent `timestamp` key.
* **Troubleshooting & Fix:**
  - Every ODS-E telemetry record must possess a valid `timestamp`. Use `odse validate --input <file>` to verify payload compliance.

### Edge Case 7: Non-Standard `NaN` Values in JSON Output
* **Symptom:** JSON export fails or outputs non-standard `NaN` / `Infinity` literals rejected by strict JSON parsers.
* **Root Cause:**
  - SCADA sensors frequently experience communication dropouts or periods of standstill, generating `NaN` values in pandas DataFrames.
* **Adapter Behavior:**
  - `openoa_to_odse()` replaces all `NaN` values with `None`, serializing cleanly to standard JSON `null`.
* **Troubleshooting & Fix:**
  - Downstream consumers can rely on `null` in JSON output. If non-null values are required, apply interpolation (`df.interpolate()`) before exporting.

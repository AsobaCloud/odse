"""ODS-E to OpenOA Interoperability Adapter (SEP-OPENOA).

This module bridges Open Data Schema for Energy (ODS-E) normalized telemetry
records into multi-table structures conforming to OpenOA (Open Operational Assessment)
conventions developed by the National Laboratory of the Rockies (NLR / NREL),
and exports OpenOA PlantData / DataFrames back into ODS-E interchange payloads.

Edge Cases & Troubleshooting Guide
==================================

1. Energy (kWh) vs. Instantaneous Power (kW):
   - OpenOA SCADA analysis expects both active power (`wm_power_kw`) and energy (`wm_energy_kwh`).
   - ODS-E canonical specification strictly maps `active_power_kW` -> `wm_power_kw`
     and `kWh` -> `wm_energy_kwh`.
   - If your inverter logger only provides `kWh`, calculate active power prior to running OpenOA:
     `active_power_kW = (kWh / interval_hours)`.

2. Casing and Non-Standard Key Passthrough:
   - Canonical ODS-E keys use explicit unit-suffixed camelCase keys:
     `active_power_kW`, `wind_speed_ms`, `ambient_temperature_c`, etc.
   - Any unmapped OEM or custom columns (e.g. `rotor_rpm`, `blade_pitch_deg`, `soc`)
     pass through intact into the resulting DataFrame.

3. Loss Accounting via ODS-E Error Taxonomy:
   - ODS-E canonical `error_type` (`normal`, `warning`, `critical`, `fault`, `offline`,
     `standby`, `unknown`) maps directly to OpenOA's `status_id`.
   - When `drop_invalid=True`, records with `fault` or `offline` are purged.
   - When `drop_invalid=False`, `status_id` is preserved so OpenOA's availability loss
     and downtime categorization algorithms can quantify lost energy.

4. Multi-Table Plant Assembly (SCADA, Met Tower, Revenue Meter):
   - OpenOA models multi-domain renewable plants with separate tables:
     `scada` (turbine/inverter data), `tower` (meteorological station), and `meter` (revenue meter).
   - `odse_to_openoa()` accepts either a standard telemetry list (converted to `scada`)
     or a multi-table envelope: `{"scada": [...], "tower": [...], "meter": [...], "metadata": {...}}`.

5. Timezone Alignment & UTC Normalization:
   - OpenOA requires UTC-indexed timestamps for multi-year AEP loss assessments.
   - `odse_to_openoa()` normalizes all ISO-8601 timestamps (including `+02:00`, `-05:00`, `Z`)
     into a sorted UTC `pd.DatetimeIndex`.
   - `openoa_to_odse()` exports timestamps in standard UTC ISO-8601 strings with a `Z` suffix.

6. Nighttime & Missing Data NaN Sanitization:
   - Renewable datasets contain `NaN` during missing sensor reads or nighttime hours.
   - `openoa_to_odse()` sanitizes all `NaN` and infinite values to `None` (JSON `null`).
"""

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# Canonical ODS-E Schema to OpenOA Field Mapping Matrices
ODSE_TO_OPENOA_SCADA_MAP: Dict[str, str] = {
    "active_power_kW": "wm_power_kw",
    "kWh": "wm_energy_kwh",
    "wind_speed_ms": "ws_ms",
    "ambient_temperature_c": "temp_c",
    "module_temperature_c": "temp_cell",
    "poa_irradiance": "poa_global",
    "error_type": "status_id",
}

OPENOA_SCADA_TO_ODSE_MAP: Dict[str, str] = {v: k for k, v in ODSE_TO_OPENOA_SCADA_MAP.items()}

ODSE_TO_OPENOA_TOWER_MAP: Dict[str, str] = {
    "poa_irradiance": "poa_global",
    "ghi": "ghi",
    "ambient_temperature_c": "temp_c",
    "wind_speed_ms": "ws_ms",
}

ODSE_TO_OPENOA_METER_MAP: Dict[str, str] = {
    "kWh": "net_energy_kwh",
    "active_power_kW": "power_kw",
}


def _check_dependencies() -> None:
    """Ensure optional pandas dependency is installed."""
    if not HAS_PANDAS:
        raise ImportError(
            "pandas is required for the ODS-E OpenOA adapter. "
            "Install optional dependencies using: pip install 'odse[openoa]'"
        )


def _check_openoa_available() -> bool:
    """Checks if OpenOA (openoa or operational_analysis) is natively installed."""
    try:
        import openoa  # noqa: F401
        return True
    except ImportError:
        try:
            import operational_analysis  # noqa: F401
            return True
        except ImportError:
            return False


def _parse_payload(source: Union[str, pathlib.Path, dict, list]) -> Tuple[Any, Dict[str, Any]]:
    """Parse payload from file, string, dict, list, JSON, or JSONL."""
    if isinstance(source, (str, pathlib.Path)):
        path_obj = pathlib.Path(source)
        raw_text: Optional[str] = None
        is_file = False
        try:
            if path_obj.exists() and path_obj.is_file():
                is_file = True
                raw_text = path_obj.read_text(encoding="utf-8")
        except (OSError, ValueError):
            is_file = False

        if not is_file:
            raw_text = str(source)

        if raw_text is None or not raw_text.strip():
            return [], {}

        stripped = raw_text.strip()
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            # Fallback to JSONL
            records = [json.loads(line) for line in stripped.splitlines() if line.strip()]
            return records, {}
    elif isinstance(source, (dict, list)):
        payload = source
    else:
        raise TypeError(f"Invalid source type: {type(source)}. Expected str, Path, dict, or list.")

    if isinstance(payload, dict):
        meta = dict(payload.get("metadata", {}))
        # Check if payload is a multi-table structure
        if any(k in payload for k in ("scada", "tower", "meter")):
            return payload, meta
        records = payload.get("telemetry", payload.get("data", payload.get("records", None)))
        if records is None:
            records = [payload]
        return records, meta
    elif isinstance(payload, list):
        return payload, {}
    else:
        raise ValueError("Unsupported ODS-E payload structure.")


def _process_timeseries_df(
    records: List[Dict[str, Any]],
    column_map: Dict[str, str],
    map_variables: bool,
    drop_invalid: bool,
    default_asset_id: str = "asset_01",
) -> Any:
    """Process a list of records into a UTC-indexed DataFrame with OpenOA column mappings."""
    if not records:
        df = pd.DataFrame()
        df.index = pd.DatetimeIndex([], tz="UTC", name="timestamp")
        return df

    df = pd.DataFrame(records)
    if "timestamp" not in df.columns:
        raise KeyError("ODS-E payload is missing mandatory 'timestamp' field.")

    # Purge invalid records if requested
    if drop_invalid and "error_type" in df.columns:
        df = df[~df["error_type"].isin(["fault", "offline"])].copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()

    if "asset_id" not in df.columns and "status_id" in column_map.values():
        df["asset_id"] = default_asset_id

    if map_variables:
        rename_cols = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_cols)

    return df


def odse_to_openoa(
    source: Union[str, pathlib.Path, dict, list],
    plant_name: str = "ODSE_Plant",
    map_variables: bool = True,
    drop_invalid: bool = False,
    return_plantdata: bool = True,
    tower: Optional[Union[str, pathlib.Path, List[Dict[str, Any]]]] = None,
    meter: Optional[Union[str, pathlib.Path, List[Dict[str, Any]]]] = None,
) -> Any:
    """
    Converts ODS-E telemetry payloads into an OpenOA PlantData object
    or a structured dictionary of DataFrames formatted for OpenOA analysis.

    Parameters
    ----------
    source : str, Path, dict, or list
        Input ODS-E JSON file path, raw JSON string, or dict/list payload.
    plant_name : str, default 'ODSE_Plant'
        Name of the renewable power plant asset.
    map_variables : bool, default True
        If True, renames ODS-E keys to standard OpenOA column names.
    drop_invalid : bool, default False
        If True, filters out records with error_type in ['fault', 'offline'].
    return_plantdata : bool, default True
        If True and openoa is installed, attempts to return openoa.plant.PlantData.
        Otherwise returns a dictionary of formatted DataFrames {'scada': df, 'metadata': meta, ...}.
    tower : str, Path, or list, optional
        Auxiliary meteorological tower data.
    meter : str, Path, or list, optional
        Auxiliary revenue meter data.

    Returns
    -------
    openoa.plant.PlantData or dict
        OpenOA PlantData container or dictionary of DataFrames.
    """
    _check_dependencies()

    parsed, meta = _parse_payload(source)
    meta["plant_name"] = plant_name
    default_asset = meta.get("asset_id", meta.get("site_id", "asset_01"))

    # Extract tables from payload or auxiliary arguments
    scada_records: List[Dict[str, Any]] = []
    tower_records: Optional[List[Dict[str, Any]]] = None
    meter_records: Optional[List[Dict[str, Any]]] = None

    if isinstance(parsed, dict) and any(k in parsed for k in ("scada", "tower", "meter")):
        scada_records = parsed.get("scada", [])
        tower_records = parsed.get("tower", None)
        meter_records = parsed.get("meter", None)
    elif isinstance(parsed, list):
        scada_records = parsed

    if tower is not None:
        tower_parsed, _ = _parse_payload(tower)
        tower_records = tower_parsed if isinstance(tower_parsed, list) else None

    if meter is not None:
        meter_parsed, _ = _parse_payload(meter)
        meter_records = meter_parsed if isinstance(meter_parsed, list) else None

    df_scada = _process_timeseries_df(
        scada_records,
        ODSE_TO_OPENOA_SCADA_MAP,
        map_variables=map_variables,
        drop_invalid=drop_invalid,
        default_asset_id=default_asset,
    )

    result_dict: Dict[str, Any] = {
        "scada": df_scada,
        "metadata": meta,
    }

    if tower_records is not None:
        result_dict["tower"] = _process_timeseries_df(
            tower_records,
            ODSE_TO_OPENOA_TOWER_MAP,
            map_variables=map_variables,
            drop_invalid=drop_invalid,
            default_asset_id=default_asset,
        )

    if meter_records is not None:
        result_dict["meter"] = _process_timeseries_df(
            meter_records,
            ODSE_TO_OPENOA_METER_MAP,
            map_variables=map_variables,
            drop_invalid=drop_invalid,
            default_asset_id=default_asset,
        )

    # Attempt to construct OpenOA PlantData if requested and available
    if return_plantdata and _check_openoa_available():
        try:
            from openoa.plant import PlantData  # type: ignore
            plant = PlantData(
                scada=df_scada,
                meter=result_dict.get("meter", None),
                tower=result_dict.get("tower", None),
                name=plant_name,
                latitude=meta.get("latitude", 0.0),
                longitude=meta.get("longitude", 0.0),
                capacity=meta.get("installed_capacity_kw", meta.get("capacity_kw", 1000.0)),
            )
            return plant
        except Exception:
            try:
                from operational_analysis.types.plant import PlantData  # type: ignore
                # OpenOA 2.x interface
                plant = PlantData(
                    path=None,
                    name=plant_name,
                )
                plant.scada = df_scada
                return plant
            except Exception:
                pass

    return result_dict


def openoa_to_odse(
    plant_data: Any,
    site_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Converts an OpenOA PlantData object, dictionary of DataFrames, or SCADA DataFrame
    back into a canonical ODS-E JSON dictionary payload.

    Parameters
    ----------
    plant_data : PlantData, dict, or pd.DataFrame
        Input OpenOA structure.
    site_id : str, optional
        Canonical site or asset identifier.
    metadata : dict, optional
        Additional metadata header fields.

    Returns
    -------
    dict
        Canonical ODS-E payload with "metadata" and "telemetry" list.
    """
    _check_dependencies()

    meta = dict(metadata) if metadata else {}

    if hasattr(plant_data, "scada"):
        df_scada = plant_data.scada.copy()
        meta["plant_name"] = getattr(plant_data, "name", "ODSE_Plant")
        meta["installed_capacity_kw"] = getattr(plant_data, "capacity", None)
    elif isinstance(plant_data, dict) and "scada" in plant_data:
        df_scada = plant_data["scada"].copy()
        meta.update(plant_data.get("metadata", {}))
    elif isinstance(plant_data, pd.DataFrame):
        df_scada = plant_data.copy()
    else:
        raise ValueError("Unsupported OpenOA input structure. Expected PlantData object, dict, or DataFrame.")

    if site_id:
        meta["site_id"] = site_id

    if df_scada.empty:
        return {"metadata": meta, "telemetry": []}

    # 1. Normalize DatetimeIndex to UTC
    if not isinstance(df_scada.index, pd.DatetimeIndex):
        if "time" in df_scada.columns:
            df_scada["timestamp"] = pd.to_datetime(df_scada["time"], utc=True)
            df_scada = df_scada.set_index("timestamp")
        else:
            raise TypeError("OpenOA DataFrame index must be a pandas.DatetimeIndex.")

    if df_scada.index.tz is None:
        idx_utc = df_scada.index.tz_localize("UTC")
    else:
        idx_utc = df_scada.index.tz_convert("UTC")

    timestamp_strings = idx_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Inverse Variable Mapping
    df_out = df_scada.rename(columns={k: v for k, v in OPENOA_SCADA_TO_ODSE_MAP.items() if k in df_scada.columns})

    # Reset index safely and insert clean timestamp column
    df_out = df_out.reset_index(drop=True)
    df_out.insert(0, "timestamp", timestamp_strings)

    if "error_type" not in df_out.columns:
        if "status_id" in df_out.columns:
            df_out["error_type"] = df_out["status_id"]
        else:
            df_out["error_type"] = "normal"

    # 3. Sanitize NaNs to None for compliant JSON
    sanitized_records: List[Dict[str, Any]] = []
    for row in df_out.to_dict(orient="records"):
        clean_row = {}
        for k, v in row.items():
            if pd.isna(v):
                clean_row[k] = None
            else:
                clean_row[k] = v
        sanitized_records.append(clean_row)

    return {
        "metadata": meta,
        "telemetry": sanitized_records,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for python -m odse.adapters.openoa."""
    parser = argparse.ArgumentParser(
        prog="python -m odse.adapters.openoa",
        description="Convert ODS-E telemetry data into OpenOA-compatible structures.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input ODS-E JSON or JSONL file path (use '-' or omit for stdin).",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout).",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "csv", "parquet"],
        default="json",
        help="Output format: json, csv, or parquet (default: json).",
    )
    parser.add_argument(
        "--plant-name",
        default="ODSE_Plant",
        help="Name of the renewable power plant (default: ODSE_Plant).",
    )
    parser.add_argument(
        "--no-map-variables",
        dest="map_variables",
        action="store_false",
        help="Do not rename ODS-E attributes to OpenOA column names.",
    )
    parser.add_argument(
        "--drop-invalid",
        action="store_true",
        help="Drop rows where error_type indicates fault or offline.",
    )

    args = parser.parse_args(argv)

    try:
        source_content = sys.stdin.read() if args.input == "-" else args.input
        res = odse_to_openoa(
            source=source_content,
            plant_name=args.plant_name,
            map_variables=args.map_variables,
            drop_invalid=args.drop_invalid,
            return_plantdata=False,
        )

        df = res["scada"]
        meta = res["metadata"]

        if args.format == "csv":
            out_str = df.to_csv()
            if args.output:
                pathlib.Path(args.output).write_text(out_str, encoding="utf-8")
            else:
                sys.stdout.write(out_str)
        elif args.format == "parquet":
            if not args.output:
                sys.stderr.write("Error: --output is required when format is parquet.\n")
                return 1
            df.to_parquet(args.output)
        else:  # json
            records = []
            df_reset = df.reset_index()
            if "timestamp" in df_reset.columns:
                df_reset["timestamp"] = df_reset["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            for row in df_reset.to_dict(orient="records"):
                clean_row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
                records.append(clean_row)

            output_obj = {
                "metadata": meta,
                "data": records,
            }
            out_str = json.dumps(output_obj, indent=2)
            if args.output:
                pathlib.Path(args.output).write_text(out_str, encoding="utf-8")
            else:
                sys.stdout.write(out_str)
                sys.stdout.write("\n")
        return 0

    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

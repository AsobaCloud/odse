"""ODS-E to pvlib Interoperability Adapter (SEP-PVLIB).

This module bridges Open Data Schema for Energy (ODS-E) normalized telemetry
records into pandas DataFrame structures conforming to `pvlib-python` conventions
(specifically aligning with `pvlib.iotools` two-tuple patterns: `(data, metadata)`),
and exports simulated pvlib DataFrames back into ODS-E interchange payloads.

Edge Cases & Troubleshooting Guide
==================================

1. Missing `p_mp` in pvlib models:
   - Schedulers or inverters may only export interval energy (`kWh`).
   - ODS-E maps `kWh` -> `ac_energy` and `active_power_kW` -> `p_mp`.
   - If your pvlib calculation (e.g. ModelChain) requires `p_mp` (instantaneous power),
     ensure your source transform emits `active_power_kW`. If only `kWh` is present,
     derive `active_power_kW = (kWh / interval_hours)` before passing to pvlib.

2. Casing and Non-Standard Key Passthrough:
   - Canonical ODS-E keys in this adapter are strictly camelCase/unit-specified:
     `active_power_kW`, `dc_voltage_v`, `dc_current_a`, `poa_irradiance`, etc.
   - Any unmapped OEM or legacy keys (e.g., `active_power_kw` with lowercase `w`
     or `active_power` in Watts) will NOT be renamed to `p_mp`. They are preserved
     as passthrough columns in the DataFrame.
   - Troubleshooting: If `p_mp` is absent in the resulting DataFrame, verify that your
     ODS-E input payload contains the exact key `active_power_kW`.

3. Timezone Alignment:
   - pvlib solar position and transposition algorithms require UTC DatetimeIndexes
     or accurate timezone awareness.
   - `odse_to_pvlib()` automatically normalizes all ISO-8601 timestamps (including
     positive/negative offsets like `+02:00` or `-05:00`) to UTC `pd.DatetimeIndex`
     and sorts them chronologically.
   - `pvlib_to_odse()` automatically converts any tz-aware DatetimeIndex to UTC
     before formatting as ISO-8601 strings with a `Z` suffix.

4. Empty Records & Missing Timestamp:
   - Input payloads missing the mandatory `"timestamp"` field raise a `KeyError`.
   - Empty input arrays return `(pd.DataFrame(), metadata)` without raising an exception.

5. Handling `NaN` and Null Values:
   - pvlib dataframes often contain `NaN` for missing sensor data (e.g., nighttime irradiance).
   - When converting back via `pvlib_to_odse()`, `NaN` values are sanitized to `None`
     (JSON `null`) to maintain JSON schema compliance.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# Canonical bidirectional variable mapping matrix
ODSE_TO_PVLIB_MAP: Dict[str, str] = {
    # Legacy input keys (SEP-050): accepted on input, deprecated;
    # canonical keys below win on round-trip output.
    "active_power_kW": "p_mp",
    "dc_voltage_v": "v_dc",
    "dc_current_a": "i_dc",
    # Canonical ODS-E keys (SEP-049)
    "kW": "p_mp",
    "kWh": "ac_energy",
    "poa_irradiance": "poa_global",
    "ghi": "ghi",
    "dni": "dni",
    "dhi": "dhi",
    "ambient_temperature_c": "temp_air",
    "module_temperature_c": "temp_cell",
    "wind_speed_ms": "wind_speed",
    "voltage_dc": "v_dc",
    "current_dc": "i_dc",
}

PVLIB_TO_ODSE_MAP: Dict[str, str] = {v: k for k, v in ODSE_TO_PVLIB_MAP.items()}


def _check_dependencies() -> None:
    """Ensure optional pandas dependency is installed."""
    if not HAS_PANDAS:
        raise ImportError(
            "pandas is required for the ODS-E pvlib adapter. "
            "Install optional dependencies using: pip install 'odse[pvlib]'"
        )


def _parse_payload(source: Union[str, Path, dict, list]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse an ODS-E payload from a filepath, JSON string, JSONL string, or Python structure.

    Returns:
        tuple of (records_list, metadata_dict)
    """
    if isinstance(source, (str, Path)):
        path_obj = Path(source)
        raw_text: Optional[str] = None

        # Check if source points to an existing file
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
        # Attempt standard JSON parse
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            # Fallback: attempt newline-delimited JSON (JSONL)
            records = []
            for line in stripped.splitlines():
                line = line.strip()
                if line:
                    records.append(json.loads(line))
            return records, {}

    elif isinstance(source, (dict, list)):
        payload = source
    else:
        raise TypeError(f"Invalid source type: {type(source)}. Expected str, Path, dict, or list.")

    # Extract metadata and telemetry array from payload
    if isinstance(payload, dict):
        meta = payload.get("metadata", {})
        records = payload.get("telemetry", payload.get("data", payload.get("records", None)))
        if records is None:
            # Single telemetry record payload
            records = [payload]
    elif isinstance(payload, list):
        meta = {}
        records = payload
    else:
        raise ValueError("Malformed ODS-E payload format. Expected dict or list.")

    return records, meta


def odse_to_pvlib(
    source: Union[str, Path, dict, list],
    map_variables: bool = True,
    drop_invalid: bool = False,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Converts an ODS-E JSON file, JSONL file, raw string, dictionary, or list into a
    pvlib-compliant pandas DataFrame and metadata dictionary.

    Parameters
    ----------
    source : str, Path, dict, or list
        File path to ODS-E JSON/JSONL, raw JSON string, or pre-parsed dictionary/list.
    map_variables : bool, default True
        Renames canonical ODS-E attributes to standard pvlib column names
        (e.g. 'poa_irradiance' -> 'poa_global', 'ambient_temperature_c' -> 'temp_air').
    drop_invalid : bool, default False
        If True, drops rows where 'error_type' is 'fault' or 'offline'.

    Returns
    -------
    data : pandas.DataFrame
        UTC DatetimeIndex-aligned DataFrame ready for pvlib.ModelChain, temperature models,
        or performance ratio (PR) calculations.
    meta : dict
        Extracted asset and site metadata header from the ODS-E payload.

    Raises
    ------
    ImportError
        If pandas is not installed.
    KeyError
        If telemetry records lack the mandatory 'timestamp' field.
    TypeError
        If source is not a str, Path, dict, or list.
    """
    _check_dependencies()

    records, meta = _parse_payload(source)
    if not records:
        return pd.DataFrame(), meta

    df = pd.DataFrame(records)

    if "timestamp" not in df.columns:
        raise KeyError("ODS-E telemetry record is missing the mandatory 'timestamp' field.")

    # 3. Construct DataFrame & Enforce UTC DatetimeIndex
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()

    # 4. Filter Invalid Records (Optional)
    if drop_invalid and "error_type" in df.columns:
        df = df[~df["error_type"].isin(["fault", "offline"])]

    # 5. Apply Variable Renaming Matrix
    if map_variables:
        rename_cols = {k: v for k, v in ODSE_TO_PVLIB_MAP.items() if k in df.columns}
        df = df.rename(columns=rename_cols)

    return df, meta


def pvlib_to_odse(
    df: Any,
    site_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Exports a pvlib pandas DataFrame into a standard ODS-E JSON dictionary payload.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with a DatetimeIndex and standard pvlib or custom columns.
    site_id : str
        Canonical site or asset identifier.
    metadata : dict, optional
        Additional asset/site metadata to include in the metadata header.

    Returns
    -------
    dict
        ODS-E payload with "metadata" and "telemetry" lists conforming to ODS-E schema.

    Raises
    ------
    ImportError
        If pandas is not installed.
    TypeError
        If df does not have a DatetimeIndex.
    """
    _check_dependencies()

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DataFrame index must be a DatetimeIndex.")

    meta = dict(metadata) if metadata else {}
    meta["site_id"] = site_id
    meta["schema_version"] = "ODS-E-1.0"

    # Enforce UTC DatetimeIndex
    if df.index.tz is None:
        utc_index = df.index.tz_localize("UTC")
    else:
        utc_index = df.index.tz_convert("UTC")

    df_out = df.copy()
    # Reset index cleanly without depending on df.index.name
    df_out = df_out.reset_index(drop=True)
    df_out.insert(0, "timestamp", utc_index.strftime("%Y-%m-%dT%H:%M:%SZ"))

    # Reverse column mapping
    rename_cols = {k: v for k, v in PVLIB_TO_ODSE_MAP.items() if k in df_out.columns}
    df_out = df_out.rename(columns=rename_cols)

    # Sanitize NaNs to None for valid JSON serialization
    records: List[Dict[str, Any]] = []
    for row in df_out.to_dict(orient="records"):
        clean_row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        records.append(clean_row)

    return {
        "metadata": meta,
        "telemetry": records,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for python -m odse.adapters.pvlib."""
    parser = argparse.ArgumentParser(
        prog="python -m odse.adapters.pvlib",
        description="Convert ODS-E SCADA data into pvlib-compatible structures.",
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
        "--no-map-variables",
        dest="map_variables",
        action="store_false",
        help="Do not rename ODS-E attributes to pvlib column names.",
    )
    parser.add_argument(
        "--drop-invalid",
        action="store_true",
        help="Drop rows where error_type indicates fault or offline.",
    )

    args = parser.parse_args(argv)

    try:
        if args.input == "-":
            source_content = sys.stdin.read()
        else:
            source_content = args.input

        df, meta = odse_to_pvlib(
            source=source_content,
            map_variables=args.map_variables,
            drop_invalid=args.drop_invalid,
        )

        if args.format == "csv":
            out_str = df.to_csv()
            if args.output:
                Path(args.output).write_text(out_str, encoding="utf-8")
            else:
                sys.stdout.write(out_str)
        elif args.format == "parquet":
            if not args.output:
                sys.stderr.write("Error: --output is required when format is parquet.\n")
                return 1
            df.to_parquet(args.output)
        else:  # json
            # Export as JSON dict with metadata and records
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
                Path(args.output).write_text(out_str, encoding="utf-8")
            else:
                sys.stdout.write(out_str)
                sys.stdout.write("\n")
        return 0

    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

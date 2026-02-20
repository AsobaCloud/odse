"""Serialization helpers for ODS-E records (SEP-016)."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def to_json(records: Iterable[Dict[str, Any]], output_path: str) -> None:
    """Write records as newline-delimited JSON (JSONL)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")))
            handle.write("\n")


def to_csv(records: Iterable[Dict[str, Any]], output_path: str) -> None:
    """Write records as CSV using ODS-E field names as headers."""
    rows = list(records)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def to_dataframe(records: Iterable[Dict[str, Any]]):
    """Return a pandas DataFrame with canonical ODS-E dtypes."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for to_dataframe(). Install with: pip install odse[dataframe]"
        ) from exc

    df = pd.DataFrame(list(records))
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if "kWh" in df.columns:
        df["kWh"] = df["kWh"].astype("float64")
    return df


def to_parquet(
    records: Iterable[Dict[str, Any]],
    output_path: str,
    partition_by: Optional[List[str]] = None,
    mode: str = "overwrite",
) -> None:
    """
    Write partitioned parquet files.

    If partition_by is set, one file is written per partition:
    <output_path>/<key>=<value>/part-00000.parquet
    """
    if mode not in {"overwrite", "append"}:
        raise ValueError("mode must be one of: overwrite, append")

    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for to_parquet(). Install with: pip install odse[parquet]"
        ) from exc

    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required for to_parquet(). Install with: pip install odse[parquet]"
        ) from exc

    rows = [_with_derived_partition_fields(dict(record)) for record in records]
    df = pd.DataFrame(rows)
    root = Path(output_path)
    root.mkdir(parents=True, exist_ok=True)

    partition_cols = partition_by or []
    for key in partition_cols:
        if key not in df.columns:
            df[key] = None

    if not partition_cols:
        file_path = root / "part-00000.parquet"
        if mode == "append" and file_path.exists():
            _append_parquet_file(df, file_path)
        else:
            df.to_parquet(file_path, engine="pyarrow", index=False)
        return

    grouped = df.groupby(partition_cols, dropna=False, sort=False)
    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        partition_parts = []
        for col_name, value in zip(partition_cols, keys):
            rendered = "null" if value is None else str(value)
            partition_parts.append(f"{col_name}={rendered}")
        partition_dir = root.joinpath(*partition_parts)
        partition_dir.mkdir(parents=True, exist_ok=True)
        file_path = partition_dir / "part-00000.parquet"
        if mode == "append" and file_path.exists():
            _append_parquet_file(group, file_path)
        else:
            group.to_parquet(file_path, engine="pyarrow", index=False)


def _append_parquet_file(df, file_path: Path) -> None:
    """Append by rewriting existing file with concatenated rows."""
    import pandas as pd

    existing = pd.read_parquet(file_path, engine="pyarrow")
    merged = pd.concat([existing, df], ignore_index=True)
    merged.to_parquet(file_path, engine="pyarrow", index=False)


def _with_derived_partition_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    ts = _parse_timestamp(record.get("timestamp"))
    if ts is None:
        return record
    record.setdefault("year", ts.year)
    record.setdefault("month", ts.month)
    record.setdefault("day", ts.day)
    record.setdefault("hour", ts.hour)
    return record


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

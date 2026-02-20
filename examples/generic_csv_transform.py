#!/usr/bin/env python3
"""Generic CSV mapping example: arbitrary CSV -> ODS-E -> validate -> parquet."""

from pathlib import Path
import sys

# Allow running from repo root without installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    from odse import to_parquet, to_json, transform, validate_batch

    fixtures = ROOT / "examples" / "fixtures"
    out_dir = ROOT / "examples" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Declare mapping from source CSV columns to ODS-E fields.
    mapping = {
        "timestamp": "Timestamp",
        "kWh": "Energy_kWh",
        "asset_id": "Asset",
    }

    # 2) Transform generic SCADA export into ODS-E records.
    input_csv = fixtures / "generic_scada.csv"
    records = transform(input_csv, source="csv", mapping=mapping)

    # 3) Validate all records in one call and print a batch summary.
    result = validate_batch(records)
    print(result.summary)

    # 4) Write JSONL regardless of optional dependencies.
    json_path = out_dir / "generic_transform.jsonl"
    to_json(records, str(json_path))

    # 5) Write parquet output when optional parquet deps are installed.
    parquet_root = out_dir / "generic_transform_parquet"
    try:
        to_parquet(records, str(parquet_root), partition_by=["asset_id", "year", "month", "day"])
        parquet_status = f"wrote parquet to {parquet_root}"
    except ImportError as exc:
        parquet_status = f"skipped parquet ({exc})"

    print(f"Records: {len(records)}")
    print(f"JSONL output: {json_path}")
    print(f"Parquet status: {parquet_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

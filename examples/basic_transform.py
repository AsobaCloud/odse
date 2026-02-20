#!/usr/bin/env python3
"""Basic OEM transform example: CSV -> ODS-E JSON + Parquet."""

from pathlib import Path
import sys

# Allow running from repo root without installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    from odse import to_json, to_parquet, transform

    fixtures = ROOT / "examples" / "fixtures"
    out_dir = ROOT / "examples" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load one synthetic Huawei fixture and transform it to ODS-E records.
    input_csv = fixtures / "huawei_sample.csv"
    records = transform(input_csv, source="huawei", asset_id="SITE-HW-001")

    # 2) Persist newline-delimited JSON for quick inspection.
    json_path = out_dir / "basic_transform.jsonl"
    to_json(records, str(json_path))

    # 3) Persist partitioned parquet when optional parquet deps are available.
    parquet_root = out_dir / "basic_transform_parquet"
    try:
        to_parquet(records, str(parquet_root), partition_by=["asset_id", "year", "month", "day"])
        parquet_status = f"wrote parquet to {parquet_root}"
    except ImportError as exc:
        parquet_status = f"skipped parquet ({exc})"

    print(f"Transformed records: {len(records)}")
    print(f"JSONL output: {json_path}")
    print(f"Parquet status: {parquet_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

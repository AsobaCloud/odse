#!/usr/bin/env python3
"""Batch directory example: process multiple OEM files into one partitioned output."""

from pathlib import Path
import sys

# Allow running from repo root without installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _source_for(path: Path) -> str:
    if "huawei" in path.name:
        return "huawei"
    if "solarman" in path.name:
        return "solarman"
    raise ValueError(f"No source mapping defined for file: {path.name}")


def _asset_for(path: Path) -> str:
    stem = path.stem
    return stem.replace("_", "-").upper()


def main() -> int:
    from odse import to_json, to_parquet, transform

    batch_dir = ROOT / "examples" / "fixtures" / "batch"
    out_dir = ROOT / "examples" / "output_batch"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Iterate a directory with multiple OEM fixture files.
    all_records = []
    for file_path in sorted(batch_dir.glob("*.csv")):
        source = _source_for(file_path)

        # 2) Transform each file with the correct source adapter.
        rows = transform(file_path, source=source, asset_id=_asset_for(file_path))
        all_records.extend(rows)

    # 3) Persist combined batch as JSONL for easy debugging.
    json_path = out_dir / "batch_directory.jsonl"
    to_json(all_records, str(json_path))

    # 4) Persist combined batch as partitioned parquet by asset/date if available.
    parquet_root = out_dir / "batch_parquet"
    try:
        to_parquet(all_records, str(parquet_root), partition_by=["asset_id", "year", "month", "day"])
        parquet_status = f"wrote parquet to {parquet_root}"
    except ImportError as exc:
        parquet_status = f"skipped parquet ({exc})"

    print(f"Input files: {len(list(batch_dir.glob('*.csv')))}")
    print(f"Output records: {len(all_records)}")
    print(f"JSONL output: {json_path}")
    print(f"Parquet status: {parquet_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

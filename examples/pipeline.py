#!/usr/bin/env python3
"""Pipeline example: transform -> enrich -> validate_batch -> parquet."""

from pathlib import Path
import sys

# Allow running from repo root without installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    from odse import enrich, to_parquet, to_json, transform, validate_batch

    fixtures = ROOT / "examples" / "fixtures"
    out_dir = ROOT / "examples" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Transform raw OEM telemetry into base ODS-E records.
    records = transform(fixtures / "huawei_sample.csv", source="huawei", asset_id="SITE-JBAY")

    # 2) Inject settlement context that downstream settlement logic expects.
    records = enrich(
        records,
        {
            "seller_party_id": "nersa:gen:JBAY-001",
            "buyer_party_id": "nersa:buy:CITY-001",
            "settlement_period_start": "2026-02-09T12:00:00Z",
            "settlement_period_end": "2026-02-09T12:30:00Z",
            "contract_reference": "PPA-001",
            "settlement_type": "bilateral",
        },
    )

    # 3) Validate the batch against the bilateral profile.
    validation = validate_batch(records, profile="bilateral")
    print(validation.summary)

    # 4) Persist JSONL for traceability.
    json_path = out_dir / "pipeline.jsonl"
    to_json(records, str(json_path))

    # 5) Persist partitioned parquet when optional deps are available.
    parquet_root = out_dir / "pipeline_parquet"
    try:
        to_parquet(records, str(parquet_root), partition_by=["asset_id", "year", "month", "day", "hour"])
        parquet_status = f"wrote parquet to {parquet_root}"
    except ImportError as exc:
        parquet_status = f"skipped parquet ({exc})"

    print(f"Records: {len(records)}")
    print(f"JSONL output: {json_path}")
    print(f"Parquet status: {parquet_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

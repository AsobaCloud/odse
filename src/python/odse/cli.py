"""ODS-E CLI entrypoint for transform and validate workflows (SEP-015)."""

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from . import __version__
from . import io as odse_io
from .transformer import transform
from .validator import validate


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="odse",
        description="ODS-E: Open Data Schema for Energy",
    )
    parser.add_argument(
        "--version", action="version", version=f"odse {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- transform ---
    p_transform = subparsers.add_parser(
        "transform",
        help="Transform OEM data to ODS-E format",
    )
    p_transform.add_argument(
        "--source",
        "-s",
        required=True,
        help="Data source (e.g., huawei, enphase, solaredge, generic_csv)",
    )
    p_transform.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input file path",
    )
    p_transform.add_argument(
        "--column-map",
        help="Inline mapping for generic_csv source (e.g. timestamp=Timestamp,kWh=Power)",
    )
    p_transform.add_argument("--asset-id", help="Asset identifier")
    p_transform.add_argument("--timezone", help="Timezone offset (e.g., +02:00)")
    p_transform.add_argument(
        "--interval-minutes",
        type=int,
        default=5,
        help="Interval in minutes for kW→kWh conversion (default: 5)",
    )
    p_transform.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
    )
    p_transform.add_argument(
        "--format",
        "-f",
        choices=["json", "csv", "parquet"],
        default="json",
        help="Output format (default: json)",
    )

    # --- validate ---
    p_validate = subparsers.add_parser(
        "validate",
        help="Validate ODS-E records",
    )
    p_validate.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input JSON file with ODS-E records",
    )
    p_validate.add_argument(
        "--level",
        "-l",
        default="schema",
        choices=["schema", "semantic"],
        help="Validation level (default: schema)",
    )
    p_validate.add_argument(
        "--profile", "-p",
        help="Conformance profile (e.g., bilateral, wheeling, sawem_brp, municipal_recon)",
    )
    p_validate.add_argument(
        "--capacity-kw", type=float,
        help="System capacity in kW (for semantic validation)",
    )
    p_validate.add_argument(
        "--latitude", type=float, help="Site latitude",
    )
    p_validate.add_argument(
        "--longitude", type=float, help="Site longitude",
    )

    p_version = subparsers.add_parser("version", help="Print ODS-E version")
    p_version.set_defaults(command="version")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "transform":
        _cmd_transform(args)
    elif args.command == "validate":
        _cmd_validate(args)
    elif args.command == "version":
        print(__version__)
        sys.exit(0)


def _cmd_transform(args):
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    kwargs: Dict[str, Any] = {}
    source = args.source
    if args.column_map:
        kwargs["column_map"] = _parse_column_map(args.column_map)
    if args.asset_id:
        kwargs["asset_id"] = args.asset_id
    if args.timezone:
        kwargs["timezone"] = args.timezone
    if args.interval_minutes:
        kwargs["interval_minutes"] = args.interval_minutes

    try:
        records = transform(input_path, source=source, **kwargs)
    except Exception as exc:
        print(f"Error: transform failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        output_text = json.dumps(records, indent=2)
        if args.output:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Wrote {len(records)} records to {args.output}", file=sys.stderr)
        else:
            print(output_text)
        return

    if args.format == "csv":
        if args.output:
            odse_io.to_csv(records, args.output)
            print(f"Wrote {len(records)} records to {args.output}", file=sys.stderr)
        else:
            print(_records_to_csv_text(records), end="")
        return

    if args.format == "parquet":
        output_path = args.output
        if not output_path:
            print("Error: --output is required for parquet format", file=sys.stderr)
            sys.exit(1)
        try:
            odse_io.to_parquet(records, output_path)
        except ImportError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"Wrote {len(records)} records to {output_path}", file=sys.stderr)
        return


def _cmd_validate(args):
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = [data]
    else:
        print("Error: input must be a JSON array or object", file=sys.stderr)
        sys.exit(1)

    total = len(records)
    passed = 0
    failed = 0
    all_errors = []
    all_warnings = []

    for i, record in enumerate(records):
        kwargs = {"level": args.level}
        if args.profile:
            kwargs["profile"] = args.profile
        if args.capacity_kw is not None:
            kwargs["capacity_kw"] = args.capacity_kw
        if args.latitude is not None:
            kwargs["latitude"] = args.latitude
        if args.longitude is not None:
            kwargs["longitude"] = args.longitude

        result = validate(record, **kwargs)
        if result.is_valid:
            passed += 1
        else:
            failed += 1
            for err in result.errors:
                all_errors.append({"record": i, "path": err.path, "code": err.code, "message": err.message})
        for warn in result.warnings:
            all_warnings.append({"record": i, "path": warn.path, "code": warn.code, "message": warn.message})

    report = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": all_errors,
        "warnings": all_warnings,
    }

    print(json.dumps(report, indent=2))
    sys.exit(0 if failed == 0 else 1)


def _parse_column_map(spec: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    pairs = [part.strip() for part in spec.split(",") if part.strip()]
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(
                f"Invalid --column-map segment '{pair}'. Expected key=value."
            )
        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ValueError(
                f"Invalid --column-map segment '{pair}'. Expected key=value."
            )
        mapping[key] = value
    if "timestamp" not in mapping:
        raise ValueError("--column-map must include timestamp=CSV_COLUMN")
    return mapping


def _records_to_csv_text(records: List[Dict[str, Any]]) -> str:
    if not records:
        return ""
    fieldnames = sorted({key for rec in records for key in rec.keys()})
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue()




if __name__ == "__main__":
    main()

# ODS-E Quickstart (60-Second First Value)

This page gets you from install to validated ODS-E output with bundled sample data.

## 1) Install (10 seconds)

```bash
pip install -e src/python[parquet]
```

## 2) Transform your first file (30 seconds)

```bash
odse transform --source generic_csv \
  --input examples/fixtures/quickstart_scada.csv \
  --column-map timestamp=Timestamp,kWh=ActiveEnergy,asset_id=Asset \
  --output examples/output/quickstart.cleaned.json
```

## 3) Validate (10 seconds)

```bash
odse validate --input examples/output/quickstart.cleaned.json --level schema
```

## 4) What just happened (10 seconds)

The `transform` command mapped raw SCADA columns into ODS-E records with normalized field names.
The `validate` command checked each record against ODS-E schema rules and printed a batch report.
You now have clean, validated ODS-E records ready for downstream analytics and storage.

## 5) Optional: write Parquet from CLI

```bash
odse transform --source generic_csv \
  --input examples/fixtures/quickstart_scada.csv \
  --column-map timestamp=Timestamp,kWh=ActiveEnergy,asset_id=Asset \
  --format parquet \
  --output examples/output/quickstart.parquet
```

## 6) Next: do it in Python

```python
from pathlib import Path

from odse import to_parquet, transform, validate_batch

records = transform(
    Path("examples/fixtures/quickstart_scada.csv"),
    source="generic_csv",
    column_map={
        "timestamp": "Timestamp",
        "kWh": "ActiveEnergy",
        "asset_id": "Asset",
    },
)

result = validate_batch(records, level="schema")
print(result.summary)

to_parquet(records, "examples/output/quickstart_py_parquet", partition_by=["asset_id", "year", "month", "day"])
```

## 7) Next steps

- [For Data Engineers guide](examples/README.md)
- [Bring Your Own Data tutorial](examples/generic_csv_transform.py)
- [SDK reference surface](src/python/odse/__init__.py)

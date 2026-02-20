# ODS-E SDK Examples

These examples are copy-paste runnable from the repository root and use only public `odse` APIs.

## Run

```bash
python3 examples/basic_transform.py
python3 examples/generic_csv_transform.py
python3 examples/pipeline.py
python3 examples/batch_directory.py
```

## Included examples

- `examples/basic_transform.py`
  - Single OEM transform (Huawei fixture) -> JSONL + Parquet output.
- `examples/generic_csv_transform.py`
  - Generic CSV column-mapping transform -> batch validation -> JSONL + Parquet output.
- `examples/pipeline.py`
  - Full flow: transform -> enrich settlement context -> validate_batch -> JSONL + Parquet output.
- `examples/batch_directory.py`
  - Process a directory of mixed OEM files into one partitioned output.

## Fixtures

Synthetic fixture data is bundled in `examples/fixtures/` and `examples/fixtures/batch/`.

## Outputs

By default, scripts write to:

- `examples/output/`
- `examples/output_batch/`

Parquet writes require optional dependencies (`odse[parquet]`).
If those dependencies are missing, each script still completes and reports parquet as skipped.

import csv
import json
import os
import tempfile
import unittest
from unittest import mock

from odse.io import to_csv, to_dataframe, to_json, to_parquet


def _has_pandas():
    try:
        import pandas  # noqa: F401
    except ImportError:
        return False
    return True


def _has_pyarrow():
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        return False
    return True


class IOSerializationTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "timestamp": "2026-02-09T12:00:00Z",
                "kWh": 5.0,
                "error_type": "normal",
                "asset_id": "SITE-001",
            },
            {
                "timestamp": "2026-02-09T13:00:00Z",
                "kWh": 4.0,
                "error_type": "warning",
                "asset_id": "SITE-001",
            },
        ]

    def test_to_json_writes_jsonl(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as handle:
            path = handle.name
        try:
            to_json(self.records, path)
            with open(path, encoding="utf-8") as handle:
                lines = [line.rstrip("\n") for line in handle.readlines()]
            self.assertEqual(len(lines), 2)
            first = json.loads(lines[0])
            self.assertEqual(first["timestamp"], "2026-02-09T12:00:00Z")
            self.assertEqual(first["kWh"], 5.0)
        finally:
            os.unlink(path)

    def test_to_csv_writes_headers(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as handle:
            path = handle.name
        try:
            to_csv(self.records, path)
            with open(path, encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertIn("timestamp", reader.fieldnames)
            self.assertIn("kWh", reader.fieldnames)
            self.assertEqual(len(rows), 2)
        finally:
            os.unlink(path)

    def test_to_parquet_raises_without_pyarrow(self):
        real_import = __import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "pyarrow":
                raise ImportError("No module named pyarrow")
            return real_import(name, globals, locals, fromlist, level)

        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch("builtins.__import__", side_effect=fake_import):
                with self.assertRaises(ImportError):
                    to_parquet(self.records, tmp_dir, partition_by=["asset_id", "year"])


@unittest.skipUnless(_has_pandas(), "pandas not installed")
class DataFrameTests(unittest.TestCase):
    def test_to_dataframe_dtypes(self):
        df = to_dataframe(
            [
                {
                    "timestamp": "2026-02-09T12:00:00Z",
                    "kWh": 5,
                    "error_type": "normal",
                }
            ]
        )
        self.assertTrue(str(df["timestamp"].dtype).startswith("datetime64"))
        self.assertEqual(str(df["kWh"].dtype), "float64")


@unittest.skipUnless(_has_pandas() and _has_pyarrow(), "pandas/pyarrow not installed")
class ParquetTests(unittest.TestCase):
    def test_partition_fields_derived_from_timestamp(self):
        import pandas as pd

        records = [
            {
                "timestamp": "2026-02-09T12:15:00Z",
                "kWh": 3.2,
                "error_type": "normal",
                "asset_id": "SITE-001",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            to_parquet(records, tmp_dir, partition_by=["asset_id", "year", "month", "day", "hour"])
            expected_file = os.path.join(
                tmp_dir,
                "asset_id=SITE-001",
                "year=2026",
                "month=2",
                "day=9",
                "hour=12",
                "part-00000.parquet",
            )
            self.assertTrue(os.path.exists(expected_file))
            df = pd.read_parquet(expected_file, engine="pyarrow")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["kWh"], 3.2)

    def test_append_mode_appends_partition_file(self):
        import pandas as pd

        batch_one = [
            {
                "timestamp": "2026-02-09T12:00:00Z",
                "kWh": 1.0,
                "error_type": "normal",
                "asset_id": "SITE-001",
            }
        ]
        batch_two = [
            {
                "timestamp": "2026-02-09T12:30:00Z",
                "kWh": 2.0,
                "error_type": "normal",
                "asset_id": "SITE-001",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parts = ["asset_id", "year", "month", "day", "hour"]
            to_parquet(batch_one, tmp_dir, partition_by=parts)
            to_parquet(batch_two, tmp_dir, partition_by=parts, mode="append")
            expected_file = os.path.join(
                tmp_dir,
                "asset_id=SITE-001",
                "year=2026",
                "month=2",
                "day=9",
                "hour=12",
                "part-00000.parquet",
            )
            df = pd.read_parquet(expected_file, engine="pyarrow")
            self.assertEqual(len(df), 2)


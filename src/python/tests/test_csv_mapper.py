import json
import os
import tempfile
import unittest

from odse.transformer import transform


class GenericCSVTransformerTests(unittest.TestCase):
    """Tests for SEP-020 generic CSV column-mapping transformer."""

    def test_basic_mapping_with_kwh(self):
        csv_data = (
            "ts,energy_kwh,status\n"
            "2026-02-09 12:00:00,5.0,normal\n"
            "2026-02-09 12:05:00,4.8,normal\n"
        )
        mapping = {
            "timestamp": "ts",
            "kWh": "energy_kwh",
            "error_type": "status",
        }
        rows = transform(csv_data, source="csv", mapping=mapping)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["kWh"], 5.0)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertIn("2026-02-09", rows[0]["timestamp"])

    def test_kw_fallback_to_kwh(self):
        csv_data = (
            "time,power_kw\n"
            "2026-02-09 12:00:00,10.0\n"
        )
        mapping = {"timestamp": "time", "kW": "power_kw"}
        rows = transform(csv_data, source="csv", mapping=mapping, interval_minutes=5)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["kWh"], 10.0 * (5.0 / 60.0))
        self.assertEqual(rows[0]["kW"], 10.0)

    def test_asset_id_from_column(self):
        csv_data = (
            "ts,kwh,site\n"
            "2026-02-09 12:00:00,5.0,SITE-A\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh", "asset_id": "site"}
        rows = transform(csv_data, source="csv", mapping=mapping)
        self.assertEqual(rows[0]["asset_id"], "SITE-A")

    def test_asset_id_from_kwarg_overrides_column(self):
        csv_data = (
            "ts,kwh,site\n"
            "2026-02-09 12:00:00,5.0,SITE-A\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh"}
        rows = transform(csv_data, source="csv", mapping=mapping, asset_id="OVERRIDE")
        self.assertEqual(rows[0]["asset_id"], "OVERRIDE")

    def test_error_code_mapping(self):
        csv_data = (
            "ts,kwh,err\n"
            "2026-02-09 12:00:00,5.0,E101\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh", "error_code": "err"}
        rows = transform(csv_data, source="csv", mapping=mapping)
        self.assertEqual(rows[0]["error_code"], "E101")

    def test_default_error_type(self):
        csv_data = (
            "ts,kwh\n"
            "2026-02-09 12:00:00,5.0\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh"}
        rows = transform(csv_data, source="csv", mapping=mapping)
        self.assertEqual(rows[0]["error_type"], "normal")

    def test_custom_default_error_type(self):
        csv_data = (
            "ts,kwh\n"
            "2026-02-09 12:00:00,5.0\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh"}
        rows = transform(
            csv_data, source="csv", mapping=mapping, default_error_type="unknown"
        )
        self.assertEqual(rows[0]["error_type"], "unknown")

    def test_extra_columns_mapping(self):
        csv_data = (
            "ts,kwh,temp,freq\n"
            "2026-02-09 12:00:00,5.0,41.2,50.01\n"
        )
        mapping = {
            "timestamp": "ts",
            "kWh": "kwh",
            "extra": {"temperature": "temp", "frequency": "freq"},
        }
        rows = transform(csv_data, source="csv", mapping=mapping)
        self.assertAlmostEqual(rows[0]["temperature"], 41.2)
        self.assertAlmostEqual(rows[0]["frequency"], 50.01)

    def test_missing_timestamp_skips_row(self):
        csv_data = (
            "ts,kwh\n"
            ",5.0\n"
            "2026-02-09 12:05:00,4.8\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh"}
        rows = transform(csv_data, source="csv", mapping=mapping)
        self.assertEqual(len(rows), 1)

    def test_missing_mapping_raises(self):
        with self.assertRaises(ValueError) as ctx:
            transform("ts,kwh\n", source="csv")
        self.assertIn("mapping", str(ctx.exception).lower())

    def test_missing_timestamp_key_raises(self):
        with self.assertRaises(ValueError):
            transform("ts,kwh\n", source="csv", mapping={"kWh": "kwh"})

    def test_generic_alias(self):
        csv_data = (
            "ts,kwh\n"
            "2026-02-09 12:00:00,5.0\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh"}
        rows = transform(csv_data, source="generic", mapping=mapping)
        self.assertEqual(len(rows), 1)

    def test_json_mapping_file(self):
        csv_data = (
            "ts,kwh\n"
            "2026-02-09 12:00:00,5.0\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh"}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mapping, f)
            f.flush()
            try:
                rows = transform(csv_data, source="csv", mapping=f.name)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["kWh"], 5.0)
            finally:
                os.unlink(f.name)

    def test_timezone_applied(self):
        csv_data = (
            "ts,kwh\n"
            "2026-02-09 12:00:00,5.0\n"
        )
        mapping = {"timestamp": "ts", "kWh": "kwh"}
        rows = transform(
            csv_data, source="csv", mapping=mapping, timezone="+02:00"
        )
        self.assertIn("+02:00", rows[0]["timestamp"])

    def test_zero_kwh_and_kw_defaults_to_zero(self):
        csv_data = (
            "ts,other\n"
            "2026-02-09 12:00:00,foo\n"
        )
        mapping = {"timestamp": "ts"}
        rows = transform(csv_data, source="csv", mapping=mapping)
        self.assertEqual(rows[0]["kWh"], 0.0)


if __name__ == "__main__":
    unittest.main()

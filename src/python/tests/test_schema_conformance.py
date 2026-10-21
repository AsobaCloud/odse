"""SEP-049 conformance harness.

Strict Draft 2020-12 validation of transformer output records against
schemas/energy-timeseries.json. Prevents schema/runtime drift: any key
emitted by a transformer that is not defined in the schema fails here,
so new fields must be schema'd (or the transform fixed) first.

Related: SEP-049 (issue #56).
"""
import json
import unittest
from pathlib import Path

from odse.transformer import transform
from odse.validator import SCHEMA_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "schemas" / "energy-timeseries.json"
FIXTURE_DIR = REPO_ROOT / "examples" / "data"

# (source key, fixture file) — real fixture files from examples/data (SEP-037)
FIXTURE_FILE_TRANSFORMS = [
    ("huawei", "huawei_fusionsolar_24h.csv"),
]

# (source key, inline payload, transform kwargs) — payloads mirror
# tests/test_transformer_runtime.py shapes for OEMs whose example fixtures
# require API response formats (JSON) not present in examples/data yet.
# TODO (SEP-051): replace with real JSON fixture files as they land.
INLINE_PAYLOAD_TRANSFORMS = [
    (
        "enphase",
        json.dumps([
            {"end_at": 1739102400, "wh_del": 3500, "devices_reporting": 9},
            {"end_at": 1739102700, "wh_del": 3400, "devices_reporting": 10},
        ]),
        {"expected_devices": 10},
    ),
    (
        "solarman",
        "Update Time,Generation(kWh),Device State,Power(W)\n"
        "2026-02-09 12:00:00,100.0,Operating,500\n"
        "2026-02-09 12:05:00,100.6,Operating,600\n",
        {},
    ),
]


def _has_jsonschema():
    try:
        import jsonschema  # noqa: F401
        return True
    except ImportError:
        return False


class TestSchemaConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = None
        if _has_jsonschema():
            from jsonschema import Draft202012Validator
            with open(SCHEMA_PATH) as f:
                cls.validator = Draft202012Validator(json.load(f))

    def test_validator_schema_fields_parity(self):
        """validator.SCHEMA_FIELDS must exactly mirror schema file properties."""
        with open(SCHEMA_PATH) as f:
            props = set(json.load(f)["properties"])
        self.assertEqual(
            SCHEMA_FIELDS, props,
            "SCHEMA_FIELDS (validator.py) and schemas/energy-timeseries.json have drifted",
        )

    def test_unknown_field_warning(self):
        """validate() warns (non-fatally) on fields outside the schema."""
        from odse.validator import validate

        result = validate({
            "timestamp": "2026-10-21T12:00:00+02:00",
            "kWh": 1.9,
            "error_type": "normal",
            "power_watts": 2280,  # not a schema field
        })
        self.assertTrue(result.is_valid)
        self.assertIn("UNKNOWN_FIELD", [w.code for w in result.warnings])
        self.assertIn("$.power_watts", [w.path for w in result.warnings])

    @unittest.skipUnless(_has_jsonschema(), "jsonschema not installed")
    def test_fixture_transform_output_strictly_valid(self):
        """Every OEM fixture transform output must pass strict schema validation."""
        failures = []
        for source, filename in FIXTURE_FILE_TRANSFORMS:
            records = transform((FIXTURE_DIR / filename).read_text(), source=source)
            self.assertTrue(records, f"{filename} produced no records")
            for i, rec in enumerate(records):
                for err in sorted(self.validator.iter_errors(rec), key=str):
                    failures.append(
                        f"{source}/{filename}[{i}]: {err.message}"
                    )
        for source, payload, kwargs in INLINE_PAYLOAD_TRANSFORMS:
            records = transform(payload, source=source, **kwargs)
            self.assertTrue(records, f"{source} inline payload produced no records")
            for i, rec in enumerate(records):
                for err in sorted(self.validator.iter_errors(rec), key=str):
                    failures.append(f"{source}[{i}]: {err.message}")
        self.assertEqual([], failures, "\n".join(failures))

    @unittest.skipUnless(_has_jsonschema(), "jsonschema not installed")
    def test_full_electrical_record_strictly_valid(self):
        """A record exercising every SEP-049 electrical field must validate strictly."""
        rec = {
            "timestamp": "2026-10-21T12:00:00+02:00",
            "kWh": 1.9,
            "kW": 22.8,
            "kVAr": 2.2,
            "voltage_ac": 236.5,
            "voltage_ac_l1": 236.8,
            "voltage_ac_l2": 236.1,
            "voltage_ac_l3": 236.6,
            "current_ac": 55.7,
            "current_ac_l1": 18.6,
            "current_ac_l2": 18.5,
            "current_ac_l3": 18.6,
            "frequency": 50.0,
            "voltage_dc": 580.3,
            "current_dc": 39.1,
            "temperature": 41.2,
            "ambient_temperature_c": 24.0,
            "module_temperature_c": 45.7,
            "poa_irradiance": 812.0,
            "ghi": 780.0,
            "dni": 690.0,
            "dhi": 120.0,
            "error_type": "normal",
        }
        self.validator.validate(rec)  # raises on failure


if __name__ == "__main__":
    unittest.main()

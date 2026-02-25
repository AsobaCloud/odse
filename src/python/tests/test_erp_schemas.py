"""Tests for ERP enrichment JSON schemas and IFS Cloud YAML transform.

Validates the 7 ERP enrichment JSON Schema files for structural correctness,
ODS-E conventions, and sample record conformance, plus validates the IFS Cloud
YAML transform structure and cross-schema consistency.
"""

import json
import re
import unittest
from pathlib import Path


SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas"
ERP_TRANSFORM_DIR = Path(__file__).resolve().parents[3] / "erp-transforms"

ERP_SCHEMAS = [
    "equipment-id-map.json",
    "equipment-register.json",
    "maintenance-history.json",
    "spare-parts.json",
    "procurement-context.json",
    "failure-taxonomy.json",
    "alarm-frequency-profile.json",
]

SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


def _has_jsonschema():
    try:
        import jsonschema  # noqa: F401
        return True
    except ImportError:
        return False


def _has_yaml():
    try:
        import yaml  # noqa: F401
        return True
    except ImportError:
        return False


def _load_schema(name):
    with open(SCHEMA_DIR / name) as f:
        return json.load(f)


def _collect_enums(obj):
    """Recursively collect all enum arrays from a JSON Schema."""
    found = []
    if isinstance(obj, dict):
        if "enum" in obj:
            found.append(obj["enum"])
        for v in obj.values():
            found.extend(_collect_enums(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_enums(item))
    return found


# ---------------------------------------------------------------------------
# Class 1: Schema file structure and ODS-E convention checks (stdlib only)
# ---------------------------------------------------------------------------

class ERPSchemaStructureTests(unittest.TestCase):
    """Structural checks using only the json stdlib module."""

    @classmethod
    def setUpClass(cls):
        cls.schemas = {}
        for name in ERP_SCHEMAS:
            cls.schemas[name] = _load_schema(name)

    def test_all_schemas_valid_json(self):
        """All 7 schema files parse as valid JSON."""
        for name in ERP_SCHEMAS:
            with self.subTest(schema=name):
                self.assertIn(name, self.schemas)

    def test_schema_has_draft_2020_12(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                self.assertEqual(
                    schema.get("$schema"),
                    "https://json-schema.org/draft/2020-12/schema",
                )

    def test_schema_id_matches_filename(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                expected = f"https://ona-protocol.org/schemas/v1/{name}"
                self.assertEqual(schema.get("$id"), expected)

    def test_schema_title_starts_with_odse(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                self.assertTrue(
                    schema.get("title", "").startswith("ODS-E"),
                    f"{name} title does not start with 'ODS-E': {schema.get('title')}",
                )

    def test_schema_has_additional_properties_false(self):
        """Top-level object (or array items) has additionalProperties: false."""
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                if schema.get("type") == "object":
                    self.assertFalse(schema.get("additionalProperties", True))
                elif schema.get("type") == "array":
                    items = schema.get("items", {})
                    self.assertFalse(items.get("additionalProperties", True))

    def test_nested_objects_have_additional_properties_false(self):
        """Nested object definitions also disallow extra properties."""
        # equipment-id-map source items
        id_map = self.schemas["equipment-id-map.json"]
        source_items = id_map["items"]["properties"]["sources"]["items"]
        self.assertFalse(source_items.get("additionalProperties", True))

        # maintenance-history parts_consumed items
        mh = self.schemas["maintenance-history.json"]
        parts_items = mh["properties"]["parts_consumed"]["items"]
        self.assertFalse(parts_items.get("additionalProperties", True))

    def test_enums_are_lowercase_snake_case(self):
        for name, schema in self.schemas.items():
            for enum_values in _collect_enums(schema):
                for val in enum_values:
                    with self.subTest(schema=name, value=val):
                        self.assertRegex(
                            val, SNAKE_RE,
                            f"Enum value '{val}' in {name} is not lowercase_snake_case",
                        )

    def test_required_fields_declared(self):
        expected = {
            "equipment-id-map.json": ["equipment_id", "sources"],
            "equipment-register.json": ["equipment_id", "site_id", "equipment_type"],
            "maintenance-history.json": [
                "equipment_id", "work_order_id", "wo_type", "wo_status", "reported_date",
            ],
            "spare-parts.json": ["part_id", "qty_on_hand"],
            "procurement-context.json": ["part_id"],
            "failure-taxonomy.json": ["failure_code", "failure_description"],
            "alarm-frequency-profile.json": ["equipment_id", "alarm_code"],
        }
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                # For array schemas, required lives on items
                target = schema if schema.get("type") == "object" else schema.get("items", {})
                self.assertEqual(
                    sorted(target.get("required", [])),
                    sorted(expected[name]),
                )

    def test_cross_schema_field_type_consistency(self):
        """equipment_id and part_id are string type in every schema that uses them."""
        for name, schema in self.schemas.items():
            props = schema.get("properties", {})
            if schema.get("type") == "array":
                props = schema.get("items", {}).get("properties", {})
            with self.subTest(schema=name, field="equipment_id"):
                if "equipment_id" in props:
                    self.assertEqual(props["equipment_id"]["type"], "string")
            with self.subTest(schema=name, field="part_id"):
                if "part_id" in props:
                    self.assertEqual(props["part_id"]["type"], "string")

    def test_equipment_register_type_enum(self):
        schema = self.schemas["equipment-register.json"]
        enum_vals = schema["properties"]["equipment_type"]["enum"]
        expected = [
            "site", "array", "inverter", "combiner", "string",
            "module", "transformer", "tracker", "meter",
        ]
        self.assertEqual(sorted(enum_vals), sorted(expected))
        self.assertEqual(len(enum_vals), 9)

    def test_alarm_frequency_count_fields_are_integer(self):
        schema = self.schemas["alarm-frequency-profile.json"]
        props = schema["properties"]
        for field in ["count_7d", "count_30d", "count_90d", "prior_wo_count_same_alarm"]:
            with self.subTest(field=field):
                self.assertEqual(props[field]["type"], "integer")

    def test_equipment_id_map_is_array_type(self):
        schema = self.schemas["equipment-id-map.json"]
        self.assertEqual(schema["type"], "array")
        # All other schemas are object type
        for name, s in self.schemas.items():
            if name != "equipment-id-map.json":
                with self.subTest(schema=name):
                    self.assertEqual(s["type"], "object")

    def test_numeric_fields_have_minimum_zero(self):
        checks = {
            "equipment-register.json": ["design_capacity_kw"],
            "maintenance-history.json": ["downtime_hours", "total_cost"],
            "spare-parts.json": [
                "qty_on_hand", "qty_reserved", "qty_available",
                "reorder_point", "supplier_lead_time_days", "last_unit_cost",
            ],
            "procurement-context.json": [
                "avg_lead_time_days", "avg_unit_cost", "open_po_qty",
            ],
            "failure-taxonomy.json": [
                "recurrence_rate", "typical_mttr_hours", "typical_cost",
            ],
            "alarm-frequency-profile.json": [
                "count_7d", "count_30d", "count_90d",
                "mean_time_between_alarms_hours", "escalation_rate",
                "prior_wo_count_same_alarm",
            ],
        }
        for schema_name, fields in checks.items():
            props = self.schemas[schema_name]["properties"]
            for field in fields:
                with self.subTest(schema=schema_name, field=field):
                    self.assertEqual(props[field].get("minimum"), 0)

    def test_date_fields_have_format(self):
        date_fields = {
            "equipment-register.json": {
                "install_date": "date",
                "warranty_expiry": "date",
            },
            "maintenance-history.json": {
                "reported_date": "date-time",
                "completed_date": "date-time",
            },
            "procurement-context.json": {
                "last_po_date": "date",
                "open_po_eta": "date",
            },
        }
        for schema_name, field_map in date_fields.items():
            props = self.schemas[schema_name]["properties"]
            for field, fmt in field_map.items():
                with self.subTest(schema=schema_name, field=field):
                    self.assertEqual(props[field].get("format"), fmt)


# ---------------------------------------------------------------------------
# Class 2: Sample record validation (requires jsonschema)
# ---------------------------------------------------------------------------

@unittest.skipUnless(_has_jsonschema(), "jsonschema not installed")
class ERPSchemaValidationTests(unittest.TestCase):
    """Validates sample records against schemas using jsonschema."""

    @classmethod
    def setUpClass(cls):
        from jsonschema import Draft202012Validator
        cls.validators = {}
        for name in ERP_SCHEMAS:
            schema = _load_schema(name)
            cls.validators[name] = Draft202012Validator(schema)

    def _assert_valid(self, schema_name, instance):
        self.validators[schema_name].validate(instance)

    def _assert_invalid(self, schema_name, instance):
        from jsonschema import ValidationError
        with self.assertRaises(ValidationError):
            self.validators[schema_name].validate(instance)

    # -- equipment-id-map --

    def _base_id_map_record(self, **overrides):
        record = {
            "equipment_id": "EQ-001",
            "sources": [
                {"system": "ifs-cloud", "type": "erp", "native_id": "MCH-100"}
            ],
        }
        record.update(overrides)
        return record

    def test_id_map_valid_array(self):
        self._assert_valid("equipment-id-map.json", [self._base_id_map_record()])

    def test_id_map_missing_equipment_id(self):
        rec = self._base_id_map_record()
        del rec["equipment_id"]
        self._assert_invalid("equipment-id-map.json", [rec])

    def test_id_map_invalid_source_type_enum(self):
        rec = self._base_id_map_record()
        rec["sources"] = [{"system": "x", "type": "INVALID", "native_id": "y"}]
        self._assert_invalid("equipment-id-map.json", [rec])

    # -- equipment-register --

    def _base_register_record(self, **overrides):
        record = {
            "equipment_id": "EQ-001",
            "site_id": "SITE-A",
            "equipment_type": "inverter",
        }
        record.update(overrides)
        return record

    def test_register_valid_record(self):
        self._assert_valid("equipment-register.json", self._base_register_record())

    def test_register_missing_site_id(self):
        rec = self._base_register_record()
        del rec["site_id"]
        self._assert_invalid("equipment-register.json", rec)

    def test_register_invalid_equipment_type_enum(self):
        self._assert_invalid(
            "equipment-register.json",
            self._base_register_record(equipment_type="INVALID"),
        )

    def test_register_extra_property_rejected(self):
        self._assert_invalid(
            "equipment-register.json",
            self._base_register_record(unknown_field="oops"),
        )

    def test_register_full_record(self):
        rec = self._base_register_record(
            equipment_subtype="central",
            parent_equipment_id="EQ-000",
            source_equipment_id="MCH-100",
            manufacturer="SMA",
            model="STP-50",
            serial_number="SN123",
            install_date="2024-01-15",
            warranty_expiry="2029-01-15",
            design_capacity_kw=50.0,
            cost_center="CC-100",
        )
        self._assert_valid("equipment-register.json", rec)

    # -- maintenance-history --

    def _base_maintenance_record(self, **overrides):
        record = {
            "equipment_id": "EQ-001",
            "work_order_id": "WO-1001",
            "wo_type": "corrective",
            "wo_status": "open",
            "reported_date": "2026-02-10T08:00:00Z",
        }
        record.update(overrides)
        return record

    def test_maintenance_valid_record(self):
        self._assert_valid(
            "maintenance-history.json", self._base_maintenance_record(),
        )

    def test_maintenance_missing_required(self):
        rec = self._base_maintenance_record()
        del rec["work_order_id"]
        self._assert_invalid("maintenance-history.json", rec)

    def test_maintenance_invalid_wo_type_enum(self):
        self._assert_invalid(
            "maintenance-history.json",
            self._base_maintenance_record(wo_type="INVALID"),
        )

    def test_maintenance_invalid_wo_status_enum(self):
        self._assert_invalid(
            "maintenance-history.json",
            self._base_maintenance_record(wo_status="INVALID"),
        )

    def test_maintenance_valid_parts_consumed(self):
        rec = self._base_maintenance_record(
            parts_consumed=[{"part_id": "SP-001", "qty": 2}],
        )
        self._assert_valid("maintenance-history.json", rec)

    def test_maintenance_invalid_nested_part_missing_part_id(self):
        rec = self._base_maintenance_record(
            parts_consumed=[{"qty": 2}],
        )
        self._assert_invalid("maintenance-history.json", rec)

    def test_maintenance_full_record(self):
        rec = self._base_maintenance_record(
            completed_date="2026-02-11T14:00:00Z",
            source_equipment_id="MCH-100",
            downtime_hours=6.5,
            failure_code="FC-01",
            cause_code="CC-01",
            total_cost=1200.00,
            parts_consumed=[{"part_id": "SP-001", "qty": 3}],
        )
        self._assert_valid("maintenance-history.json", rec)

    # -- spare-parts --

    def _base_spare_parts_record(self, **overrides):
        record = {
            "part_id": "SP-001",
            "qty_on_hand": 10,
        }
        record.update(overrides)
        return record

    def test_spare_parts_valid_record(self):
        self._assert_valid("spare-parts.json", self._base_spare_parts_record())

    def test_spare_parts_negative_qty_on_hand(self):
        self._assert_invalid(
            "spare-parts.json",
            self._base_spare_parts_record(qty_on_hand=-1),
        )

    def test_spare_parts_full_record(self):
        rec = self._base_spare_parts_record(
            description="DC Fuse 15A",
            equipment_types_served=["inverter", "combiner"],
            qty_reserved=2,
            qty_available=8,
            reorder_point=5,
            supplier_lead_time_days=14,
            last_unit_cost=3.50,
        )
        self._assert_valid("spare-parts.json", rec)

    # -- procurement-context --

    def _base_procurement_record(self, **overrides):
        record = {"part_id": "SP-001"}
        record.update(overrides)
        return record

    def test_procurement_valid_minimal(self):
        self._assert_valid(
            "procurement-context.json", self._base_procurement_record(),
        )

    def test_procurement_valid_full(self):
        rec = self._base_procurement_record(
            preferred_supplier="ACME Corp",
            avg_lead_time_days=21,
            avg_unit_cost=3.25,
            last_po_date="2026-01-15",
            open_po_qty=50,
            open_po_eta="2026-03-01",
        )
        self._assert_valid("procurement-context.json", rec)

    def test_procurement_extra_property_rejected(self):
        self._assert_invalid(
            "procurement-context.json",
            self._base_procurement_record(bogus="x"),
        )

    # -- failure-taxonomy --

    def _base_failure_record(self, **overrides):
        record = {
            "failure_code": "FC-01",
            "failure_description": "Inverter overtemperature shutdown",
        }
        record.update(overrides)
        return record

    def test_failure_valid_record(self):
        self._assert_valid("failure-taxonomy.json", self._base_failure_record())

    def test_failure_recurrence_rate_above_one_rejected(self):
        self._assert_invalid(
            "failure-taxonomy.json",
            self._base_failure_record(recurrence_rate=1.5),
        )

    def test_failure_negative_mttr_rejected(self):
        self._assert_invalid(
            "failure-taxonomy.json",
            self._base_failure_record(typical_mttr_hours=-1),
        )

    def test_failure_full_record(self):
        rec = self._base_failure_record(
            cause_code="CC-01",
            cause_description="Fan failure",
            recurrence_rate=0.15,
            typical_mttr_hours=4.0,
            typical_cost=800.00,
        )
        self._assert_valid("failure-taxonomy.json", rec)

    # -- alarm-frequency-profile --

    def _base_alarm_record(self, **overrides):
        record = {
            "equipment_id": "EQ-001",
            "alarm_code": "ALM-100",
        }
        record.update(overrides)
        return record

    def test_alarm_valid_record(self):
        self._assert_valid(
            "alarm-frequency-profile.json", self._base_alarm_record(),
        )

    def test_alarm_non_integer_count_rejected(self):
        self._assert_invalid(
            "alarm-frequency-profile.json",
            self._base_alarm_record(count_7d=3.5),
        )

    def test_alarm_invalid_prior_resolution_enum(self):
        self._assert_invalid(
            "alarm-frequency-profile.json",
            self._base_alarm_record(prior_resolution="INVALID"),
        )

    def test_alarm_negative_escalation_rate_rejected(self):
        self._assert_invalid(
            "alarm-frequency-profile.json",
            self._base_alarm_record(escalation_rate=-0.5),
        )

    def test_alarm_full_record(self):
        rec = self._base_alarm_record(
            source_equipment_id="INV-42",
            count_7d=12,
            count_30d=35,
            count_90d=80,
            mean_time_between_alarms_hours=14.2,
            escalation_rate=1.37,
            prior_wo_count_same_alarm=3,
            prior_resolution="closed_resolved",
        )
        self._assert_valid("alarm-frequency-profile.json", rec)


# ---------------------------------------------------------------------------
# Class 3: IFS Cloud YAML transform validation (requires PyYAML)
# ---------------------------------------------------------------------------

@unittest.skipUnless(_has_yaml(), "PyYAML not installed")
class IFSCloudTransformTests(unittest.TestCase):
    """Validates the IFS Cloud YAML transform structure."""

    @classmethod
    def setUpClass(cls):
        import yaml
        with open(ERP_TRANSFORM_DIR / "ifs-cloud.yaml") as f:
            cls.doc = yaml.safe_load(f)

    def test_yaml_parses(self):
        self.assertIsInstance(self.doc, dict)

    def test_has_required_sections(self):
        for section in [
            "transform", "input_schema", "equipment_id_resolution",
            "extractions", "validation", "notes",
        ]:
            with self.subTest(section=section):
                self.assertIn(section, self.doc)

    def test_transform_metadata(self):
        t = self.doc["transform"]
        self.assertEqual(t["name"], "ifs-cloud")
        self.assertEqual(t["vendor"], "IFS")

    def test_all_extractions_reference_existing_schemas(self):
        for ext_name, ext in self.doc["extractions"].items():
            with self.subTest(extraction=ext_name):
                target = ext["target_schema"]
                self.assertTrue(
                    (SCHEMA_DIR / target).exists(),
                    f"Schema file {target} referenced by extraction "
                    f"'{ext_name}' not found in {SCHEMA_DIR}",
                )

    def test_extraction_count(self):
        self.assertEqual(len(self.doc["extractions"]), 5)

    def test_each_extraction_has_output_mapping(self):
        for ext_name, ext in self.doc["extractions"].items():
            with self.subTest(extraction=ext_name):
                self.assertIn("output_mapping", ext)
                self.assertIsInstance(ext["output_mapping"], dict)

    def test_each_extraction_has_refresh_cadence(self):
        for ext_name, ext in self.doc["extractions"].items():
            with self.subTest(extraction=ext_name):
                self.assertIn("refresh_cadence", ext)

    def test_equipment_id_resolution_references_id_map(self):
        eid = self.doc["equipment_id_resolution"]
        self.assertEqual(eid["target_schema"], "equipment-id-map.json")


if __name__ == "__main__":
    unittest.main()

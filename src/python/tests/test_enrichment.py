import unittest

from odse.enrichment import enrich
from odse.transformer import transform


class EnrichmentTests(unittest.TestCase):
    """Tests for SEP-003 reference enrichment contract."""

    def _base_rows(self, count=2, **overrides):
        """Return a list of minimal valid ODS-E rows."""
        rows = []
        for i in range(count):
            record = {
                "timestamp": f"2026-02-18T{12 + i:02d}:00:00Z",
                "kWh": 5.0 + i,
                "error_type": "normal",
            }
            record.update(overrides)
            rows.append(record)
        return rows

    # --- CSV transform pathway ---

    def test_csv_transform_then_enrich_settlement(self):
        csv_data = (
            "timestamp,power,inverter_state,run_state\n"
            "2026-02-18 12:00:00,10,512,1\n"
        )
        rows = transform(csv_data, source="huawei")
        context = {
            "seller_party_id": "nersa:gen:SOLARPK-001",
            "buyer_party_id": "nersa:offtaker:MUN042",
            "settlement_period_start": "2026-02-18T12:00:00+02:00",
            "settlement_period_end": "2026-02-18T12:30:00+02:00",
            "contract_reference": "PPA-001",
            "settlement_type": "bilateral",
        }
        enriched = enrich(rows, context)
        self.assertEqual(len(enriched), 1)
        for key, value in context.items():
            self.assertEqual(enriched[0][key], value)
        # Original telemetry preserved
        self.assertIn("timestamp", enriched[0])
        self.assertIn("kWh", enriched[0])
        self.assertIn("error_type", enriched[0])

    def test_csv_transform_then_enrich_tariff(self):
        csv_data = (
            "timestampISO,dP1,dP2,dQ1,dQ2\n"
            "2026-02-18 12:00:00,1000,,200,\n"
        )
        rows = transform(csv_data, source="switch")
        context = {
            "tariff_schedule_id": "nersa:capetown:RES01:v3",
            "tariff_period": "peak",
            "tariff_currency": "ZAR",
        }
        enriched = enrich(rows, context)
        self.assertEqual(len(enriched), 1)
        for key, value in context.items():
            self.assertEqual(enriched[0][key], value)
        # Switch-specific fields preserved
        self.assertIn("kVA", enriched[0])
        self.assertIn("PF", enriched[0])

    # --- JSON transform pathway ---

    def test_json_transform_then_enrich_settlement(self):
        payload = """
        [
          {"end_at": 1739102400, "wh_del": 3500, "devices_reporting": 10}
        ]
        """
        rows = transform(payload, source="enphase", expected_devices=10)
        context = {
            "seller_party_id": "nersa:gen:ENPHASE-001",
            "settlement_type": "bilateral",
        }
        enriched = enrich(rows, context)
        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0]["seller_party_id"], "nersa:gen:ENPHASE-001")
        self.assertEqual(enriched[0]["settlement_type"], "bilateral")
        self.assertEqual(enriched[0]["kWh"], 3.5)

    def test_json_transform_then_enrich_topology(self):
        payload = """
        {
          "success": true,
          "code": 0,
          "result": {
            "uploadTime": "2026-02-18 12:00:00",
            "acpower": 4200.0,
            "yieldtoday": 18.4,
            "inverterStatus": "102"
          }
        }
        """
        rows = transform(payload, source="solaxcloud")
        context = {
            "country_code": "ZA",
            "municipality_id": "za.wc.city_of_cape_town",
            "distribution_zone": "CCT-NORTH",
            "voltage_level": "MV",
        }
        enriched = enrich(rows, context)
        self.assertEqual(len(enriched), 1)
        for key, value in context.items():
            self.assertEqual(enriched[0][key], value)

    # --- Conflict resolution: source wins (default) ---

    def test_source_field_not_overwritten_by_default(self):
        rows = self._base_rows(1, asset_id="ORIGINAL-001")
        enrich(rows, {"asset_id": "OVERRIDE-999"})
        self.assertEqual(rows[0]["asset_id"], "ORIGINAL-001")

    def test_context_fills_absent_fields_only(self):
        rows = self._base_rows(1, asset_id="ORIGINAL-001")
        enrich(rows, {
            "asset_id": "OVERRIDE-999",
            "seller_party_id": "nersa:gen:NEW-001",
        })
        self.assertEqual(rows[0]["asset_id"], "ORIGINAL-001")
        self.assertEqual(rows[0]["seller_party_id"], "nersa:gen:NEW-001")

    def test_error_type_preserved_when_context_conflicts(self):
        rows = self._base_rows(1, error_type="warning")
        enrich(rows, {"error_type": "normal"})
        self.assertEqual(rows[0]["error_type"], "warning")

    # --- Override mode: context wins ---

    def test_override_mode_overwrites_existing_fields(self):
        rows = self._base_rows(1, asset_id="ORIGINAL-001")
        enrich(rows, {"asset_id": "OVERRIDE-999"}, override=True)
        self.assertEqual(rows[0]["asset_id"], "OVERRIDE-999")

    def test_override_mode_also_fills_absent_fields(self):
        rows = self._base_rows(1, asset_id="ORIGINAL-001")
        enrich(rows, {
            "asset_id": "OVERRIDE-999",
            "seller_party_id": "nersa:gen:NEW-001",
        }, override=True)
        self.assertEqual(rows[0]["asset_id"], "OVERRIDE-999")
        self.assertEqual(rows[0]["seller_party_id"], "nersa:gen:NEW-001")

    # --- Edge cases ---

    def test_empty_context_is_noop(self):
        rows = self._base_rows(2)
        original = [dict(r) for r in rows]
        enrich(rows, {})
        self.assertEqual(rows, original)
        # Also test None
        rows2 = self._base_rows(2)
        enrich(rows2, None)
        self.assertEqual(rows2, original)

    def test_empty_rows_returns_empty(self):
        result = enrich([], {"seller_party_id": "nersa:gen:TEST-001"})
        self.assertEqual(result, [])

    def test_unknown_context_keys_passed_through(self):
        rows = self._base_rows(2)
        enrich(rows, {"custom_field": "value123"})
        for row in rows:
            self.assertEqual(row["custom_field"], "value123")


if __name__ == "__main__":
    unittest.main()

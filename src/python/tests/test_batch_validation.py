import unittest

from odse import BatchValidationResult, validate
from odse.validator import validate_batch


class BatchValidationTests(unittest.TestCase):
    def test_validate_batch_aggregates_counts_and_indexed_errors(self):
        records = [
            {"timestamp": "2026-02-09T12:00:00Z", "kWh": 5.0, "error_type": "normal"},
            {"kWh": 5.0, "error_type": "normal"},  # missing timestamp
            {"timestamp": "2026-02-09T12:05:00Z", "kWh": 6.0, "error_type": "normal"},
        ]
        result = validate_batch(records)
        self.assertIsInstance(result, BatchValidationResult)
        self.assertEqual(result.total, 3)
        self.assertEqual(result.valid, 2)
        self.assertEqual(result.invalid, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0][0], 1)
        self.assertEqual(result.errors[0][1].code, "REQUIRED_FIELD_MISSING")
        self.assertIn("2/3 valid", result.summary)
        self.assertIn("REQUIRED_FIELD_MISSING", result.summary)

    def test_validate_batch_profile_validation(self):
        records = [
            {
                "timestamp": "2026-02-09T12:00:00Z",
                "kWh": 5.0,
                "error_type": "normal",
                "seller_party_id": "nersa:gen:SELLER-1",
                "buyer_party_id": "nersa:buy:BUYER-1",
                "settlement_period_start": "2026-02-09T12:00:00Z",
                "settlement_period_end": "2026-02-09T12:30:00Z",
                "contract_reference": "C-001",
                "settlement_type": "bilateral",
            },
            {
                "timestamp": "2026-02-09T12:30:00Z",
                "kWh": 4.0,
                "error_type": "normal",
                "seller_party_id": "nersa:gen:SELLER-2",
            },
        ]

        result = validate_batch(records, profile="bilateral")
        self.assertEqual(result.total, 2)
        self.assertEqual(result.valid, 1)
        self.assertEqual(result.invalid, 1)
        self.assertGreaterEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0][0], 1)

    def test_validate_unchanged_for_single_record(self):
        record = {"timestamp": "2026-02-09T12:00:00Z", "kWh": 5.0, "error_type": "normal"}
        single = validate(record)
        batch = validate_batch([record])
        self.assertTrue(single.is_valid)
        self.assertEqual(batch.total, 1)
        self.assertEqual(batch.valid, 1)
        self.assertEqual(batch.invalid, 0)
        self.assertEqual(len(batch.errors), 0)


if __name__ == "__main__":
    unittest.main()

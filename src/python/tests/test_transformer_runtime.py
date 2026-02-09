import unittest

from ods_e.transformer import transform


class TransformerRuntimeTests(unittest.TestCase):
    def test_huawei_run_state_zero_maps_offline(self):
        csv_data = (
            "timestamp,power,inverter_state,run_state\n"
            "2026-02-09 12:00:00,10,512,0\n"
        )
        rows = transform(csv_data, source="huawei")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "offline")
        self.assertEqual(rows[0]["error_code"], "512")
        self.assertAlmostEqual(rows[0]["kWh"], 10.0 * (5.0 / 60.0))

    def test_huawei_warning_state_mapping(self):
        csv_data = (
            "timestamp,power,inverter_state,run_state\n"
            "2026-02-09 12:05:00,6,513,1\n"
        )
        rows = transform(csv_data, source="huawei")
        self.assertEqual(rows[0]["error_type"], "warning")

    def test_switch_status_parity(self):
        csv_data = (
            "timestampISO,dP1,dP2,dQ1,dQ2\n"
            "2026-02-09 12:00:00,1000,,200,\n"
            "2026-02-09 12:15:00,0,,0,\n"
            "2026-02-09 12:30:00,-500,,0,\n"
        )
        rows = transform(csv_data, source="switch")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertEqual(rows[1]["error_type"], "standby")
        self.assertEqual(rows[2]["error_type"], "warning")

    def test_solaxcloud_realtime_payload(self):
        payload = """
        {
          "success": true,
          "code": 0,
          "result": {
            "uploadTime": "2026-02-09 12:00:00",
            "acpower": 4200.0,
            "yieldtoday": 18.4,
            "inverterStatus": "102"
          }
        }
        """
        rows = transform(payload, source="solaxcloud")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertEqual(rows[0]["kWh"], 18.4)
        self.assertEqual(rows[0]["error_code"], "102")
        self.assertEqual(rows[0]["oem_error_code"], "0")

    def test_fimer_daily_series_payload(self):
        payload = """
        {
          "series": [
            {"date": "2026-02-08", "energy": 15000, "unit": "Wh"}
          ]
        }
        """
        rows = transform(payload, source="fimer")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertEqual(rows[0]["kWh"], 15.0)

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            transform("{}", source="not-a-real-source")


if __name__ == "__main__":
    unittest.main()

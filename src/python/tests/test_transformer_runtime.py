import unittest

from odse.transformer import transform
from odse.validator import validate


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

    def test_enphase_maps_wh_and_status_ratio(self):
        payload = """
        [
          {"end_at": 1739102400, "wh_del": 3500, "devices_reporting": 9}
        ]
        """
        rows = transform(payload, source="enphase", expected_devices=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kWh"], 3.5)
        self.assertEqual(rows[0]["error_type"], "warning")

    def test_enphase_offline_when_zero_devices(self):
        payload = """
        [
          {"end_at": 1739102400, "wh_del": 0, "devices_reporting": 0}
        ]
        """
        rows = transform(payload, source="enphase", expected_devices=12)
        self.assertEqual(rows[0]["error_type"], "offline")

    def test_solarman_generation_delta_and_state_mapping(self):
        csv_data = (
            "Update Time,Generation(kWh),Device State,Power(W)\n"
            "2026-02-09 12:00:00,100.0,Operating,500\n"
            "2026-02-09 12:05:00,100.6,Operating,600\n"
            "2026-02-09 12:10:00,100.6,Standby,0\n"
        )
        rows = transform(csv_data, source="solarman")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertAlmostEqual(rows[0]["kWh"], 0.0)
        self.assertAlmostEqual(rows[1]["kWh"], 0.6)
        self.assertEqual(rows[2]["error_type"], "standby")

    def test_solarman_fallback_infers_from_power(self):
        csv_data = (
            "Update Time,Generation(kWh),Power(W)\n"
            "2026-02-09 12:00:00,20.0,0\n"
            "2026-02-09 12:05:00,20.0,250\n"
        )
        rows = transform(csv_data, source="solarman")
        self.assertEqual(rows[0]["error_type"], "offline")
        self.assertEqual(rows[1]["error_type"], "normal")

    def test_solaredge_inverter_data_mapping(self):
        payload = """
        {
          "data": {
            "telemetries": [
              {
                "date": "2026-02-09 12:00:00",
                "totalActivePower": 5000,
                "inverterMode": "MPPT",
                "operationMode": 1,
                "L1Data": {
                  "apparentPower": 5200,
                  "reactivePower": 400,
                  "cosPhi": 0.96
                }
              }
            ]
          }
        }
        """
        rows = transform(payload, source="solaredge")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertEqual(rows[0]["error_code"], "1")
        self.assertAlmostEqual(rows[0]["kW"], 5.0)

    def test_fronius_power_flow_mapping(self):
        payload = """
        {
          "Head": {"Timestamp": "2026-02-09T12:00:00Z", "Status": {"Code": 0}},
          "Body": {"Data": {"Site": {"P_PV": 4200, "E_Day": 13500}}}
        }
        """
        rows = transform(payload, source="fronius")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertAlmostEqual(rows[0]["kW"], 4.2)
        self.assertAlmostEqual(rows[0]["kWh"], 13.5)

    def test_sma_normalized_mapping(self):
        payload = """
        {
          "records": [
            {
              "normalized": {
                "timestamp": "2026-02-09T12:00:00Z",
                "active_power_w": 3000,
                "active_energy_wh": 2500,
                "status_code": "ONLINE",
                "event_severity": "warning",
                "event_code": "E101"
              }
            }
          ]
        }
        """
        rows = transform(payload, source="sma")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "warning")
        self.assertEqual(rows[0]["error_code"], "E101")
        self.assertAlmostEqual(rows[0]["kWh"], 2.5)

    def test_solis_normalized_mapping(self):
        payload = """
        {
          "records": [
            {
              "normalized": {
                "timestamp": "2026-02-09T12:00:00Z",
                "active_power_w": 4600,
                "inverter_status": "running",
                "status_code": "200",
                "temperature_c": 41.2
              }
            }
          ]
        }
        """
        rows = transform(payload, source="solis")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "normal")
        self.assertEqual(rows[0]["error_code"], "200")
        self.assertAlmostEqual(rows[0]["kW"], 4.6)


class EnergyTimeseriesValidationTests(unittest.TestCase):
    """Tests for the extended energy-timeseries schema fields."""

    def _base_record(self, **overrides):
        record = {
            "timestamp": "2026-02-09T12:00:00Z",
            "kWh": 5.0,
            "error_type": "normal",
        }
        record.update(overrides)
        return record

    def test_generation_record_validates(self):
        """Existing generation records (no direction) still validate."""
        result = validate(self._base_record())
        self.assertTrue(result.is_valid)

    def test_explicit_generation_direction_validates(self):
        result = validate(self._base_record(direction="generation"))
        self.assertTrue(result.is_valid)

    def test_consumption_record_validates(self):
        result = validate(self._base_record(
            direction="consumption",
            end_use="whole_building",
        ))
        self.assertTrue(result.is_valid)

    def test_net_record_with_negative_kwh_validates(self):
        result = validate(self._base_record(
            direction="net",
            kWh=-3.2,
        ))
        self.assertTrue(result.is_valid)

    def test_negative_kwh_rejected_for_generation(self):
        result = validate(self._base_record(kWh=-1.0))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    def test_negative_kwh_rejected_for_consumption(self):
        result = validate(self._base_record(
            direction="consumption",
            kWh=-1.0,
        ))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    def test_invalid_direction_rejected(self):
        result = validate(self._base_record(direction="export"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_invalid_end_use_rejected(self):
        result = validate(self._base_record(end_use="teleportation"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_invalid_fuel_type_rejected(self):
        result = validate(self._base_record(fuel_type="antimatter"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_valid_fuel_type_accepted(self):
        result = validate(self._base_record(fuel_type="natural_gas"))
        self.assertTrue(result.is_valid)

    def test_end_use_with_fuel_type(self):
        result = validate(self._base_record(
            direction="consumption",
            end_use="heating",
            fuel_type="natural_gas",
        ))
        self.assertTrue(result.is_valid)

    def test_semantic_skips_capacity_check_for_consumption(self):
        result = validate(
            self._base_record(direction="consumption", kWh=500.0),
            level="semantic",
            capacity_kw=10.0,
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.warnings), 0)

    def test_semantic_capacity_check_still_applies_for_generation(self):
        result = validate(
            self._base_record(direction="generation", kWh=500.0),
            level="semantic",
            capacity_kw=10.0,
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].code, "EXCEEDS_PHYSICAL_MAXIMUM")


if __name__ == "__main__":
    unittest.main()

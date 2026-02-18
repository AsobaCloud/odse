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

    # --- Unchecked base fields ---

    def test_error_code_string_accepted(self):
        result = validate(self._base_record(error_code="E101"))
        self.assertTrue(result.is_valid)

    def test_error_code_non_string_rejected(self):
        result = validate(self._base_record(error_code=101))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    def test_kvarh_number_accepted(self):
        result = validate(self._base_record(kVArh=1.5))
        self.assertTrue(result.is_valid)

    def test_kvarh_non_number_rejected(self):
        result = validate(self._base_record(kVArh="bad"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    def test_kva_valid_accepted(self):
        result = validate(self._base_record(kVA=10.0))
        self.assertTrue(result.is_valid)

    def test_kva_negative_rejected(self):
        result = validate(self._base_record(kVA=-1.0))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    # --- Party IDs ---

    def test_valid_party_ids_accepted(self):
        result = validate(self._base_record(
            seller_party_id="nersa:gen:ABC001",
            buyer_party_id="nersa:offtaker:MUN042",
            network_operator_id="nersa:dso:eskom-tx",
            wheeling_agent_id="nersa:agent:wesco.1",
            balance_responsible_party_id="nersa:brp:BRP-01",
        ))
        self.assertTrue(result.is_valid)

    def test_invalid_seller_party_id_pattern_rejected(self):
        result = validate(self._base_record(seller_party_id="bad id!"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "PATTERN_MISMATCH")

    def test_invalid_buyer_party_id_pattern_rejected(self):
        result = validate(self._base_record(buyer_party_id="no-colons"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "PATTERN_MISMATCH")

    def test_party_id_non_string_rejected(self):
        result = validate(self._base_record(network_operator_id=123))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    # --- Settlement ---

    def test_valid_settlement_fields_accepted(self):
        result = validate(self._base_record(
            settlement_period_start="2026-02-09T00:00:00Z",
            settlement_period_end="2026-02-09T00:30:00Z",
            loss_factor=0.03,
            contract_reference="PPA-2026-001",
            settlement_type="bilateral",
        ))
        self.assertTrue(result.is_valid)

    def test_negative_loss_factor_rejected(self):
        result = validate(self._base_record(loss_factor=-0.01))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    def test_invalid_settlement_type_rejected(self):
        result = validate(self._base_record(settlement_type="spot"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_settlement_period_start_non_string_rejected(self):
        result = validate(self._base_record(settlement_period_start=12345))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    # --- Tariff ---

    def test_valid_tariff_fields_accepted(self):
        result = validate(self._base_record(
            tariff_schedule_id="nersa:capetown:RES01:v3",
            tariff_period="peak",
            tariff_currency="ZAR",
            tariff_version_effective_at="2026-01-01T00:00:00Z",
            energy_charge_component=1.85,
            network_charge_component=0.42,
        ))
        self.assertTrue(result.is_valid)

    def test_invalid_tariff_schedule_id_rejected(self):
        result = validate(self._base_record(tariff_schedule_id="bad-format"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "PATTERN_MISMATCH")

    def test_invalid_tariff_period_rejected(self):
        result = validate(self._base_record(tariff_period="super_peak"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_invalid_tariff_currency_rejected(self):
        result = validate(self._base_record(tariff_currency="zar"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "PATTERN_MISMATCH")

    def test_negative_energy_charge_rejected(self):
        result = validate(self._base_record(energy_charge_component=-0.5))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    def test_negative_network_charge_rejected(self):
        result = validate(self._base_record(network_charge_component=-1))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    # --- Granular charge components ---

    def test_valid_granular_charges_accepted(self):
        result = validate(self._base_record(
            generation_charge_component=0.50,
            transmission_charge_component=0.12,
            distribution_charge_component=0.30,
            ancillary_service_charge_component=0.05,
            non_bypassable_charge_component=0.02,
            environmental_levy_component=0.01,
        ))
        self.assertTrue(result.is_valid)

    def test_negative_generation_charge_rejected(self):
        result = validate(self._base_record(generation_charge_component=-0.1))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    def test_non_number_distribution_charge_rejected(self):
        result = validate(self._base_record(distribution_charge_component="free"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    def test_negative_environmental_levy_rejected(self):
        result = validate(self._base_record(environmental_levy_component=-0.01))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    # --- Wheeling ---

    def test_valid_wheeling_fields_accepted(self):
        result = validate(self._base_record(
            wheeling_type="virtual",
            wheeling_status="confirmed",
            injection_point_id="INJ-001",
            offtake_point_id="OFT-002",
            wheeling_path_id="WP-2026-001",
        ))
        self.assertTrue(result.is_valid)

    def test_invalid_wheeling_type_rejected(self):
        result = validate(self._base_record(wheeling_type="direct"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_invalid_wheeling_status_rejected(self):
        result = validate(self._base_record(wheeling_status="pending"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_wheeling_path_id_non_string_rejected(self):
        result = validate(self._base_record(wheeling_path_id=999))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    # --- Curtailment ---

    def test_valid_curtailment_fields_accepted(self):
        result = validate(self._base_record(
            curtailment_flag=True,
            curtailment_type="congestion",
            curtailed_kWh=2.5,
            curtailment_instruction_id="SO-INST-001",
        ))
        self.assertTrue(result.is_valid)

    def test_curtailment_flag_non_boolean_rejected(self):
        result = validate(self._base_record(curtailment_flag=1))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    def test_invalid_curtailment_type_rejected(self):
        result = validate(self._base_record(curtailment_type="economic"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_negative_curtailed_kwh_rejected(self):
        result = validate(self._base_record(curtailed_kWh=-1.0))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    # --- BRP / Imbalance ---

    def test_valid_brp_fields_accepted(self):
        result = validate(self._base_record(
            forecast_kWh=5.5,
            imbalance_kWh=-0.5,
        ))
        self.assertTrue(result.is_valid)

    def test_negative_imbalance_accepted(self):
        """imbalance_kWh can be negative (under-delivery)."""
        result = validate(self._base_record(imbalance_kWh=-3.0))
        self.assertTrue(result.is_valid)

    def test_forecast_kwh_non_number_rejected(self):
        result = validate(self._base_record(forecast_kWh="five"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    def test_imbalance_kwh_non_number_rejected(self):
        result = validate(self._base_record(imbalance_kWh=True))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    # --- Municipal billing ---

    def test_valid_billing_fields_accepted(self):
        result = validate(self._base_record(
            billing_period="2026-02",
            billed_kWh=150.0,
            billing_status="metered",
            daa_reference="DAA-2026-042",
        ))
        self.assertTrue(result.is_valid)

    def test_negative_billed_kwh_rejected(self):
        result = validate(self._base_record(billed_kWh=-10.0))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    def test_invalid_billing_status_rejected(self):
        result = validate(self._base_record(billing_status="pending"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_billing_period_non_string_rejected(self):
        result = validate(self._base_record(billing_period=202602))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")

    # --- Certificates ---

    def test_valid_certificate_fields_accepted(self):
        result = validate(self._base_record(
            renewable_attribute_id="IREC-ZA-2026-00001",
            certificate_standard="i_rec",
            verification_status="issued",
            carbon_intensity_gCO2_per_kWh=0.0,
        ))
        self.assertTrue(result.is_valid)

    def test_invalid_certificate_standard_rejected(self):
        result = validate(self._base_record(certificate_standard="gold_standard"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_invalid_verification_status_rejected(self):
        result = validate(self._base_record(verification_status="approved"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "ENUM_MISMATCH")

    def test_negative_carbon_intensity_rejected(self):
        result = validate(self._base_record(carbon_intensity_gCO2_per_kWh=-5.0))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "OUT_OF_BOUNDS")

    def test_carbon_intensity_non_number_rejected(self):
        result = validate(self._base_record(carbon_intensity_gCO2_per_kWh="low"))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, "TYPE_MISMATCH")


if __name__ == "__main__":
    unittest.main()

"""
Tests for industrial connectors mapping logic.
"""

import unittest
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies that might be missing
sys.modules['paho'] = MagicMock()
sys.modules['paho.mqtt'] = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()
sys.modules['jsonpath_ng'] = MagicMock()

import odse.connectors.mqtt  # noqa: E402
odse.connectors.mqtt.parse_jsonpath = None
from odse.connectors.mqtt import MQTTConnector  # noqa: E402

class TestMQTTMapping(unittest.TestCase):
    def setUp(self):
        self.config = {
            "broker": "localhost",
            "subscriptions": [
                {
                    "topic": "site/+/inv/+/telemetry",
                    "asset_id_template": "za:{0}:inv:{1}",
                    "mapping": {
                        "timestamp": "$.time",
                        "kWh": "$.energy",
                        "kW": "$.power",
                        "error_type": "$.status"
                    }
                }
            ]
        }
        self.connector = MQTTConnector(self.config)

    def test_asset_id_extraction(self):
        topic = "site/site-01/inv/inv-55/telemetry"
        sub = self.config["subscriptions"][0]
        asset_id = self.connector._extract_asset_id(topic, sub)
        self.assertEqual(asset_id, "za:site-01:inv:inv-55")

    def test_payload_mapping(self):
        payload = {
            "time": "2024-05-31T12:00:00Z",
            "energy": 1234.5,
            "power": 10.5,
            "status": "normal"
        }
        mapping = self.config["subscriptions"][0]["mapping"]
        record = self.connector._apply_mapping(payload, mapping)
        
        self.assertEqual(record["timestamp"], "2024-05-31T12:00:00+00:00")
        self.assertEqual(record["kWh"], 1234.5)
        self.assertEqual(record["kW"], 10.5)
        self.assertEqual(record["error_type"], "normal")

    def test_secret_resolution(self):
        with patch.dict('os.environ', {'MY_MQTT_USER': 'admin'}):
            config = {"auth": {"username": "${MY_MQTT_USER}"}}
            resolved = self.connector._resolve_secrets(config)
            self.assertEqual(resolved["auth"]["username"], "admin")

if __name__ == "__main__":
    unittest.main()

"""
MQTT Connector for ODS-E.

Subscribes to MQTT topics and maps JSON payloads to ODS-E records.
Supports topic-based asset ID extraction and JSONPath field mapping.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    from jsonpath_ng import parse as parse_jsonpath
except ImportError:
    parse_jsonpath = None

from ..validator import validate
from ..transformer import _to_iso8601, _to_float

logger = logging.getLogger(__name__)


class MQTTConnector:
    """
    Industrial MQTT connector for ODS-E.
    
    Handles connection, subscription, and mapping of MQTT messages.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connector with a configuration dictionary.
        
        Args:
            config: Connector configuration (broker, port, subscriptions, etc.)
        """
        if mqtt is None:
            raise ImportError(
                "paho-mqtt is required for MQTTConnector. "
                "Install with: pip install paho-mqtt"
            )
        
        self.config = self._resolve_secrets(config)
        self.client_id = self.config.get("client_id", "odse-ingest")
        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)
        
        # Configure authentication
        auth = self.config.get("auth", {})
        username = auth.get("username")
        password = auth.get("password")
        if username:
            self.client.username_pw_set(username, password)
            
        # Configure TLS
        tls = self.config.get("tls", {})
        if tls.get("enabled"):
            self.client.tls_set(
                ca_certs=tls.get("ca_certs"),
                certfile=tls.get("certfile"),
                keyfile=tls.get("keyfile")
            )

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self.subscriptions = self.config.get("subscriptions", [])
        self._last_msg_time = {} # asset_id -> timestamp
        self.on_record_callback = None

    def _resolve_secrets(self, config: Any) -> Any:
        """Recursively expand ${VAR} in config strings."""
        if isinstance(config, dict):
            return {k: self._resolve_secrets(v) for k, v in config.items()}
        if isinstance(config, list):
            return [self._resolve_secrets(v) for v in config]
        if isinstance(config, str):
            return re.sub(
                r"\$\{([^}]+)\}",
                lambda m: os.getenv(m.group(1), m.group(0)),
                config
            )
        return config

    def connect(self):
        """Connect to the MQTT broker."""
        broker = self.config.get("broker", "localhost")
        port = int(self.config.get("port", 1883))
        keepalive = int(self.config.get("keepalive", 60))
        
        logger.info(f"Connecting to MQTT broker {broker}:{port}...")
        self.client.connect(broker, port, keepalive)

    def run(self, forever: bool = True):
        """Start the MQTT loop."""
        if forever:
            self.client.loop_forever()
        else:
            self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            # Resubscribe on connect (standard paho practice)
            for sub in self.subscriptions:
                topic = sub.get("topic")
                if topic:
                    client.subscribe(topic, qos=sub.get("qos", 1))
                    logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects."""
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker (rc={rc}). Will attempt reconnect.")

    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to decode MQTT payload on {msg.topic}: {e}")
            return

        # Find matching subscription
        for sub in self.subscriptions:
            if mqtt.topic_matches_sub(sub["topic"], msg.topic):
                self._process_message(payload, msg.topic, sub)
                # If multiple subs match, we process all of them? 
                # Usually topics are specific enough.

    def _process_message(self, payload: Any, topic: str, sub: Dict[str, Any]):
        """Map payload to ODS-E record and validate."""
        mapping = sub.get("mapping", {})
        
        # 1. Extract Asset ID
        asset_id = self._extract_asset_id(topic, sub)
        if not asset_id:
            logger.warning(f"Could not resolve asset_id for topic {topic}")
            return

        # 2. Map fields
        record = self._apply_mapping(payload, mapping)
        record["asset_id"] = asset_id
        
        # 3. Ensure mandatory fields
        if "timestamp" not in record or not record["timestamp"]:
            record["timestamp"] = _to_iso8601(time.time())
        if "error_type" not in record:
            record["error_type"] = "normal"
            
        # 4. Validate
        result = validate(record)
        if not result.is_valid:
            logger.error(f"Invalid ODS-E record from {topic}: {result.errors}")
            return

        # 5. Handle record
        self._last_msg_time[asset_id] = time.time()
        if self.on_record_callback:
            self.on_record_callback(record)
        else:
            # Default: print to stdout for PoC
            print(json.dumps(record))

    def _extract_asset_id(self, topic: str, sub: Dict[str, Any]) -> Optional[str]:
        """Extract asset_id from topic segments using template."""
        template = sub.get("asset_id_template")
        if not template:
            return sub.get("mapping", {}).get("asset_id")
            
        # Split topic and sub topic to find wildcards
        topic_parts = topic.split("/")
        sub_parts = sub["topic"].split("/")
        
        wildcard_values = []
        for s_part, t_part in zip(sub_parts, topic_parts):
            if s_part in ("+", "#"):
                wildcard_values.append(t_part)
                
        try:
            return template.format(*wildcard_values)
        except (IndexError, KeyError) as e:
            logger.error(f"Failed to format asset_id_template '{template}' with values {wildcard_values}: {e}")
            return None

    def _apply_mapping(self, payload: Any, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply JSONPath mapping to payload."""
        record = {}
        for odse_field, path in mapping.items():
            if odse_field == "asset_id": # Handled separately
                continue
                
            if path.startswith("$."):
                value = self._query_jsonpath(payload, path)
            else:
                # Direct field access or literal
                value = payload.get(path) if isinstance(payload, dict) else None
                
            if value is not None:
                # Basic type coercion based on ODS-E expectations
                if odse_field in ("kWh", "kW", "voltage_ac", "current_ac", "frequency", "PF"):
                    record[odse_field] = _to_float(value)
                elif odse_field == "timestamp":
                    record[odse_field] = _to_iso8601(value)
                else:
                    record[odse_field] = value
                    
        return record

    def _query_jsonpath(self, payload: Any, path: str) -> Any:
        """Extract value using JSONPath."""
        if parse_jsonpath is None:
            # Fallback for simple top-level keys if jsonpath-ng is missing
            key = path[2:] if path.startswith("$.") else path
            return payload.get(key) if isinstance(payload, dict) else None
            
        try:
            jsonpath_expr = parse_jsonpath(path)
            matches = jsonpath_expr.find(payload)
            return matches[0].value if matches else None
        except Exception as e:
            logger.error(f"JSONPath query failed for {path}: {e}")
            return None

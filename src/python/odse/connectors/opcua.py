"""
OPC-UA Connector for ODS-E.

Monitors OPC-UA NodeIDs and aggregates changes into ODS-E records.
"""

import asyncio
import logging
import os
import re
import time
from typing import Any, Dict

try:
    from asyncua import Client, Node
except ImportError:
    Client = None

from ..validator import validate
from ..transformer import _to_iso8601, _to_float

logger = logging.getLogger(__name__)


class OPCUAConnector:
    """
    Industrial OPC-UA connector for ODS-E.
    
    Subscribes to NodeID changes and aggregates them by asset_id.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connector with a configuration dictionary.
        
        Args:
            config: Connector configuration (endpoint, nodes, etc.)
        """
        if Client is None:
            raise ImportError(
                "asyncua is required for OPCUAConnector. "
                "Install with: pip install asyncua"
            )
        
        self.config = self._resolve_secrets(config)
        self.url = self.config.get("endpoint") or self.config.get("url")
        self.nodes_config = self.config.get("nodes", [])
        
        # Internal state
        self._cache = {} # asset_id -> {field: value, timestamp: last_update}
        self.on_record_callback = None
        self._stop_event = asyncio.Event()

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

    async def run(self):
        """Start the OPC-UA subscription loop."""
        if not self.url:
            raise ValueError("OPC-UA endpoint URL is required")

        logger.info(f"Connecting to OPC-UA server at {self.url}...")
        
        while not self._stop_event.is_set():
            try:
                async with Client(url=self.url) as client:
                    logger.info("Connected to OPC-UA server successfully")
                    
                    # Create subscription
                    handler = SubscriptionHandler(self)
                    subscription = await client.create_subscription(1000, handler)
                    
                    # Map NodeIDs to their config
                    node_map = {}
                    nodes_to_subscribe = []
                    
                    for node_cfg in self.nodes_config:
                        node_id = node_cfg.get("node_id")
                        if not node_id:
                            continue
                        node = client.get_node(node_id)
                        nodes_to_subscribe.append(node)
                        node_map[node_id] = node_cfg
                        
                    # Subscribe to data changes
                    await subscription.subscribe_data_change(nodes_to_subscribe)
                    logger.info(f"Subscribed to {len(nodes_to_subscribe)} OPC-UA nodes")
                    
                    # Wait for stop event or connection loss
                    while not self._stop_event.is_set():
                        await asyncio.sleep(1)
                        
            except (asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.error(f"OPC-UA connection error: {e}. Retrying in 10s...")
                await asyncio.sleep(10)

    def stop(self):
        """Stop the connector."""
        self._stop_event.set()

    def _handle_data_change(self, node: Node, val: Any, data: Any):
        """Handle a data change event from a subscribed node."""
        node_id = str(node.nodeid)
        
        # Find node config
        node_cfg = None
        for cfg in self.nodes_config:
            if cfg.get("node_id") == node_id:
                node_cfg = cfg
                break
                
        if not node_cfg:
            return

        asset_id = node_cfg.get("asset_id")
        field = node_cfg.get("field") or node_cfg.get("ods_e_field")
        
        if not asset_id or not field:
            return

        # Update cache
        if asset_id not in self._cache:
            self._cache[asset_id] = {"asset_id": asset_id, "timestamp": _to_iso8601(time.time())}
            
        # Type coercion
        if field in ("kWh", "kW", "voltage_ac", "current_ac", "frequency", "PF"):
            val = _to_float(val)
            
        self._cache[asset_id][field] = val
        self._cache[asset_id]["timestamp"] = _to_iso8601(time.time())
        
        # If we have the mandatory fields for a record, or enough fields, emit it
        # In a real system, we might wait for a "complete" set or emit periodically
        self._maybe_emit_record(asset_id)

    def _maybe_emit_record(self, asset_id: str):
        """Decide whether to emit an ODS-E record for the asset."""
        cached = self._cache.get(asset_id)
        if not cached:
            return

        # Mandatory fields for ODS-E
        if "kWh" not in cached:
            # For PoC, we only emit if we have at least energy
            return

        record = cached.copy()
        if "error_type" not in record:
            record["error_type"] = "normal"

        # Validate
        result = validate(record)
        if result.is_valid:
            if self.on_record_callback:
                self.on_record_callback(record)
            else:
                import json
                print(json.dumps(record))


class SubscriptionHandler:
    """Handle OPC-UA subscription events."""

    def __init__(self, connector: OPCUAConnector):
        self.connector = connector

    def datachange_notification(self, node: Node, val: Any, data: Any):
        """Callback for data change notifications."""
        self.connector._handle_data_change(node, val, data)

    def event_notification(self, event: Any):
        """Callback for event notifications."""
        pass

    def status_change_notification(self, status: Any):
        """Callback for status change notifications."""
        logger.info(f"OPC-UA status change: {status}")

# Industrial Protocol Integration: MQTT & OPC-UA

This specification defines how ODS-E (Open Data Schema for Energy) integrates with industrial telemetry protocols, specifically MQTT and OPC-UA, to enable real-time energy data ingestion.

## 1. Overview

Industrial energy assets (Inverters, Meters, Transformers) often communicate via local protocols (Modbus, IEC 61850) which are aggregated by an Edge Gateway. These gateways typically republish data using **MQTT** (pub/sub) or **OPC-UA** (client/server) for upstream consumption.

ODS-E provides a standardized way to map these heterogeneous streams into the canonical ODS-E record format.

## 2. MQTT Integration

MQTT integration focuses on subscribing to JSON-encoded telemetry streams.

### 2.1 Topic-to-Asset Mapping
Topics often contain asset identifiers in their structure (e.g., `factory-01/inverter-55/telemetry`). ODS-E uses a template-based mapping to extract these.

- **Topic**: `site/{site_id}/inv/{inv_id}/data`
- **Asset ID Template**: `za:{site_id}:inv:{inv_id}`

### 2.2 Payload Mapping (JSONPath)
Since JSON structures vary by OEM or Gateway, ODS-E uses JSONPath for field extraction.

| ODS-E Field | JSONPath Example | Description |
| :--- | :--- | :--- |
| `timestamp` | `$.ts` | ISO8601 string or Unix epoch |
| `kWh` | `$.metrics.energy_total` | Cumulative active energy |
| `kW` | `$.metrics.power_active` | Real-time active power |
| `error_type`| `$.status.level` | Mapped to ODS-E enum |

### 2.3 Configuration Schema
```yaml
connector:
  type: mqtt
  broker: "mqtt.local"
  subscriptions:
    - topic: "energy/meters/+/status"
      mapping:
        asset_id: "meter:{1}" # Segment 1 from topic
        kWh: "$.val"
        error_type: "$.state"
```

## 3. OPC-UA Integration

OPC-UA integration focuses on monitoring specific **NodeIDs** and aggregating them into records.

### 3.1 Node Grouping
Unlike MQTT, OPC-UA data is often flat. ODS-E groups NodeIDs by `asset_id`.

| NodeID | ODS-E Field | Asset ID |
| :--- | :--- | :--- |
| `ns=2;s=Inv1.P` | `kW` | `site:inv-1` |
| `ns=2;s=Inv1.E` | `kWh` | `site:inv-1` |
| `ns=2;s=Inv2.P` | `kW` | `site:inv-2` |

### 3.2 Sampling and Reporting
ODS-E can either:
1.  **Report on Change**: Create a record whenever a mapped NodeID changes.
2.  **Sampled Interval**: Collect the latest values for all nodes in a group every N seconds and emit a single record.

### 3.3 Configuration Schema
```yaml
connector:
  type: opcua
  endpoint: "opc.tcp://192.168.1.50:4840"
  nodes:
    - node_id: "ns=2;s=Device1.ActivePower"
      asset_id: "factory:dev1"
      field: "kW"
    - node_id: "ns=2;s=Device1.Energy"
      asset_id: "factory:dev1"
      field: "kWh"
```

## 4. Real-Life Robustness

To be usable in industrial environments, the connectors must handle more than just "happy path" data.

### 4.1 Resilience & Connectivity
- **Automatic Retries**: Both MQTT and OPC-UA clients must implement exponential backoff for reconnections.
- **Session Persistence**: Use MQTT "Clean Session = False" and persistent ClientIDs to ensure no messages are lost during brief broker outages.
- **Watchdog**: A background task should monitor the age of the "last received message" per asset and emit an ODS-E record with `error_type: "offline"` if data stalls.

### 4.2 Security
- **Secret Management**: Configuration files MUST NOT store plain-text passwords. Use `${ENV_VAR}` syntax for broker/server credentials.
- **TLS/SSL**: Mandatory support for encrypted connections and certificate-based authentication.

### 4.3 Advanced Mapping (Transformations)
Raw industrial data often needs pre-processing before it matches ODS-E requirements:
- **Scaling**: Multiply raw integers by a factor (e.g., `scale: 0.1` for 100 -> 10.0 kW).
- **Unit Conversion**: Support for converting `W` to `kW` or `Wh` to `kWh` inline.
- **Deadbanding**: (OPC-UA) Only emit a record if the value changes by more than a certain threshold to reduce noise.

## 5. Ingestion Pipeline

The `odse ingest` command runs as a long-lived process:

1.  **Connect**: Establish connection to the broker/server.
2.  **Subscribe**: Listen for changes on mapped topics/nodes.
3.  **Map**: Transform the incoming raw data into an ODS-E record.
4.  **Validate**: Run `odse.validator` on the record.
5.  **Sink**: Append to JSONL, publish to a message queue, or write to a database.

"""
ODS-E Transformer

Transforms OEM-specific data formats to ODS-E schema.
"""

import csv
import json
import math
from datetime import datetime, timezone as dt_timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union


def transform(
    data: Union[str, Path],
    source: str,
    asset_id: Optional[str] = None,
    timezone: Optional[str] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Transform OEM data to ODS-E format.

    Args:
        data: Path to data file or data string
        source: OEM source identifier (e.g., "huawei", "enphase", "solarman")
        asset_id: Optional asset identifier to include in output
        timezone: Optional timezone for timestamp conversion

    Returns:
        List of ODS-E formatted records
    """
    transformer = _get_transformer(source)
    return transformer.transform(
        data,
        asset_id=asset_id,
        timezone=timezone,
        **kwargs,
    )


def transform_stream(
    data: Union[str, Path],
    source: str,
    **kwargs,
) -> Iterator[Dict[str, Any]]:
    """
    Stream transform OEM data to ODS-E format.

    Useful for large files where loading all records into memory
    is not practical.

    Args:
        data: Path to data file
        source: OEM source identifier
        **kwargs: Additional arguments passed to transformer

    Yields:
        ODS-E formatted records one at a time
    """
    transformer = _get_transformer(source)
    yield from transformer.transform_stream(data, **kwargs)


def _get_transformer(source: str):
    """Get the appropriate transformer for the source."""
    transformers = {
        "huawei": HuaweiTransformer(),
        "enphase": EnphaseTransformer(),
        "solarman": SolarmanTransformer(),
        "switch": SwitchTransformer(),
        "solaxcloud": SolaxCloudTransformer(),
        "solax": SolaxCloudTransformer(),
        "fimer": FimerTransformer(),
        "auroravision": FimerTransformer(),
        "solaredge": SolarEdgeTransformer(),
        "fronius": FroniusTransformer(),
        "sma": SMATransformer(),
        "solis": SolisTransformer(),
        "soliscloud": SolisTransformer(),
    }

    source_lower = source.lower()
    if source_lower not in transformers:
        raise ValueError(
            f"Unknown source '{source}'. "
            f"Supported sources: {list(transformers.keys())}"
        )

    return transformers[source_lower]


class BaseTransformer:
    """Base class for OEM transformers."""

    def transform(
        self,
        data: Union[str, Path],
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Transform data to ODS-E format."""
        raise NotImplementedError

    def transform_stream(
        self,
        data: Union[str, Path],
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """Stream transform data to ODS-E format."""
        # Default implementation: yield from transform()
        yield from self.transform(data, **kwargs)

    def _parse_json(self, data: Union[str, Path]) -> Any:
        """Parse JSON from a file path or JSON string."""
        if isinstance(data, Path):
            with data.open("r", encoding="utf-8") as f:
                return json.load(f)

        file_path = _resolve_existing_path(data)
        if file_path:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)

        return json.loads(data)

    def _parse_csv_rows(self, data: Union[str, Path]) -> List[Dict[str, Any]]:
        """Parse CSV rows from a file path or CSV string."""
        if isinstance(data, Path):
            text = data.read_text(encoding="utf-8")
        else:
            file_path = _resolve_existing_path(data)
            text = (
                file_path.read_text(encoding="utf-8")
                if file_path
                else str(data)
            )

        return list(csv.DictReader(StringIO(text)))


class HuaweiTransformer(BaseTransformer):
    """Transform Huawei FusionSolar data to ODS-E."""

    ERROR_CODES = {
        "normal": [0, 1, 2, 3, 256, 512, 1025, 1026, 1280, 1281, 1536, 1792, 2048, 2304, 40960, 49152],
        "warning": [513, 514, 772, 773, 774],
        "critical": [768, 770, 771, 45056],
        "fault": [769, 1024],
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0
        asset_id = kwargs.get("asset_id")
        timezone = kwargs.get("timezone")

        records: List[Dict[str, Any]] = []
        for row in rows:
            timestamp = _first_value(
                row,
                ["timestamp", "Time", "Timestamp", "time"],
            )
            iso_ts = _to_iso8601(timestamp, timezone=timezone)
            if not iso_ts:
                continue

            power_kw = _to_float(
                _first_value(row, ["power", "Active Power(kW)", "Power", "power_kw"])
            )
            inverter_state = _to_int(
                _first_value(row, ["inverter_state", "Inverter State", "State", "status"])
            )
            run_state = _to_int(_first_value(row, ["run_state", "Running State", "Run State"]))

            record: Dict[str, Any] = {
                "timestamp": iso_ts,
                "kWh": max((power_kw or 0.0) * interval_hours, 0.0),
                "error_type": self._map_error_code(inverter_state, run_state),
                "error_code": "unknown" if inverter_state is None else str(inverter_state),
            }
            if asset_id:
                record["asset_id"] = asset_id
            records.append(record)

        return records

    def _map_error_code(self, code: Optional[int], run_state: Optional[int] = None) -> str:
        if run_state == 0:
            return "offline"
        if code is None:
            return "unknown"
        for error_type, codes in self.ERROR_CODES.items():
            if code in codes:
                return error_type
        return "unknown"


class EnphaseTransformer(BaseTransformer):
    """Transform Enphase Envoy data to ODS-E."""

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        expected_devices = kwargs.get("expected_devices")
        asset_id = kwargs.get("asset_id")

        if isinstance(payload, dict):
            items = payload.get("production") if isinstance(payload.get("production"), list) else [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        records: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            end_at = _to_float(item.get("end_at"))
            wh_del = _to_float(item.get("wh_del"))
            timestamp = _to_iso8601(end_at)
            if timestamp is None or wh_del is None:
                continue

            devices_reporting = _to_int(item.get("devices_reporting"))
            error_type = self._derive_status(
                devices_reporting=devices_reporting,
                expected_devices=expected_devices,
            )

            record: Dict[str, Any] = {
                "timestamp": timestamp,
                "kWh": max(wh_del / 1000.0, 0.0),
                "error_type": error_type,
            }
            if asset_id:
                record["asset_id"] = asset_id
            records.append(record)

        return records

    @staticmethod
    def _derive_status(
        *,
        devices_reporting: Optional[int],
        expected_devices: Optional[int],
    ) -> str:
        if devices_reporting is None:
            return "offline"
        if expected_devices is None or expected_devices <= 0:
            if devices_reporting == 0:
                return "offline"
            return "normal"

        ratio = devices_reporting / float(expected_devices)
        if ratio >= 0.95:
            return "normal"
        if ratio >= 0.80:
            return "warning"
        if devices_reporting > 0:
            return "critical"
        return "offline"


class SolarmanTransformer(BaseTransformer):
    """Transform Solarman Logger data to ODS-E."""

    STATE_MAPPING = {
        "Normal": "normal",
        "Operating": "normal",
        "Warning": "warning",
        "Fault": "fault",
        "Error": "fault",
        "Offline": "offline",
        "Standby": "standby",
        "Degraded": "warning",
        "Disconnected": "offline",
        "No Data": "offline",
        "Idle": "standby",
        "Waiting": "standby",
        "Online": "normal",
        "1": "normal",
        "0": "offline",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        timezone = kwargs.get("timezone")
        asset_id = kwargs.get("asset_id")
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0

        records: List[Dict[str, Any]] = []
        prev_generation: Optional[float] = None

        for row in rows:
            timestamp_raw = _first_value(row, ["update_time", "Update Time", "Time", "Timestamp"])
            timestamp = _to_iso8601(timestamp_raw, timezone=timezone)
            if not timestamp:
                continue

            generation = _to_float(
                _first_value(row, ["generation", "Generation(kWh)", "Total Generation", "Cumulative Energy"])
            )
            generation_missing = generation is None
            if generation_missing:
                continue

            if prev_generation is None:
                kwh = 0.0
            else:
                kwh = max(generation - prev_generation, 0.0)
            prev_generation = generation

            device_state_raw = _first_value(row, ["device_state", "Device State", "Status", "State"])
            power_w = _to_float(_first_value(row, ["power", "Power(W)", "Active Power", "Output Power"]))
            error_type = self._map_state(device_state_raw, power_w)

            record: Dict[str, Any] = {
                "timestamp": timestamp,
                "kWh": kwh,
                "error_type": error_type,
                "error_code": str(device_state_raw) if device_state_raw not in (None, "") else "inferred",
            }
            if power_w is not None:
                record["kW"] = power_w / 1000.0
                if generation_missing and power_w > 0:
                    record["kWh"] = (power_w / 1000.0) * interval_hours
            if asset_id:
                record["asset_id"] = asset_id
            records.append(record)

        return records

    def _map_state(self, device_state: Optional[Any], power_w: Optional[float]) -> str:
        if device_state is not None:
            state_key = str(device_state).strip()
            if state_key in self.STATE_MAPPING:
                return self.STATE_MAPPING[state_key]
            state_title = state_key.title()
            if state_title in self.STATE_MAPPING:
                return self.STATE_MAPPING[state_title]

        if power_w is None:
            return "unknown"
        if power_w > 0:
            return "normal"
        if power_w == 0:
            return "offline"
        return "warning"


class SwitchTransformer(BaseTransformer):
    """Transform Switch meter CSV data to ODS-E."""

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        interval_hours = (kwargs.get("interval_minutes", 15) or 15) / 60.0
        asset_id = kwargs.get("asset_id")
        timezone = kwargs.get("timezone")

        records: List[Dict[str, Any]] = []
        for row in rows:
            timestamp = _first_value(row, ["timestampISO", "timestamp", "Time", "Date/Time"])
            iso_ts = _to_iso8601(timestamp, timezone=timezone)
            if not iso_ts:
                continue

            d_p1 = _to_float(row.get("dP1"))
            d_p2 = _to_float(row.get("dP2"))
            d_q1 = _to_float(row.get("dQ1"))
            d_q2 = _to_float(row.get("dQ2"))

            power_w = d_p1 if d_p1 is not None else d_p2
            reactive_w = d_q1 if d_q1 is not None else d_q2

            p_kw = (power_w or 0.0) / 1000.0
            q_kvar = (reactive_w or 0.0) / 1000.0
            kva = math.sqrt((p_kw**2) + (q_kvar**2)) if (power_w is not None or reactive_w is not None) else None
            pf = (p_kw / kva) if kva and kva > 0 else None

            record: Dict[str, Any] = {
                "timestamp": iso_ts,
                "kWh": max(p_kw * interval_hours, 0.0),
                "error_type": self._map_switch_error(power_w),
                "error_code": _switch_error_code(power_w),
            }
            if reactive_w is not None:
                record["kVArh"] = q_kvar * interval_hours
            if kva is not None:
                record["kVA"] = kva
            if pf is not None:
                record["PF"] = max(0.0, min(1.0, pf))
            if asset_id:
                record["asset_id"] = asset_id

            records.append(record)

        return records

    @staticmethod
    def _map_switch_error(power: Optional[float]) -> str:
        if power is None:
            return "unknown"
        if power == 0:
            return "standby"
        if power > 0:
            return "normal"
        return "warning"


class SolaxCloudTransformer(BaseTransformer):
    """Transform SolaXCloud API v2 JSON payloads to ODS-E."""

    STATUS_MAPPING = {
        "100": "standby",
        "101": "standby",
        "102": "normal",
        "103": "warning",
        "104": "fault",
        "105": "warning",
        "106": "standby",
        "107": "warning",
        "108": "standby",
        "109": "standby",
        "110": "standby",
        "111": "standby",
        "112": "standby",
        "113": "warning",
        "114": "standby",
        "130": "warning",
        "131": "normal",
        "132": "warning",
        "133": "warning",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0
        asset_id = kwargs.get("asset_id")

        results: List[Dict[str, Any]] = []
        records = _extract_solax_records(payload)
        for rec in records:
            timestamp = _to_iso8601(
                rec.get("uploadTime") or rec.get("timestamp"),
                timezone=timezone,
            )
            if not timestamp:
                continue

            ac_power_w = _to_float(rec.get("acpower"))
            yield_today = _to_float(rec.get("yieldtoday"))
            kwh = yield_today if yield_today is not None else max(((ac_power_w or 0.0) / 1000.0) * interval_hours, 0.0)

            status_code = str(rec.get("inverterStatus")) if rec.get("inverterStatus") is not None else None
            error_type = self.STATUS_MAPPING.get(status_code or "", "unknown")
            record: Dict[str, Any] = {
                "timestamp": timestamp,
                "kWh": kwh,
                "error_type": error_type,
                "error_code": status_code or "unknown",
            }

            if ac_power_w is not None:
                record["kW"] = ac_power_w / 1000.0
            if payload.get("code") is not None and isinstance(payload, dict):
                record["oem_error_code"] = str(payload.get("code"))
            if asset_id:
                record["asset_id"] = asset_id
            results.append(record)

        return results


class FimerTransformer(BaseTransformer):
    """Transform FIMER Aurora Vision payloads to ODS-E."""

    STATUS_MAPPING = {
        "OK": "normal",
        "ONLINE": "normal",
        "RUNNING": "normal",
        "WARNING": "warning",
        "DEGRADED": "warning",
        "FAULT": "fault",
        "ERROR": "fault",
        "OFFLINE": "offline",
        "DISCONNECTED": "offline",
        "STANDBY": "standby",
        "SLEEP": "standby",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 15) or 15) / 60.0
        asset_id = kwargs.get("asset_id")

        output: List[Dict[str, Any]] = []

        if isinstance(payload, dict) and isinstance(payload.get("series"), list):
            for entry in payload["series"]:
                timestamp = _to_iso8601(entry.get("date"), timezone=timezone)
                if not timestamp:
                    continue
                energy = _normalize_energy_to_kwh(entry.get("energy"), entry.get("unit"))
                output.append(
                    _base_record(
                        timestamp=timestamp,
                        kwh=energy if energy is not None else 0.0,
                        error_type="normal",
                        error_code=None,
                        asset_id=asset_id,
                    )
                )
            return output

        if isinstance(payload, dict) and isinstance(payload.get("points"), list):
            for entry in payload["points"]:
                timestamp = _to_iso8601(entry.get("timestamp"), timezone=timezone)
                if not timestamp:
                    continue
                value = _to_float(entry.get("value"))
                kwh = max(((value or 0.0) / 1000.0) * interval_hours, 0.0)
                output.append(
                    _base_record(
                        timestamp=timestamp,
                        kwh=kwh,
                        error_type="normal",
                        error_code=None,
                        asset_id=asset_id,
                    )
                )
            return output

        if isinstance(payload, dict):
            timestamp = _to_iso8601(
                payload.get("lastReportedTimestamp") or payload.get("timestamp"),
                timezone=timezone,
            )
            if timestamp:
                status = str(payload.get("status", "unknown")).upper()
                output.append(
                    _base_record(
                        timestamp=timestamp,
                        kwh=0.0,
                        error_type=self.STATUS_MAPPING.get(status, "unknown"),
                        error_code=payload.get("message") or status,
                        asset_id=asset_id,
                    )
                )

        return output


class SolarEdgeTransformer(BaseTransformer):
    """Transform SolarEdge monitoring payloads to ODS-E."""

    MODE_MAPPING = {
        "MPPT": "normal",
        "ON": "normal",
        "PRODUCTION": "normal",
        "OFF": "offline",
        "SLEEPING": "standby",
        "STARTING": "standby",
        "SHUTTING_DOWN": "standby",
        "STANDBY": "standby",
        "FAULT": "fault",
        "ERROR": "fault",
        "MAINTENANCE": "warning",
        "LOCKED_GRID": "warning",
        "LOCKED_INTERNAL": "warning",
        "NIGHT_MODE": "standby",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 15) or 15) / 60.0
        asset_id = kwargs.get("asset_id")

        out: List[Dict[str, Any]] = []
        if isinstance(payload, dict) and isinstance(payload.get("data", {}).get("telemetries"), list):
            for t in payload["data"]["telemetries"]:
                ts = _to_iso8601(t.get("date"), timezone=timezone)
                if not ts:
                    continue
                power_w = _to_float(t.get("totalActivePower"))
                kwh = max(((power_w or 0.0) / 1000.0) * interval_hours, 0.0)
                mode = str(t.get("inverterMode") or "").upper()
                rec = _base_record(
                    timestamp=ts,
                    kwh=kwh,
                    error_type=self.MODE_MAPPING.get(mode, "unknown"),
                    error_code=t.get("operationMode"),
                    asset_id=asset_id,
                )
                if power_w is not None:
                    rec["kW"] = power_w / 1000.0
                l1 = t.get("L1Data", {}) if isinstance(t.get("L1Data"), dict) else {}
                for src_key, dst_key, scale in [
                    ("apparentPower", "kVA", 1000.0),
                    ("reactivePower", "kVAr", 1000.0),
                    ("cosPhi", "PF", None),
                    ("acVoltage", "voltage_ac", None),
                    ("acCurrent", "current_ac", None),
                    ("acFrequency", "frequency", None),
                ]:
                    val = _to_float(l1.get(src_key))
                    if val is not None:
                        rec[dst_key] = (val / scale) if scale else val
                out.append(rec)
            return out

        if isinstance(payload, dict) and isinstance(payload.get("energy", {}).get("values"), list):
            for v in payload["energy"]["values"]:
                ts = _to_iso8601(v.get("date"), timezone=timezone)
                val = _to_float(v.get("value"))
                if ts and val is not None:
                    out.append(
                        _base_record(
                            timestamp=ts,
                            kwh=max(val / 1000.0, 0.0),
                            error_type="normal",
                            error_code=None,
                            asset_id=asset_id,
                        )
                    )
            return out

        if isinstance(payload, dict) and isinstance(payload.get("power", {}).get("values"), list):
            for v in payload["power"]["values"]:
                ts = _to_iso8601(v.get("date"), timezone=timezone)
                val = _to_float(v.get("value"))
                if not ts:
                    continue
                kwh = max(((val or 0.0) / 1000.0) * interval_hours, 0.0)
                rec = _base_record(
                    timestamp=ts,
                    kwh=kwh,
                    error_type="normal" if (val or 0) > 0 else "standby",
                    error_code=None,
                    asset_id=asset_id,
                )
                if val is not None:
                    rec["kW"] = val / 1000.0
                out.append(rec)
            return out

        return out


class FroniusTransformer(BaseTransformer):
    """Transform Fronius local Solar API payloads to ODS-E."""

    STATUS_CODE_MAPPING = {
        0: "normal",
        1: "normal",
        2: "normal",
        3: "normal",
        4: "normal",
        5: "normal",
        6: "normal",
        7: "standby",
        8: "standby",
        9: "fault",
        10: "offline",
        11: "warning",
        12: "warning",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0
        asset_id = kwargs.get("asset_id")

        if not isinstance(payload, dict):
            return []

        head = payload.get("Head", {}) if isinstance(payload.get("Head"), dict) else {}
        body = payload.get("Body", {}) if isinstance(payload.get("Body"), dict) else {}
        data_block = body.get("Data", {}) if isinstance(body.get("Data"), dict) else {}
        ts = _to_iso8601(head.get("Timestamp"), timezone=timezone)
        if not ts:
            return []

        if isinstance(data_block.get("Site"), dict):
            site = data_block["Site"]
            p_pv = _to_float(site.get("P_PV"))
            e_day = _to_float(site.get("E_Day"))
            status_code = _to_int(head.get("Status", {}).get("Code") if isinstance(head.get("Status"), dict) else None)
            rec = _base_record(
                timestamp=ts,
                kwh=max((e_day or ((p_pv or 0.0) * interval_hours)) / 1000.0, 0.0),
                error_type="normal" if (status_code in (None, 0)) else "warning",
                error_code=status_code,
                asset_id=asset_id,
            )
            if p_pv is not None:
                rec["kW"] = p_pv / 1000.0
            return [rec]

        if "PAC" in data_block:
            pac = _to_float(_deep_get(data_block, ["PAC", "Value"]))
            sac = _to_float(_deep_get(data_block, ["SAC", "Value"]))
            day_energy = _to_float(_deep_get(data_block, ["DAY_ENERGY", "Value"]))
            status_code = _to_int(_deep_get(data_block, ["DeviceStatus", "StatusCode"]))
            error_code = _deep_get(data_block, ["DeviceStatus", "ErrorCode"])
            rec = _base_record(
                timestamp=ts,
                kwh=max((day_energy or ((pac or 0.0) * interval_hours)) / 1000.0, 0.0),
                error_type=self.STATUS_CODE_MAPPING.get(status_code or -1, "unknown"),
                error_code=error_code,
                asset_id=asset_id,
            )
            if pac is not None:
                rec["kW"] = pac / 1000.0
            if sac is not None:
                rec["kVA"] = sac / 1000.0
                if pac is not None and sac > 0:
                    rec["PF"] = max(0.0, min(1.0, pac / sac))
            return [rec]

        if isinstance(data_block.get("PowerReal_P_Sum"), (int, float)):
            p = _to_float(data_block.get("PowerReal_P_Sum"))
            s = _to_float(data_block.get("PowerApparent_S_Sum"))
            q = _to_float(data_block.get("PowerReactive_Q_Sum"))
            e = _to_float(data_block.get("EnergyReal_WAC_Sum_Produced"))
            pf = _to_float(data_block.get("PowerFactor_Sum"))
            rec = _base_record(
                timestamp=ts,
                kwh=max((e or ((p or 0.0) * interval_hours)) / 1000.0, 0.0),
                error_type="normal",
                error_code=None,
                asset_id=asset_id,
            )
            if p is not None:
                rec["kW"] = p / 1000.0
            if s is not None:
                rec["kVA"] = s / 1000.0
            if q is not None:
                rec["kVAr"] = q / 1000.0
            if pf is not None:
                rec["PF"] = max(0.0, min(1.0, pf))
            return [rec]

        return []


class SMATransformer(BaseTransformer):
    """Transform normalized SMA monitoring records to ODS-E."""

    SEVERITY_MAPPING = {
        "INFO": "normal",
        "WARNING": "warning",
        "MINOR": "warning",
        "MAJOR": "critical",
        "CRITICAL": "fault",
        "FAULT": "fault",
    }
    STATUS_FALLBACK = {
        "ONLINE": "normal",
        "RUNNING": "normal",
        "STANDBY": "standby",
        "OFFLINE": "offline",
        "ERROR": "fault",
        "UNKNOWN": "unknown",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        asset_id = kwargs.get("asset_id")
        records_in = _extract_records(payload)

        out: List[Dict[str, Any]] = []
        for r in records_in:
            normalized = r.get("normalized") if isinstance(r.get("normalized"), dict) else r
            ts = _to_iso8601(normalized.get("timestamp"), timezone=timezone)
            if not ts:
                continue

            p_w = _to_float(normalized.get("active_power_w"))
            e_wh = _to_float(normalized.get("active_energy_wh"))
            q_var = _to_float(normalized.get("reactive_power_var"))
            s_va = _to_float(normalized.get("apparent_power_va"))
            sev = str(normalized.get("event_severity") or "").upper()
            status = str(normalized.get("status_code") or "").upper()
            error_type = self.SEVERITY_MAPPING.get(sev, self.STATUS_FALLBACK.get(status, "unknown"))

            rec = _base_record(
                timestamp=ts,
                kwh=max((e_wh or 0.0) / 1000.0, 0.0),
                error_type=error_type,
                error_code=normalized.get("event_code") or normalized.get("status_code"),
                asset_id=asset_id,
            )
            if p_w is not None:
                rec["kW"] = p_w / 1000.0
            if q_var is not None:
                rec["kVAr"] = q_var / 1000.0
            if s_va is not None:
                rec["kVA"] = s_va / 1000.0
            if (p_w is not None) and (s_va is not None) and s_va > 0:
                rec["PF"] = max(0.0, min(1.0, p_w / s_va))
            for src, dst in [
                ("voltage_v", "voltage_ac"),
                ("current_a", "current_ac"),
                ("frequency_hz", "frequency"),
            ]:
                val = _to_float(normalized.get(src))
                if val is not None:
                    rec[dst] = val
            out.append(rec)
        return out


class SolisTransformer(BaseTransformer):
    """Transform normalized SolisCloud records to ODS-E."""

    STATUS_MAPPING = {
        "NORMAL": "normal",
        "RUNNING": "normal",
        "WARNING": "warning",
        "ALARM": "warning",
        "FAULT": "fault",
        "ERROR": "fault",
        "OFFLINE": "offline",
        "STANDBY": "standby",
        "SLEEP": "standby",
        "UNKNOWN": "unknown",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0
        asset_id = kwargs.get("asset_id")
        records_in = _extract_records(payload)

        out: List[Dict[str, Any]] = []
        for r in records_in:
            normalized = r.get("normalized") if isinstance(r.get("normalized"), dict) else r
            ts = _to_iso8601(normalized.get("timestamp"), timezone=timezone)
            if not ts:
                continue

            p_w = _to_float(normalized.get("active_power_w"))
            e_wh = _to_float(normalized.get("active_energy_wh"))
            q_var = _to_float(normalized.get("reactive_power_var"))
            s_va = _to_float(normalized.get("apparent_power_va"))
            status = str(
                normalized.get("inverter_status")
                or normalized.get("status_code")
                or "UNKNOWN"
            ).upper()

            kwh = (e_wh / 1000.0) if e_wh is not None else max(((p_w or 0.0) / 1000.0) * interval_hours, 0.0)
            rec = _base_record(
                timestamp=ts,
                kwh=kwh,
                error_type=self.STATUS_MAPPING.get(status, "unknown"),
                error_code=normalized.get("status_code") or normalized.get("inverter_status"),
                asset_id=asset_id,
            )
            if p_w is not None:
                rec["kW"] = p_w / 1000.0
            if q_var is not None:
                rec["kVAr"] = q_var / 1000.0
            if s_va is not None:
                rec["kVA"] = s_va / 1000.0
            if (p_w is not None) and (s_va is not None) and s_va > 0:
                rec["PF"] = max(0.0, min(1.0, p_w / s_va))
            for src, dst in [
                ("voltage_v", "voltage_ac"),
                ("current_a", "current_ac"),
                ("frequency_hz", "frequency"),
                ("temperature_c", "temperature"),
            ]:
                val = _to_float(normalized.get(src))
                if val is not None:
                    rec[dst] = val
            out.append(rec)

        return out


def _resolve_existing_path(data: Union[str, Path]) -> Optional[Path]:
    if isinstance(data, Path):
        return data if data.exists() else None
    if not isinstance(data, str):
        return None
    try:
        candidate = Path(data)
    except (TypeError, OSError, ValueError):
        return None
    try:
        return candidate if candidate.exists() else None
    except (OSError, ValueError):
        # Inline JSON/CSV strings can exceed filesystem path limits.
        return None


def _first_value(row: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    float_val = _to_float(value)
    if float_val is None:
        return None
    return int(float_val)


def _to_iso8601(value: Any, timezone: Optional[str] = None) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return (
                datetime.fromtimestamp(float(value), dt_timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )
        except (TypeError, ValueError, OSError):
            return None

    text = str(value).strip()
    if not text:
        return None

    iso_candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is None:
            if timezone and _is_offset_tz(timezone):
                return parsed.replace(microsecond=0).isoformat() + timezone
            return parsed.replace(microsecond=0).isoformat() + "Z"
        return parsed.replace(microsecond=0).isoformat()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            if timezone and _is_offset_tz(timezone):
                return parsed.replace(microsecond=0).isoformat() + timezone
            return parsed.replace(microsecond=0).isoformat() + "Z"
        except ValueError:
            continue

    return None


def _is_offset_tz(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 6:
        return False
    return value[0] in {"+", "-"} and value[1:3].isdigit() and value[3] == ":" and value[4:6].isdigit()


def _switch_error_code(power: Optional[float]) -> str:
    if power is None:
        return "unknown"
    return "0" if power == 0 else "1"


def _extract_solax_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("result"), dict):
            return [payload["result"]]
        if isinstance(payload.get("result"), list):
            return [x for x in payload["result"] if isinstance(x, dict)]
        if isinstance(payload.get("data"), dict):
            return [payload["data"]]
        if isinstance(payload.get("data"), list):
            return [x for x in payload["data"] if isinstance(x, dict)]
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def _normalize_energy_to_kwh(value: Any, unit: Optional[str]) -> Optional[float]:
    energy = _to_float(value)
    if energy is None:
        return None
    if not unit:
        return energy
    unit_upper = str(unit).strip().upper()
    if unit_upper == "WH":
        return energy / 1000.0
    if unit_upper == "MWH":
        return energy * 1000.0
    return energy


def _extract_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("records", "data", "items", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict):
                return [value]
        return [payload]
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def _deep_get(data: Dict[str, Any], keys: List[str]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _base_record(
    *,
    timestamp: str,
    kwh: float,
    error_type: str,
    error_code: Optional[Any],
    asset_id: Optional[str],
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "timestamp": timestamp,
        "kWh": max(kwh, 0.0),
        "error_type": error_type,
    }
    if error_code is not None:
        record["error_code"] = str(error_code)
    if asset_id:
        record["asset_id"] = asset_id
    return record

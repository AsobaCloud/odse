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
    kwargs["_source"] = source.lower()
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
        "sungrow": SungrowTransformer(),
        "isolarcloud": SungrowTransformer(),
        "higeco": HigecoTransformer(),
        "eskom_portal": EskomPortalTransformer(),
        "eskom-portal": EskomPortalTransformer(),
        "eskom": EskomPortalTransformer(),
        "eskom_amr": EskomAMRTransformer(),
        "eskom-amr": EskomAMRTransformer(),
        "nrs049": EskomAMRTransformer(),
        "sungrow_bess": SungrowBESSTransformer(),
        "sungrow-bess": SungrowBESSTransformer(),
        "powertitan": SungrowBESSTransformer(),
        "byd_bess": BYDBESSTransformer(),
        "byd-bess": BYDBESSTransformer(),
        "byd": BYDBESSTransformer(),
        "vestas": VestasTransformer(),
        "vestas-online": VestasTransformer(),
        "siemens_gamesa": SiemensGamesaTransformer(),
        "siemens-gamesa": SiemensGamesaTransformer(),
        "sgre": SiemensGamesaTransformer(),
        "nordex": NordexTransformer(),
        "nordex-control": NordexTransformer(),
        "terraco": TerracoTransformer(),
        "terraco-historian": TerracoTransformer(),
        "csv": GenericCSVTransformer(),
        "generic_csv": GenericCSVTransformer(),
        "generic": GenericCSVTransformer(),
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


class HigecoTransformer(BaseTransformer):
    """Transform normalized Higeco docAPI records to ODS-E."""

    CONNECTION_STATUS_MAPPING = {
        "CONNECTED": "normal",
        "DISCONNECTED": "offline",
    }

    POWER_STATUS_MAPPING = {
        "ON": "normal",
        "OFF": "standby",
        "FAULT": "fault",
        "WARNING": "warning",
    }

    def _resolve_error_type(self, normalized: Dict[str, Any], power_w: Optional[float]) -> str:
        conn = str(normalized.get("connectionStatus") or "").upper()
        if conn in self.CONNECTION_STATUS_MAPPING:
            mapped = self.CONNECTION_STATUS_MAPPING[conn]
            if mapped != "normal":
                return mapped

        pstat = str(normalized.get("powerStatus") or "").upper()
        if pstat in self.POWER_STATUS_MAPPING:
            return self.POWER_STATUS_MAPPING[pstat]

        if power_w is not None:
            return "standby" if power_w == 0 else "normal"

        return "unknown"

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

            kwh = (e_wh / 1000.0) if e_wh is not None else max(((p_w or 0.0) / 1000.0) * interval_hours, 0.0)
            error_type = self._resolve_error_type(normalized, p_w)

            rec = _base_record(
                timestamp=ts,
                kwh=kwh,
                error_type=error_type,
                error_code=normalized.get("status_code"),
                asset_id=asset_id,
            )
            if p_w is not None:
                rec["kW"] = p_w / 1000.0
            for src, dst in [
                ("voltage_dc_v", "voltage_dc"),
                ("current_dc_a", "current_dc"),
                ("temperature_c", "temperature"),
                ("voltage_v", "voltage_ac"),
                ("current_a", "current_ac"),
                ("frequency_hz", "frequency"),
            ]:
                val = _to_float(normalized.get(src))
                if val is not None:
                    rec[dst] = val
            out.append(rec)

        return out


class SungrowTransformer(BaseTransformer):
    """Transform Sungrow iSolarCloud API JSON payloads to ODS-E."""

    DEVICE_STATUS_MAPPING = {
        0: "offline",       # Disconnected
        1: "standby",       # Standby
        2: "standby",       # Starting
        3: "normal",        # Running
        4: "normal",        # Generating
        5: "warning",       # Derating
        6: "fault",         # Fault
        7: "fault",         # Alarm
        8: "standby",       # Shutdown
        9: "warning",       # Communication fault
        10: "offline",      # Not communicating
        11: "standby",      # Sleeping
        12: "warning",      # Maintenance
        13: "critical",     # Emergency stop
        14: "warning",      # Grid abnormal
        15: "fault",        # Inverter fault
    }

    PLANT_STATUS_MAPPING = {
        0: "offline",       # All devices offline
        1: "normal",        # All devices normal
        2: "warning",       # Some devices warning
        3: "fault",         # Some devices fault
        4: "critical",      # Critical fault
        5: "standby",       # All devices standby
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0
        asset_id = kwargs.get("asset_id")

        out: List[Dict[str, Any]] = []

        # Handle plant_realtime endpoint
        if isinstance(payload, dict) and "plant_id" in payload and "total_power" in payload:
            ts = _to_iso8601(payload.get("timestamp"), timezone=timezone)
            if ts:
                power_w = _to_float(payload.get("total_power"))
                energy_wh = _to_float(payload.get("daily_energy"))
                status = _to_int(payload.get("status"))
                
                rec = _base_record(
                    timestamp=ts,
                    kwh=max((energy_wh or 0.0) / 1000.0, 0.0),
                    error_type=self.PLANT_STATUS_MAPPING.get(status or -1, "unknown"),
                    error_code=status,
                    asset_id=asset_id,
                )
                if power_w is not None:
                    rec["kW"] = power_w / 1000.0
                out.append(rec)
            return out

        # Handle device_telemetry endpoint
        if isinstance(payload, dict) and "device_id" in payload and "data_points" in payload:
            data_points = payload.get("data_points", [])
            if isinstance(data_points, list):
                for point in data_points:
                    if not isinstance(point, dict):
                        continue
                    ts = _to_iso8601(point.get("timestamp"), timezone=timezone)
                    if not ts:
                        continue

                    p_w = _to_float(point.get("active_power"))
                    q_var = _to_float(point.get("reactive_power"))
                    s_va = _to_float(point.get("apparent_power"))
                    pf = _to_float(point.get("power_factor"))
                    e_wh = _to_float(point.get("daily_energy"))
                    status_code = _to_int(point.get("status_code"))
                    fault_code = point.get("fault_code")

                    kwh = (e_wh / 1000.0) if e_wh is not None else max(((p_w or 0.0) / 1000.0) * interval_hours, 0.0)
                    
                    rec = _base_record(
                        timestamp=ts,
                        kwh=kwh,
                        error_type=self.DEVICE_STATUS_MAPPING.get(status_code or -1, "unknown"),
                        error_code=fault_code,
                        asset_id=asset_id,
                    )
                    
                    if p_w is not None:
                        rec["kW"] = p_w / 1000.0
                    if q_var is not None:
                        rec["kVAr"] = q_var / 1000.0
                    if s_va is not None:
                        rec["kVA"] = s_va / 1000.0
                    if pf is not None:
                        rec["PF"] = max(0.0, min(1.0, pf))
                    elif (p_w is not None) and (s_va is not None) and s_va > 0:
                        rec["PF"] = max(0.0, min(1.0, p_w / s_va))
                    
                    # AC electrical parameters (3-phase averaging/summing)
                    v_a = _to_float(point.get("voltage_a"))
                    v_b = _to_float(point.get("voltage_b"))
                    v_c = _to_float(point.get("voltage_c"))
                    voltages = [v for v in [v_a, v_b, v_c] if v is not None and v > 0]
                    if voltages:
                        rec["voltage_ac"] = sum(voltages) / len(voltages)
                    
                    i_a = _to_float(point.get("current_a"))
                    i_b = _to_float(point.get("current_b"))
                    i_c = _to_float(point.get("current_c"))
                    currents = [i for i in [i_a, i_b, i_c] if i is not None]
                    if currents:
                        rec["current_ac"] = sum(currents)
                    
                    freq = _to_float(point.get("frequency"))
                    if freq is not None:
                        rec["frequency"] = freq
                    
                    # DC electrical parameters
                    dc_v1 = _to_float(point.get("dc_voltage_1"))
                    dc_v2 = _to_float(point.get("dc_voltage_2"))
                    dc_voltages = [v for v in [dc_v1, dc_v2] if v is not None]
                    if dc_voltages:
                        rec["voltage_dc"] = max(dc_voltages)
                    
                    dc_i1 = _to_float(point.get("dc_current_1"))
                    dc_i2 = _to_float(point.get("dc_current_2"))
                    dc_currents = [i for i in [dc_i1, dc_i2] if i is not None]
                    if dc_currents:
                        rec["current_dc"] = sum(dc_currents)
                    
                    temp = _to_float(point.get("temperature"))
                    if temp is not None:
                        rec["temperature"] = temp
                    
                    if status_code is not None:
                        rec["oem_error_code"] = str(status_code)
                    
                    out.append(rec)
            return out

        # Handle historical_data endpoint
        if isinstance(payload, dict) and "data_points" in payload:
            data_points = payload.get("data_points", [])
            if isinstance(data_points, list):
                for point in data_points:
                    if not isinstance(point, dict):
                        continue
                    ts = _to_iso8601(point.get("timestamp"), timezone=timezone)
                    if not ts:
                        continue

                    power_w = _to_float(point.get("power"))
                    energy_wh = _to_float(point.get("energy"))
                    status = _to_int(point.get("status"))

                    rec = _base_record(
                        timestamp=ts,
                        kwh=max((energy_wh or 0.0) / 1000.0, 0.0),
                        error_type=self.PLANT_STATUS_MAPPING.get(status or -1, "unknown"),
                        error_code=status,
                        asset_id=asset_id,
                    )
                    if power_w is not None:
                        rec["kW"] = power_w / 1000.0
                    out.append(rec)
            return out

        return out


class EskomPortalTransformer(BaseTransformer):
    """
    Transform Eskom Data Portal CSV data to ODS-E format.
    
    Handles wide-format CSVs from the Eskom Data Request Form.
    Melts wide columns (one per metric) into ODS-E long format,
    assigning each column to a specific asset_id.
    
    Example columns: Date, Time, RSA Contracted Forecast, Residual Forecast,
    Thermal Generation, Nuclear Generation, etc.
    """
    
    # Column to asset_id mapping for Eskom national metrics
    COLUMN_ASSET_MAP = {
        "rsa_contracted_forecast": "za-eskom:generation:rsa-contracted-forecast",
        "residual_forecast": "za-eskom:generation:residual-forecast",
        "thermal_generation": "za-eskom:generation:thermal",
        "nuclear_generation": "za-eskom:generation:nuclear",
        "renewable_generation": "za-eskom:generation:renewable",
        "pumped_storage_generation": "za-eskom:generation:pumped-storage",
        "import": "za-eskom:generation:import",
        "export": "za-eskom:generation:export",
        "total_demand": "za-eskom:demand:total",
        "system_frequency": "za-eskom:grid:frequency",
    }
    
    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        timezone = kwargs.get("timezone", "Africa/Johannesburg")
        interval_hours = (kwargs.get("interval_minutes", 30) or 30) / 60.0
        
        records: List[Dict[str, Any]] = []
        
        for row in rows:
            # Parse timestamp from Date and Time columns
            date_val = _first_value(row, ["Date", "date", "DATE"])
            time_val = _first_value(row, ["Time", "time", "TIME"])
            
            if date_val:
                timestamp_str = f"{date_val} {time_val}" if time_val else date_val
                iso_ts = _to_iso8601(timestamp_str, timezone=timezone)
            else:
                timestamp_raw = _first_value(row, ["timestamp", "Timestamp", "datetime"])
                iso_ts = _to_iso8601(timestamp_raw, timezone=timezone)
            
            if not iso_ts:
                continue
            
            # Process each metric column
            for column, asset_id in self.COLUMN_ASSET_MAP.items():
                # Try case-insensitive match
                column_lower = column.lower()
                column_space_lower = column_lower.replace("_", " ")
                column_dash_lower = column_lower.replace("_", "-")
                
                value = None
                for row_key in row.keys():
                    row_key_lower = row_key.lower()
                    if row_key_lower in [column_lower, column_space_lower, column_dash_lower]:
                        value = row[row_key]
                        break
                
                if value is None or value == "":
                    continue
                
                value_float = _to_float(value)
                if value_float is None:
                    continue
                
                # Determine kWh based on metric type
                if "generation" in column.lower() or "forecast" in column.lower():
                    kwh = max(value_float * interval_hours, 0.0)
                    direction = "generation"
                elif "demand" in column.lower():
                    kwh = max(value_float * interval_hours, 0.0)
                    direction = "consumption"
                elif "frequency" in column.lower():
                    # Frequency is in Hz, not kWh
                    kwh = 0.0
                    # Store frequency in kW field for transport (non-standard but practical)
                    kw = value_float / 1000.0 if value_float > 1 else value_float
                else:
                    kwh = max(value_float * interval_hours, 0.0)
                    direction = "generation"
                
                record: Dict[str, Any] = {
                    "timestamp": iso_ts,
                    "kWh": kwh,
                    "error_type": "normal",
                    "error_code": None,
                    "asset_id": asset_id,
                }
                
                if "frequency" in column.lower():
                    record["kW"] = kw
                    record["frequency"] = value_float
                else:
                    record["kW"] = value_float  # Store power in kW
                
                if direction:
                    record["direction"] = direction
                
                records.append(record)
        
        return records


class EskomAMRTransformer(BaseTransformer):
    """
    Transform Eskom AMR (NRS 049 Standard) meter data to ODS-E format.
    
    Handles per-meter data used for billing and wheeling.
    Format: MeterNumber, Date, kWh_Import, kWh_Export, kVArh_Q1, etc.
    
    Critical for Eskom compliance - uses billing_status field.
    """
    
    BILLING_STATUS_MAPPING = {
        "metered": "metered",
        "estimated": "estimated",
        "adjusted": "adjusted",
        "disputed": "disputed",
        "m": "metered",
        "e": "estimated",
        "a": "adjusted",
        "d": "disputed",
    }
    
    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        timezone = kwargs.get("timezone", "Africa/Johannesburg")
        interval_hours = (kwargs.get("interval_minutes", 30) or 30) / 60.0
        asset_id = kwargs.get("asset_id")
        
        records: List[Dict[str, Any]] = []
        
        for row in rows:
            # Parse timestamp
            date_val = _first_value(row, ["Date", "date", "ReadingDate"])
            time_val = _first_value(row, ["Time", "time", "ReadingTime"])
            
            if date_val:
                timestamp_str = f"{date_val} {time_val}" if time_val else date_val
                iso_ts = _to_iso8601(timestamp_str, timezone=timezone)
            else:
                timestamp_raw = _first_value(row, ["timestamp", "Timestamp", "datetime"])
                iso_ts = _to_iso8601(timestamp_raw, timezone=timezone)
            
            if not iso_ts:
                continue
            
            # Extract meter number for asset_id if not provided
            meter_number = _first_value(row, ["MeterNumber", "Meter", "meter_number", "meter_id"])
            row_asset_id = asset_id or f"za-eskom:meter:{meter_number}" if meter_number else None
            
            # Extract energy values
            kwh_import = _to_float(_first_value(row, ["kWh_Import", "Import", "kWhImport", "Import_kWh"]))
            kwh_export = _to_float(_first_value(row, ["kWh_Export", "Export", "kWhExport", "Export_kWh"]))
            kvarh_q1 = _to_float(_first_value(row, ["kVArh_Q1", "Q1", "kVArhQ1"]))
            kvarh_q2 = _to_float(_first_value(row, ["kVArh_Q2", "Q2", "kVArhQ2"]))
            kvarh_q3 = _to_float(_first_value(row, ["kVArh_Q3", "Q3", "kVArhQ3"]))
            kvarh_q4 = _to_float(_first_value(row, ["kVArh_Q4", "Q4", "kVArhQ4"]))
            
            # Extract billing status
            billing_status_raw = _first_value(row, ["billing_status", "BillingStatus", "Status", "status"])
            billing_status = self.BILLING_STATUS_MAPPING.get(
                str(billing_status_raw).lower() if billing_status_raw else "",
                "metered"
            )
            
            # Determine net energy (import - export)
            kwh_import = kwh_import or 0.0
            kwh_export = kwh_export or 0.0
            net_kwh = max(kwh_import - kwh_export, 0.0)
            
            # Total reactive energy
            total_kvarh = sum(filter(None, [kvarh_q1, kvarh_q2, kvarh_q3, kvarh_q4]))
            
            record: Dict[str, Any] = {
                "timestamp": iso_ts,
                "kWh": max(net_kwh * interval_hours, 0.0),
                "error_type": "normal",
                "error_code": None,
            }
            
            if row_asset_id:
                record["asset_id"] = row_asset_id
            
            # Add billing status for municipal reconciliation
            record["billing_status"] = billing_status
            
            # Add reactive energy if available
            if total_kvarh is not None:
                record["kVArh"] = max(total_kvarh * interval_hours, 0.0)
            
            # Add import/export breakdown
            if kwh_import is not None:
                record["kWh_import"] = max(kwh_import * interval_hours, 0.0)
            if kwh_export is not None:
                record["kWh_export"] = max(kwh_export * interval_hours, 0.0)
            
            # Store meter reference
            if meter_number:
                record["oem_reference"] = {
                    "meter_number": str(meter_number),
                    "protocol": "NRS-049"
                }
            
            records.append(record)
        
        return records


class SungrowBESSTransformer(BaseTransformer):
    """Transform Sungrow PowerTitan BESS telemetry (iSolarCloud) to ODS-E.

    Handles BESS-specific fields: state of charge, state of health, charge/
    discharge energy, cell-level temperature and voltage, cycle count, and
    dispatch mode. Input is an iSolarCloud device_telemetry-style JSON payload
    whose ``data_points`` array contains BESS tags.
    """

    # run_mode -> dispatch_mode (Sungrow PowerTitan convention)
    RUN_MODE_MAPPING = {
        0: "standby",
        1: "charging",
        2: "discharging",
        3: "balancing",
    }

    # status_code -> error_type (mirrors SungrowTransformer device mapping)
    STATUS_MAPPING = {
        0: "offline",
        1: "standby",
        2: "standby",
        3: "normal",
        4: "normal",
        5: "warning",
        6: "fault",
        7: "fault",
        8: "standby",
        9: "warning",
        10: "offline",
        11: "standby",
        12: "warning",
        13: "critical",
        14: "warning",
        15: "fault",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        payload = self._parse_json(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0
        asset_id = kwargs.get("asset_id")

        out: List[Dict[str, Any]] = []

        if not isinstance(payload, dict):
            return out

        data_points = payload.get("data_points", [])
        if not isinstance(data_points, list):
            return out

        for point in data_points:
            if not isinstance(point, dict):
                continue
            ts = _to_iso8601(point.get("timestamp"), timezone=timezone)
            if not ts:
                continue

            charge_power_w = _to_float(point.get("charge_power"))
            discharge_power_w = _to_float(point.get("discharge_power"))
            active_power_w = _to_float(point.get("active_power"))
            status_code = _to_int(point.get("status_code"))
            fault_code = point.get("fault_code")
            run_mode = _to_int(point.get("run_mode"))

            # Prefer explicit charge/discharge power; fall back to active_power sign.
            if charge_power_w is not None and discharge_power_w is not None:
                charge_kwh = max((charge_power_w / 1000.0) * interval_hours, 0.0)
                discharge_kwh = max((discharge_power_w / 1000.0) * interval_hours, 0.0)
            elif active_power_w is not None:
                if active_power_w < 0:
                    charge_kwh = max((-active_power_w / 1000.0) * interval_hours, 0.0)
                    discharge_kwh = 0.0
                else:
                    charge_kwh = 0.0
                    discharge_kwh = max((active_power_w / 1000.0) * interval_hours, 0.0)
            else:
                charge_kwh = 0.0
                discharge_kwh = 0.0

            # Net kWh for the base record: discharge - charge (generation positive).
            net_kwh = max(discharge_kwh - charge_kwh, 0.0)

            rec = _base_record(
                timestamp=ts,
                kwh=net_kwh,
                error_type=self.STATUS_MAPPING.get(status_code or -1, "unknown"),
                error_code=fault_code,
                asset_id=asset_id,
            )

            # BESS fields
            soc = _to_float(point.get("soc"))
            if soc is not None:
                rec["soc"] = max(0.0, min(100.0, soc))
            soh = _to_float(point.get("soh"))
            if soh is not None:
                rec["soh"] = max(0.0, min(100.0, soh))
            rec["charge_kWh"] = charge_kwh
            rec["discharge_kWh"] = discharge_kwh

            cycle_count = _to_float(point.get("cycle_count"))
            if cycle_count is not None:
                rec["cycle_count"] = max(0.0, cycle_count)

            cell_temp_min = _to_float(point.get("min_cell_temp"))
            if cell_temp_min is not None:
                rec["cell_temp_min_c"] = cell_temp_min
            cell_temp_max = _to_float(point.get("max_cell_temp"))
            if cell_temp_max is not None:
                rec["cell_temp_max_c"] = cell_temp_max

            cell_v_min = _to_float(point.get("min_cell_voltage"))
            if cell_v_min is not None:
                rec["cell_voltage_min_v"] = max(0.0, cell_v_min)
            cell_v_max = _to_float(point.get("max_cell_voltage"))
            if cell_v_max is not None:
                rec["cell_voltage_max_v"] = max(0.0, cell_v_max)

            dispatch_mode = self.RUN_MODE_MAPPING.get(run_mode or -1)
            if dispatch_mode is None:
                # Infer from power flow when run_mode is absent.
                if charge_kwh > 0 and discharge_kwh == 0:
                    dispatch_mode = "charging"
                elif discharge_kwh > 0 and charge_kwh == 0:
                    dispatch_mode = "discharging"
                else:
                    dispatch_mode = "standby"
            rec["dispatch_mode"] = dispatch_mode

            # Electrical parameters (optional, when present)
            q_var = _to_float(point.get("reactive_power"))
            if q_var is not None:
                rec["kVAr"] = q_var / 1000.0
            s_va = _to_float(point.get("apparent_power"))
            if s_va is not None:
                rec["kVA"] = s_va / 1000.0
            pf = _to_float(point.get("power_factor"))
            if pf is not None:
                rec["PF"] = max(0.0, min(1.0, pf))
            freq = _to_float(point.get("frequency"))
            if freq is not None:
                rec["frequency"] = freq

            if active_power_w is not None:
                rec["kW"] = active_power_w / 1000.0

            if status_code is not None:
                rec["oem_error_code"] = str(status_code)

            out.append(rec)

        return out


class BYDBESSTransformer(BaseTransformer):
    """Transform BYD BatteryBox / BMS CSV export to ODS-E.

    Expected CSV columns: timestamp, soc, soh, charge_power_kw,
    discharge_power_kw, cycle_count, cell_temp_min, cell_temp_max,
    cell_voltage_min, cell_voltage_max, bms_status, dispatch_mode.
    """

    # bms_status -> error_type
    BMS_STATUS_MAPPING = {
        0: "normal",
        1: "standby",
        2: "warning",
        3: "fault",
        4: "offline",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        timezone = kwargs.get("timezone", "Africa/Johannesburg")
        interval_hours = (kwargs.get("interval_minutes", 15) or 15) / 60.0
        asset_id = kwargs.get("asset_id")

        records: List[Dict[str, Any]] = []

        for row in rows:
            ts_raw = _first_value(row, ["timestamp", "Timestamp", "Time", "datetime"])
            iso_ts = _to_iso8601(ts_raw, timezone=timezone)
            if not iso_ts:
                continue

            charge_kw = _to_float(_first_value(row, ["charge_power_kw", "charge_power"]))
            discharge_kw = _to_float(_first_value(row, ["discharge_power_kw", "discharge_power"]))

            charge_kwh = max((charge_kw or 0.0) * interval_hours, 0.0)
            discharge_kwh = max((discharge_kw or 0.0) * interval_hours, 0.0)
            net_kwh = max(discharge_kwh - charge_kwh, 0.0)

            bms_status = _to_int(_first_value(row, ["bms_status", "status", "Status"]))
            error_type = self.BMS_STATUS_MAPPING.get(
                bms_status if bms_status is not None else -1, "unknown",
            )

            rec = _base_record(
                timestamp=iso_ts,
                kwh=net_kwh,
                error_type=error_type,
                error_code=bms_status,
                asset_id=asset_id,
            )

            soc = _to_float(_first_value(row, ["soc", "SOC"]))
            if soc is not None:
                rec["soc"] = max(0.0, min(100.0, soc))
            soh = _to_float(_first_value(row, ["soh", "SOH"]))
            if soh is not None:
                rec["soh"] = max(0.0, min(100.0, soh))

            rec["charge_kWh"] = charge_kwh
            rec["discharge_kWh"] = discharge_kwh

            cycle_count = _to_float(_first_value(row, ["cycle_count", "cycles"]))
            if cycle_count is not None:
                rec["cycle_count"] = max(0.0, cycle_count)

            cell_temp_min = _to_float(_first_value(row, ["cell_temp_min", "min_cell_temp"]))
            if cell_temp_min is not None:
                rec["cell_temp_min_c"] = cell_temp_min
            cell_temp_max = _to_float(_first_value(row, ["cell_temp_max", "max_cell_temp"]))
            if cell_temp_max is not None:
                rec["cell_temp_max_c"] = cell_temp_max

            cell_v_min = _to_float(_first_value(row, ["cell_voltage_min", "min_cell_voltage"]))
            if cell_v_min is not None:
                rec["cell_voltage_min_v"] = max(0.0, cell_v_min)
            cell_v_max = _to_float(_first_value(row, ["cell_voltage_max", "max_cell_voltage"]))
            if cell_v_max is not None:
                rec["cell_voltage_max_v"] = max(0.0, cell_v_max)

            dispatch_mode_raw = _first_value(row, ["dispatch_mode", "mode"])
            if dispatch_mode_raw is not None:
                mode = str(dispatch_mode_raw).strip().lower()
                if mode in ("charging", "discharging", "standby", "balancing"):
                    rec["dispatch_mode"] = mode
                else:
                    # Infer from power flow.
                    if charge_kwh > 0 and discharge_kwh == 0:
                        rec["dispatch_mode"] = "charging"
                    elif discharge_kwh > 0 and charge_kwh == 0:
                        rec["dispatch_mode"] = "discharging"
                    else:
                        rec["dispatch_mode"] = "standby"
            else:
                if charge_kwh > 0 and discharge_kwh == 0:
                    rec["dispatch_mode"] = "charging"
                elif discharge_kwh > 0 and charge_kwh == 0:
                    rec["dispatch_mode"] = "discharging"
                else:
                    rec["dispatch_mode"] = "standby"

            if charge_kw is not None:
                rec["kW"] = -charge_kw
            elif discharge_kw is not None:
                rec["kW"] = discharge_kw

            records.append(rec)

        return records


class VestasTransformer(BaseTransformer):
    """Transform Vestas Online SCADA CSV export to ODS-E.

    Expected CSV columns: timestamp, active_power_kw, wind_speed,
    rotor_rpm, nacelle_position, yaw_error, blade_pitch,
    generator_temp, grid_frequency, turbine_state.
    """

    # turbine_state (integer) -> error_type
    TURBINE_STATE_MAPPING = {
        0: "offline",
        1: "standby",
        2: "normal",
        3: "warning",
        4: "fault",
        5: "warning",  # maintenance
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 10) or 10) / 60.0
        asset_id = kwargs.get("asset_id")

        records: List[Dict[str, Any]] = []
        for row in rows:
            ts_raw = _first_value(row, ["timestamp", "Timestamp", "Time", "datetime"])
            iso_ts = _to_iso8601(ts_raw, timezone=timezone)
            if not iso_ts:
                continue

            power_kw = _to_float(
                _first_value(row, ["active_power_kw", "active_power", "power_kw", "Power"])
            )
            kwh = max((power_kw or 0.0) * interval_hours, 0.0)

            turbine_state = _to_int(
                _first_value(row, ["turbine_state", "state", "status", "Status"])
            )
            error_type = self.TURBINE_STATE_MAPPING.get(
                turbine_state if turbine_state is not None else -1, "unknown",
            )

            rec = _base_record(
                timestamp=iso_ts,
                kwh=kwh,
                error_type=error_type,
                error_code=turbine_state,
                asset_id=asset_id,
            )

            if power_kw is not None:
                rec["kW"] = power_kw

            wind_speed = _to_float(_first_value(row, ["wind_speed", "WindSpeed", "wind_speed_ms"]))
            if wind_speed is not None:
                rec["wind_speed_ms"] = max(0.0, wind_speed)

            rotor_rpm = _to_float(_first_value(row, ["rotor_rpm", "rotor_speed", "RotorRPM"]))
            if rotor_rpm is not None:
                rec["rotor_rpm"] = max(0.0, rotor_rpm)

            nacelle_pos = _to_float(
                _first_value(row, ["nacelle_position", "nacelle_direction", "NacellePosition"])
            )
            if nacelle_pos is not None:
                rec["nacelle_direction_deg"] = max(0.0, min(360.0, nacelle_pos))

            blade_pitch = _to_float(_first_value(row, ["blade_pitch", "pitch_angle", "BladePitch"]))
            if blade_pitch is not None:
                rec["blade_pitch_deg"] = blade_pitch

            gen_temp = _to_float(_first_value(row, ["generator_temp", "GeneratorTemp"]))
            if gen_temp is not None:
                rec["temperature"] = gen_temp

            grid_freq = _to_float(_first_value(row, ["grid_frequency", "frequency", "GridFreq"]))
            if grid_freq is not None:
                rec["frequency"] = grid_freq

            records.append(rec)

        return records


class SiemensGamesaTransformer(BaseTransformer):
    """Transform Siemens Gamesa Diagnostic System SCADA CSV export to ODS-E.

    Expected CSV columns: timestamp, active_power_kw, reactive_power_kvar,
    wind_speed_nacelle, wind_speed_metmast, rotor_speed, pitch_angle,
    generator_speed, bearing_temp, availability_status.
    """

    # availability_status (string) -> error_type
    AVAILABILITY_MAPPING = {
        "full": "normal",
        "limited": "warning",
        "standstill": "standby",
        "error": "fault",
        "offline": "offline",
        "maintenance": "warning",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 10) or 10) / 60.0
        asset_id = kwargs.get("asset_id")

        records: List[Dict[str, Any]] = []
        for row in rows:
            ts_raw = _first_value(row, ["timestamp", "Timestamp", "Time", "datetime"])
            iso_ts = _to_iso8601(ts_raw, timezone=timezone)
            if not iso_ts:
                continue

            power_kw = _to_float(
                _first_value(row, ["active_power_kw", "active_power", "power_kw", "Power"])
            )
            kwh = max((power_kw or 0.0) * interval_hours, 0.0)

            status_raw = _first_value(
                row, ["availability_status", "status", "Status", "availability"]
            )
            error_type = "unknown"
            if status_raw is not None:
                status_key = str(status_raw).strip().lower()
                error_type = self.AVAILABILITY_MAPPING.get(status_key, "unknown")

            rec = _base_record(
                timestamp=iso_ts,
                kwh=kwh,
                error_type=error_type,
                error_code=status_raw,
                asset_id=asset_id,
            )

            if power_kw is not None:
                rec["kW"] = power_kw

            reactive_kvar = _to_float(
                _first_value(row, ["reactive_power_kvar", "reactive_power", "ReactivePower"])
            )
            if reactive_kvar is not None:
                rec["kVAr"] = reactive_kvar

            wind_speed = _to_float(
                _first_value(row, ["wind_speed_nacelle", "wind_speed", "WindSpeed"])
            )
            if wind_speed is None:
                wind_speed = _to_float(
                    _first_value(row, ["wind_speed_metmast", "metmast_wind_speed"])
                )
            if wind_speed is not None:
                rec["wind_speed_ms"] = max(0.0, wind_speed)

            rotor_speed = _to_float(_first_value(row, ["rotor_speed", "rotor_rpm", "RotorSpeed"]))
            if rotor_speed is not None:
                rec["rotor_rpm"] = max(0.0, rotor_speed)

            pitch_angle = _to_float(_first_value(row, ["pitch_angle", "blade_pitch", "PitchAngle"]))
            if pitch_angle is not None:
                rec["blade_pitch_deg"] = pitch_angle

            bearing_temp = _to_float(_first_value(row, ["bearing_temp", "BearingTemp"]))
            if bearing_temp is not None:
                rec["temperature"] = bearing_temp

            records.append(rec)

        return records


class NordexTransformer(BaseTransformer):
    """Transform Nordex Control SCADA CSV export to ODS-E.

    Expected CSV columns: timestamp, active_power_kw, wind_speed,
    rotor_speed, blade_angle, generator_temp, transformer_temp,
    turbine_status.
    """

    # turbine_status (string) -> error_type
    TURBINE_STATUS_MAPPING = {
        "running": "normal",
        "standby": "standby",
        "paused": "standby",
        "warning": "warning",
        "error": "fault",
        "offline": "offline",
        "maintenance": "warning",
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        rows = self._parse_csv_rows(data)
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 10) or 10) / 60.0
        asset_id = kwargs.get("asset_id")

        records: List[Dict[str, Any]] = []
        for row in rows:
            ts_raw = _first_value(row, ["timestamp", "Timestamp", "Time", "datetime"])
            iso_ts = _to_iso8601(ts_raw, timezone=timezone)
            if not iso_ts:
                continue

            power_kw = _to_float(
                _first_value(row, ["active_power_kw", "active_power", "power_kw", "Power"])
            )
            kwh = max((power_kw or 0.0) * interval_hours, 0.0)

            status_raw = _first_value(row, ["turbine_status", "status", "Status", "state"])
            error_type = "unknown"
            if status_raw is not None:
                status_key = str(status_raw).strip().lower()
                error_type = self.TURBINE_STATUS_MAPPING.get(status_key, "unknown")

            rec = _base_record(
                timestamp=iso_ts,
                kwh=kwh,
                error_type=error_type,
                error_code=status_raw,
                asset_id=asset_id,
            )

            if power_kw is not None:
                rec["kW"] = power_kw

            wind_speed = _to_float(_first_value(row, ["wind_speed", "WindSpeed", "wind_speed_ms"]))
            if wind_speed is not None:
                rec["wind_speed_ms"] = max(0.0, wind_speed)

            rotor_speed = _to_float(_first_value(row, ["rotor_speed", "rotor_rpm", "RotorSpeed"]))
            if rotor_speed is not None:
                rec["rotor_rpm"] = max(0.0, rotor_speed)

            blade_angle = _to_float(_first_value(row, ["blade_angle", "blade_pitch", "BladeAngle"]))
            if blade_angle is not None:
                rec["blade_pitch_deg"] = blade_angle

            gen_temp = _to_float(_first_value(row, ["generator_temp", "GeneratorTemp"]))
            if gen_temp is not None:
                rec["temperature"] = gen_temp

            records.append(rec)

        return records


class TerracoTransformer(BaseTransformer):
    """Transform Terraco SCADA historian data to ODS-E.

    Handles both JSON (REST API response) and CSV (export) inputs.
    Terraco uses ``{AssetName}.{TagName}`` naming convention. The transformer
    matches tag suffixes (case-insensitive) to ODS-E fields.

    JSON structure (REST API):
        {"data": [{"timestamp": "...", "values": {"JBAY.ActivePower": 1800.0, ...}}]}

    CSV structure (export):
        timestamp,JBAY.ActivePower,JBAY.ActiveEnergy,JBAY.Status,...
    """

    # Integer state code -> error_type
    STATE_MAPPING = {
        0: "offline",
        1: "normal",
        2: "standby",
        3: "warning",
        4: "fault",
        5: "warning",  # maintenance
    }

    # Tag suffix -> (ODS-E field, is_power_kwh)
    # Order matters: first match wins per field.
    TAG_SUFFIX_MAP = [
        (["activepower", "kw"], "kW", False),
        (["activeenergy", "kwh"], "kWh", True),
        (["status", "state"], "error_type", False),
        (["temperature"], "temperature", False),
        (["voltage"], "voltage_ac", False),
        (["current"], "current_ac", False),
        (["frequency"], "frequency", False),
        (["reactivepower"], "kVAr", False),
        (["powerfactor"], "PF", False),
    ]

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 10) or 10) / 60.0
        asset_id = kwargs.get("asset_id")

        # Detect JSON vs CSV input.
        try:
            payload = self._parse_json(data)
            if isinstance(payload, (dict, list)):
                return self._transform_json(
                    payload, timezone=timezone, interval_hours=interval_hours,
                    asset_id=asset_id,
                )
        except (json.JSONDecodeError, ValueError):
            pass

        # Fall back to CSV.
        rows = self._parse_csv_rows(data)
        return self._transform_rows(
            rows, timezone=timezone, interval_hours=interval_hours,
            asset_id=asset_id,
        )

    def _transform_json(
        self, payload: Any, *, timezone: Optional[str],
        interval_hours: float, asset_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        samples = _extract_records(payload)
        out: List[Dict[str, Any]] = []
        for sample in samples:
            ts = _to_iso8601(sample.get("timestamp"), timezone=timezone)
            if not ts:
                continue
            values = sample.get("values")
            if not isinstance(values, dict):
                # Flat dict: treat the sample itself as the values map.
                values = {k: v for k, v in sample.items() if k != "timestamp"}
            out.append(
                self._build_record(
                    ts, values, interval_hours=interval_hours, asset_id=asset_id,
                )
            )
        return out

    def _transform_rows(
        self, rows: List[Dict[str, Any]], *, timezone: Optional[str],
        interval_hours: float, asset_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for row in rows:
            ts_raw = _first_value(row, ["timestamp", "Timestamp", "Time", "datetime"])
            ts = _to_iso8601(ts_raw, timezone=timezone)
            if not ts:
                continue
            out.append(
                self._build_record(
                    ts, row, interval_hours=interval_hours, asset_id=asset_id,
                )
            )
        return out

    def _build_record(
        self, ts: str, values: Dict[str, Any], *,
        interval_hours: float, asset_id: Optional[str],
    ) -> Dict[str, Any]:
        mapped = self._map_tags(values)

        power_kw = _to_float(mapped.get("kW"))
        energy_kwh = _to_float(mapped.get("kWh"))
        if energy_kwh is not None:
            kwh = max(energy_kwh, 0.0)
        elif power_kw is not None:
            kwh = max(power_kw * interval_hours, 0.0)
        else:
            kwh = 0.0

        state_code = _to_int(mapped.get("error_type"))
        error_type = self.STATE_MAPPING.get(
            state_code if state_code is not None else -1, "unknown",
        )

        rec = _base_record(
            timestamp=ts,
            kwh=kwh,
            error_type=error_type,
            error_code=state_code,
            asset_id=asset_id,
        )

        if power_kw is not None:
            rec["kW"] = power_kw

        for field in ["temperature", "voltage_ac", "current_ac", "frequency", "kVAr"]:
            val = _to_float(mapped.get(field))
            if val is not None:
                rec[field] = val

        pf = _to_float(mapped.get("PF"))
        if pf is not None:
            rec["PF"] = max(0.0, min(1.0, pf))

        return rec

    def _map_tags(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Map Terraco tag names to ODS-E field names via suffix matching."""
        result: Dict[str, Any] = {}
        for key, val in values.items():
            if val is None or val == "":
                continue
            key_lower = str(key).lower()
            # Strip asset prefix: "JBAY.ActivePower" -> "activepower"
            suffix = key_lower.split(".")[-1] if "." in key_lower else key_lower
            for suffixes, odse_field, _is_energy in self.TAG_SUFFIX_MAP:
                if suffix in suffixes:
                    # Don't overwrite if already mapped (first match wins).
                    if odse_field not in result:
                        result[odse_field] = val
                    break
        return result


class GenericCSVTransformer(BaseTransformer):
    """Transform arbitrary CSV data to ODS-E using a column mapping."""

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        mapping = kwargs.get("column_map", kwargs.get("mapping"))
        source_name = str(kwargs.get("_source", "")).lower()
        strict_generic = source_name == "generic_csv"
        if mapping is None:
            raise ValueError(
                "Generic CSV transformer requires a 'mapping' argument. "
                "Provide a dict or path to a YAML/JSON mapping file with keys: "
                "timestamp, kWh (and optionally kW, error_type, error_code, asset_id)."
            )

        if isinstance(mapping, (str, Path)):
            mapping = self._load_mapping_file(mapping)

        if not isinstance(mapping, dict):
            raise ValueError("Mapping must be a dict.")

        if "timestamp" not in mapping:
            raise ValueError(
                "Mapping must include 'timestamp' mapped to the CSV timestamp column."
            )
        if strict_generic and "kWh" not in mapping:
            raise ValueError(
                "Mapping must include 'kWh' for source='generic_csv'."
            )

        rows = self._parse_csv_rows(data)
        asset_id = kwargs.get("asset_id")
        timezone = kwargs.get("timezone")
        interval_hours = (kwargs.get("interval_minutes", 5) or 5) / 60.0
        default_error_type = kwargs.get("default_error_type", "normal")

        ts_col = mapping["timestamp"]
        kwh_col = mapping.get("kWh")
        kw_col = mapping.get("kW")
        error_type_col = mapping.get("error_type")
        error_code_col = mapping.get("error_code")
        asset_id_col = mapping.get("asset_id")
        extra_cols = mapping.get("extra", {})

        parsed_rows: List[Dict[str, Any]] = []
        for row in rows:
            timestamp_raw = row.get(ts_col)
            iso_ts = _to_iso8601(timestamp_raw, timezone=timezone)
            if not iso_ts:
                continue
            parsed_rows.append(
                {
                    "row": row,
                    "timestamp": iso_ts,
                    "kwh_raw": _to_float(row.get(kwh_col)) if kwh_col else None,
                    "kw": _to_float(row.get(kw_col)) if kw_col else None,
                }
            )

        # For generic_csv, monotonic kWh is treated as cumulative and converted to interval deltas.
        if strict_generic and kwh_col:
            valid_kwh = [r["kwh_raw"] for r in parsed_rows if r["kwh_raw"] is not None]
            is_cumulative = len(valid_kwh) >= 2 and all(
                valid_kwh[i] >= valid_kwh[i - 1] for i in range(1, len(valid_kwh))
            )
            if is_cumulative:
                prev = None
                for item in parsed_rows:
                    current = item["kwh_raw"]
                    if current is None:
                        continue
                    if prev is None:
                        item["kwh"] = 0.0
                    else:
                        item["kwh"] = max(current - prev, 0.0)
                    prev = current
            else:
                for item in parsed_rows:
                    item["kwh"] = item["kwh_raw"]
        else:
            for item in parsed_rows:
                item["kwh"] = item["kwh_raw"]

        records: List[Dict[str, Any]] = []
        for item in parsed_rows:
            row = item["row"]
            iso_ts = item["timestamp"]
            kwh = item["kwh"]
            kw = item["kw"]

            if kwh is None and kw is not None:
                kwh = max(kw * interval_hours, 0.0)
            elif kwh is None:
                kwh = 0.0

            error_type = default_error_type
            if error_type_col and row.get(error_type_col):
                error_type = str(row[error_type_col]).strip().lower()

            error_code = None
            if error_code_col and row.get(error_code_col):
                error_code = row[error_code_col]

            row_asset_id = asset_id
            if asset_id_col and row.get(asset_id_col):
                row_asset_id = str(row[asset_id_col])

            rec = _base_record(
                timestamp=iso_ts,
                kwh=kwh,
                error_type=error_type,
                error_code=error_code,
                asset_id=row_asset_id,
            )

            if kw is not None:
                rec["kW"] = kw

            for odse_field, csv_col in extra_cols.items():
                val = _to_float(row.get(csv_col))
                if val is not None:
                    rec[odse_field] = val

            records.append(rec)

        return records

    def transform_stream(self, data: Union[str, Path], **kwargs) -> Iterator[Dict[str, Any]]:
        yield from self.transform(data, **kwargs)

    @staticmethod
    def _load_mapping_file(path: Union[str, Path]) -> dict:
        file_path = Path(path)
        text = file_path.read_text(encoding="utf-8")

        if file_path.suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError:
                raise ImportError(
                    "PyYAML is required to load YAML mapping files. "
                    "Install it with: pip install pyyaml"
                )
            return yaml.safe_load(text)

        return json.loads(text)


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

    if text.replace(".", "", 1).isdigit():
        try:
            return (
                datetime.fromtimestamp(float(text), dt_timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )
        except (TypeError, ValueError, OSError):
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

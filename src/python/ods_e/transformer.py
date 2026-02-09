"""
ODS-E Transformer

Transforms OEM-specific data formats to ODS-E schema.
"""

import csv
import json
import math
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union


def transform(
    data: Union[str, Path],
    source: str,
    asset_id: Optional[str] = None,
    timezone: Optional[str] = None,
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
    return transformer.transform(data, asset_id=asset_id, timezone=timezone)


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
        # Placeholder implementation
        return []


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
    }

    def transform(self, data: Union[str, Path], **kwargs) -> List[Dict[str, Any]]:
        # Placeholder implementation
        return []


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


def _resolve_existing_path(data: Union[str, Path]) -> Optional[Path]:
    if isinstance(data, Path):
        return data if data.exists() else None
    if not isinstance(data, str):
        return None
    try:
        candidate = Path(data)
    except (TypeError, OSError, ValueError):
        return None
    return candidate if candidate.exists() else None


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
            return datetime.utcfromtimestamp(float(value)).replace(microsecond=0).isoformat() + "Z"
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

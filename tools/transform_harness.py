#!/usr/bin/env python3
"""
Runtime transform harness for ODS-E OEM sources.

Modes:
- fixture: use built-in payload fixtures only
- live: use live API requests only (requires env config per OEM)
- mixed: use live if configured, else fallback to fixtures
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from ods_e.transformer import transform


CANONICAL_OEMS = [
    "huawei",
    "enphase",
    "solarman",
    "solaredge",
    "fronius",
    "switch",
    "sma",
    "fimer",
    "solis",
    "solaxcloud",
]

FIXTURES: Dict[str, str] = {
    "huawei": (
        "timestamp,power,inverter_state,run_state\n"
        "2026-02-09 12:00:00,10,512,1\n"
    ),
    "enphase": json.dumps([
        {"end_at": 1739102400, "wh_del": 3500, "devices_reporting": 9}
    ]),
    "solarman": (
        "Update Time,Generation(kWh),Device State,Power(W)\n"
        "2026-02-09 12:00:00,100.0,Operating,500\n"
        "2026-02-09 12:05:00,100.6,Operating,600\n"
    ),
    "solaredge": json.dumps({
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
                        "cosPhi": 0.96,
                    },
                }
            ]
        }
    }),
    "fronius": json.dumps({
        "Head": {"Timestamp": "2026-02-09T12:00:00Z", "Status": {"Code": 0}},
        "Body": {"Data": {"Site": {"P_PV": 4200, "E_Day": 13500}}},
    }),
    "switch": (
        "timestampISO,dP1,dP2,dQ1,dQ2\n"
        "2026-02-09 12:00:00,1000,,200,\n"
    ),
    "sma": json.dumps({
        "records": [
            {
                "normalized": {
                    "timestamp": "2026-02-09T12:00:00Z",
                    "active_power_w": 3000,
                    "active_energy_wh": 2500,
                    "status_code": "ONLINE",
                    "event_severity": "warning",
                    "event_code": "E101",
                }
            }
        ]
    }),
    "fimer": json.dumps({
        "series": [{"date": "2026-02-08", "energy": 15000, "unit": "Wh"}]
    }),
    "solis": json.dumps({
        "records": [
            {
                "normalized": {
                    "timestamp": "2026-02-09T12:00:00Z",
                    "active_power_w": 4600,
                    "inverter_status": "running",
                    "status_code": "200",
                    "temperature_c": 41.2,
                }
            }
        ]
    }),
    "solaxcloud": json.dumps({
        "success": True,
        "code": 0,
        "result": {
            "uploadTime": "2026-02-09 12:00:00",
            "acpower": 4200.0,
            "yieldtoday": 18.4,
            "inverterStatus": "102",
        },
    }),
}


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def env_json(name: str, default: Any) -> Any:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def get_live_config(oem: str) -> Optional[Dict[str, Any]]:
    prefix = f"ODS_LIVE_{oem.upper()}_"
    url = os.environ.get(f"{prefix}URL")

    if not url and oem == "fronius":
        host = os.environ.get("FRONIUS_HOST")
        if host:
            url = f"http://{host}/solar_api/v1/GetPowerFlowRealtimeData.fcgi"

    if not url:
        return None

    return {
        "url": url,
        "method": os.environ.get(f"{prefix}METHOD", "GET").upper(),
        "headers": env_json(f"{prefix}HEADERS", {}),
        "body": env_json(f"{prefix}BODY", None),
        "timeout": int(os.environ.get(f"{prefix}TIMEOUT", "30")),
        "transform_kwargs": env_json(f"{prefix}TRANSFORM_KWARGS", {}),
    }


def fetch_live_payload(cfg: Dict[str, Any]) -> str:
    body_bytes: Optional[bytes] = None
    if cfg["body"] is not None:
        body_bytes = json.dumps(cfg["body"]).encode("utf-8")
    req = urllib.request.Request(
        cfg["url"],
        data=body_bytes,
        method=cfg["method"],
        headers=cfg["headers"] or {},
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {cfg['url']}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"URL error for {cfg['url']}: {exc.reason}") from exc


def validate_records(records: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if not isinstance(records, list):
        return False, "transform did not return list"
    if len(records) == 0:
        return False, "transform returned empty list"
    required = {"timestamp", "kWh", "error_type"}
    for idx, row in enumerate(records):
        if not isinstance(row, dict):
            return False, f"record {idx} is not object"
        missing = required - set(row.keys())
        if missing:
            return False, f"record {idx} missing keys: {sorted(missing)}"
    return True, "ok"


def run_one(oem: str, mode: str) -> Tuple[bool, str]:
    live_cfg = get_live_config(oem)
    use_live = (mode == "live") or (mode == "mixed" and live_cfg is not None)

    if use_live and live_cfg is None:
        return False, "live config missing"

    data: str
    kwargs: Dict[str, Any] = {}
    source = oem
    if use_live:
        data = fetch_live_payload(live_cfg)
        kwargs = live_cfg.get("transform_kwargs", {})
        input_mode = "live"
    else:
        data = FIXTURES[oem]
        if oem == "enphase":
            kwargs["expected_devices"] = 10
        input_mode = "fixture"

    records = transform(data, source=source, **kwargs)
    ok, detail = validate_records(records)
    if ok:
        return True, f"{input_mode}: {len(records)} records"
    return False, f"{input_mode}: {detail}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ODS-E transform harness")
    parser.add_argument(
        "--mode",
        choices=["fixture", "live", "mixed"],
        default="mixed",
        help="fixture=fixtures only, live=live only, mixed=prefer live if configured",
    )
    parser.add_argument(
        "--oems",
        default="all",
        help="Comma-separated OEM keys or 'all'",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv(".env")
    args = parse_args()
    selected = (
        CANONICAL_OEMS
        if args.oems == "all"
        else [x.strip().lower() for x in args.oems.split(",") if x.strip()]
    )

    invalid = [x for x in selected if x not in FIXTURES]
    if invalid:
        print(f"Unknown OEM(s): {', '.join(invalid)}")
        return 2

    failures = 0
    for oem in selected:
        try:
            ok, detail = run_one(oem, args.mode)
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, str(exc)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {oem}: {detail}")
        if not ok:
            failures += 1

    if failures > 0:
        print(f"\nResult: {failures} failure(s)")
        return 1
    print("\nResult: all selected transforms passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

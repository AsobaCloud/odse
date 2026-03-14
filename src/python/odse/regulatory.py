"""Regulatory event normalization helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Iterable, List
from urllib.parse import urljoin


REGULATORY_EVENT_SCHEMA_VERSION = "regulatory-event.v1"


def _stable_id(*parts: Any) -> str:
    raw = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _parse_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text[:10] if len(text) >= 10 else text


def _slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    return "-".join(part for part in cleaned.split("-") if part)


def _classify_event_type(title: str, default: str) -> str:
    lowered = title.lower()
    if "decision" in lowered or "approves" in lowered or "approval" in lowered:
        return "decision"
    if "comment" in lowered or "hearing" in lowered or "invitation" in lowered:
        return "consultation"
    if "bidder" in lowered or "procurement" in lowered or "rfq" in lowered:
        return "procurement_update"
    if "tariff" in lowered or "price" in lowered or "fuel notice" in lowered:
        return "public_notice"
    return default


def _normalize_nersa(records: Iterable[dict[str, Any]]) -> List[dict[str, Any]]:
    events = []
    for record in records:
        title = str(record.get("title") or "").strip()
        if not title:
            continue
        href = record.get("href") or ""
        source_record_id = str(href).strip("/").split("/")[-1] if href else _slugify(title)
        events.append(
            {
                "jurisdiction": "ZA",
                "regulator": "NERSA",
                "event_type": _classify_event_type(title, "announcement"),
                "title": title,
                "summary": record.get("section") or "NERSA event",
                "effective_date": None,
                "deadline_date": None,
                "published_date": _parse_date(record.get("published_date")),
                "source_url": urljoin("https://www.nersa.org.za/", href),
                "source_system": "nersa",
                "source_record_id": source_record_id,
                "schema_version": REGULATORY_EVENT_SCHEMA_VERSION,
                "transform_version": "nersa.v1",
            }
        )
    return events


def _normalize_ippo(records: Iterable[dict[str, Any]]) -> List[dict[str, Any]]:
    events = []
    for record in records:
        title = str(record.get("headline") or "").strip()
        if not title:
            continue
        noteid = record.get("noteid")
        events.append(
            {
                "jurisdiction": "ZA",
                "regulator": "IPP Office",
                "event_type": _classify_event_type(title, "announcement"),
                "title": title,
                "summary": record.get("detail") or "IPP Office press release",
                "effective_date": None,
                "deadline_date": None,
                "published_date": _parse_date(record.get("date")),
                "source_url": urljoin("https://www.ipp-projects.co.za", f"/_entity/annotation/{noteid}") if noteid else "https://www.ipp-projects.co.za/latestnews/",
                "source_system": "ippo",
                "source_record_id": str(record.get("id") or _slugify(title)),
                "schema_version": REGULATORY_EVENT_SCHEMA_VERSION,
                "transform_version": "ippo.v1",
            }
        )
    return events


def _normalize_zera_seed(records: Iterable[dict[str, Any]]) -> List[dict[str, Any]]:
    events = []
    for record in records:
        title = str(record.get("title") or "").strip()
        if not title:
            continue
        events.append(
            {
                "jurisdiction": "ZW",
                "regulator": "ZERA",
                "event_type": _classify_event_type(title, "public_notice"),
                "title": title,
                "summary": record.get("summary"),
                "effective_date": None,
                "deadline_date": None,
                "published_date": _parse_date(record.get("published_date")),
                "source_url": record.get("source_url") or "https://www.zera.co.zw/press-releases-public-notices/",
                "source_system": "zera_seed",
                "source_record_id": str(record.get("source_record_id") or _slugify(title)),
                "schema_version": REGULATORY_EVENT_SCHEMA_VERSION,
                "transform_version": "zera_seed.v1",
            }
        )
    return events


def _normalize_us_manual(records: Iterable[dict[str, Any]]) -> List[dict[str, Any]]:
    events = []
    for record in records:
        title = str(record.get("title") or "").strip()
        if not title:
            continue
        events.append(
            {
                "jurisdiction": "US",
                "regulator": str(record.get("regulator") or "US Regulator"),
                "event_type": _classify_event_type(title, str(record.get("event_type") or "rulemaking")),
                "title": title,
                "summary": record.get("summary"),
                "effective_date": _parse_date(record.get("effective_date")),
                "deadline_date": _parse_date(record.get("deadline_date")),
                "published_date": _parse_date(record.get("published_date")),
                "source_url": record.get("source_url"),
                "source_system": "us_manual",
                "source_record_id": str(record.get("source_record_id") or _slugify(title)),
                "schema_version": REGULATORY_EVENT_SCHEMA_VERSION,
                "transform_version": "us_manual.v1",
            }
        )
    return events


def normalize_regulatory_events(
    records: Iterable[dict[str, Any]],
    *,
    source: str,
) -> List[dict[str, Any]]:
    """Normalize source-specific regulatory records into the shared envelope."""

    source_lower = source.lower()
    if source_lower == "nersa":
        normalized = _normalize_nersa(records)
    elif source_lower == "ippo":
        normalized = _normalize_ippo(records)
    elif source_lower in {"us_manual", "us"}:
        normalized = _normalize_us_manual(records)
    elif source_lower in {"zera_seed", "zera"}:
        normalized = _normalize_zera_seed(records)
    else:
        raise ValueError(f"Unknown regulatory source '{source}'")

    for event in normalized:
        if not event.get("source_record_id"):
            event["source_record_id"] = _stable_id(
                event.get("source_system"),
                event.get("title"),
                event.get("published_date"),
            )
    return normalized

import json
import unittest
from pathlib import Path

from odse.regulatory import (
    REGULATORY_EVENT_SCHEMA_VERSION,
    normalize_regulatory_events,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "schemas" / "regulatory-event.json"
TRANSFORM_PATH = ROOT / "transforms" / "regulatory-events-unified.yaml"
SPEC_PATH = ROOT / "spec" / "regulatory-event-normalization.md"


class RegulatoryTransformArtifactTests(unittest.TestCase):
    def test_artifacts_exist(self):
        self.assertTrue(SCHEMA_PATH.exists())
        self.assertTrue(TRANSFORM_PATH.exists())
        self.assertTrue(SPEC_PATH.exists())

    def test_schema_declares_expected_required_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            schema.get("$id"),
            "https://ona-protocol.org/schemas/v1/regulatory-event.json",
        )
        required = set(schema.get("required", []))
        self.assertTrue(
            {
                "jurisdiction",
                "regulator",
                "event_type",
                "title",
                "published_date",
                "source_url",
                "source_system",
                "source_record_id",
                "schema_version",
                "transform_version",
            }.issubset(required)
        )

    def test_runtime_normalizes_multiple_regulators_to_common_contract(self):
        events = []
        events.extend(
            normalize_regulatory_events(
                [
                    {
                        "title": "Notice of Proposed Rulemaking for regional transmission planning",
                        "published_date": "2026-03-01",
                        "source_url": "https://example.com/ferc/rm-1",
                        "source_record_id": "RM-1-2026",
                        "regulator": "FERC",
                        "event_type": "rulemaking",
                    }
                ],
                source="us_manual",
            )
        )
        events.extend(
            normalize_regulatory_events(
                [
                    {
                        "href": "file/8375",
                        "title": "Update on the MRP and Risk-Free Rate calculation for the period ended 31 December 2025",
                        "published_date": "17 February 2026",
                        "section": "recent_decisions",
                    }
                ],
                source="nersa",
            )
        )
        events.extend(
            normalize_regulatory_events(
                [
                    {
                        "id": "94e36e92-1adb-f011-8544-7c1e52501ab8",
                        "headline": "ANNOUNCEMENT OF ADDITIONAL PREFERRED BIDDERS UNDER BID WINDOW 7 OF THE RENEWABLE ENERGY INDEPENDENT POWER PRODUCER PROCUREMENT PROGRAMME",
                        "date": "12/16/2025 10:00:00 PM",
                        "noteid": "613d59d6-de10-d6db-83a6-86b1a2031c32",
                        "filename": "Final Media Statement Announcement ITP PQBs and REIPPPP BW7 15122025.pdf",
                    }
                ],
                source="ippo",
            )
        )
        events.extend(
            normalize_regulatory_events(
                [
                    {
                        "title": "Public Notice - Fuel Notice 4 October 2025",
                        "published_date": "2025-10-06",
                        "source_url": "https://www.zera.co.zw/press-releases-public-notices/",
                        "summary": "PUBLIC NOTICE: NOTIFICATION OF PETROLEUM PRODUCT PRICES",
                        "category": "Press Releases",
                    }
                ],
                source="zera_seed",
            )
        )

        self.assertEqual(len(events), 4)
        for event in events:
            self.assertEqual(event["schema_version"], REGULATORY_EVENT_SCHEMA_VERSION)
            self.assertIn("source_system", event)
            self.assertIn("source_record_id", event)
            self.assertIn("transform_version", event)
            self.assertIn("title", event)
            self.assertIn("published_date", event)

        self.assertEqual(events[0]["jurisdiction"], "US")
        self.assertEqual(events[1]["jurisdiction"], "ZA")
        self.assertEqual(events[2]["regulator"], "IPP Office")
        self.assertEqual(events[3]["jurisdiction"], "ZW")

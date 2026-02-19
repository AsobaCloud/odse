"""
ODS-E Enrichment

Post-transform context injection for settlement, tariff, and topology metadata.
"""

from typing import Any, Dict, List, Optional


def enrich(
    rows: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
    *,
    override: bool = False,
) -> List[Dict[str, Any]]:
    """
    Enrich transformed ODS-E rows with market context metadata.

    Injects settlement, tariff, topology, or arbitrary key-value pairs
    into each row. Intended as a post-transform step:

        rows = transform(data, source="huawei")
        enriched = enrich(rows, {
            "seller_party_id": "nersa:gen:SOLARPK-001",
            "buyer_party_id": "nersa:offtaker:MUN042",
            "tariff_period": "peak",
        })

    Recognized context field groups (not enforced -- any key is accepted):

    Settlement:
        seller_party_id, buyer_party_id, network_operator_id,
        wheeling_agent_id, settlement_period_start, settlement_period_end,
        loss_factor, contract_reference, settlement_type

    Tariff:
        tariff_schedule_id, tariff_period, tariff_currency,
        tariff_version_effective_at, energy_charge_component,
        network_charge_component

    Topology:
        country_code, municipality_id, municipality_name,
        distribution_zone, feeder_id, voltage_level,
        meter_id, connection_point_id, licensed_service_area

    Args:
        rows: List of ODS-E records (dicts) from transform() or transform_stream().
        context: Dict of metadata key-value pairs to inject into each row.
        override: When False (default), existing row fields are preserved
                  (source data wins). When True, context values overwrite
                  existing row fields (context wins).

    Returns:
        The same list of rows, enriched in place.
    """
    if not context or not rows:
        return rows

    for row in rows:
        for key, value in context.items():
            if not override and key in row:
                continue
            row[key] = value

    return rows

# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning.

## [Unreleased]

## [0.4.0] - 2026-02-19

### Added

- Municipal emissions modeling guide for US jurisdictions, including how-to workflows and project starter blueprints for ComStock/ResStock-based disaggregation.
- Market context extension spec for settlement party IDs, tariff context, and municipal/grid topology (`spec/market-context.md`).
- Optional settlement and tariff fields in `schemas/energy-timeseries.json` for bilateral/wheeling settlement and TOU-aware billing contexts.
- Optional South Africa-ready municipal/grid topology fields in `schemas/asset-metadata.json` location metadata.
- Market reform extensions spec aligned with SAETA "Policy to Power" report (`spec/market-reform-extensions.md`).
- Reference enrichment helper (`odse.enrich`) for post-transform injection of settlement, tariff, and topology context metadata (SEP-003).
- Wheeling transaction envelope fields in `energy-timeseries.json`: `wheeling_type`, `injection_point_id`, `offtake_point_id`, `wheeling_status`, `wheeling_path_id`.
- Unbundled tariff component fields in `energy-timeseries.json`: `generation_charge_component`, `transmission_charge_component`, `distribution_charge_component`, `ancillary_service_charge_component`, `non_bypassable_charge_component`, `environmental_levy_component`.
- Curtailment event tracking fields in `energy-timeseries.json`: `curtailment_flag`, `curtailment_type`, `curtailed_kWh`, `curtailment_instruction_id`.
- BRP and imbalance settlement fields in `energy-timeseries.json`: `balance_responsible_party_id`, `forecast_kWh`, `settlement_type`, `imbalance_kWh`.
- Municipal reconciliation fields in `energy-timeseries.json`: `billing_period`, `billed_kWh`, `billing_status`, `daa_reference`.
- Grid capacity and connection status fields in `asset-metadata.json` location: `connection_status`, `allocated_capacity_kw`, `connection_agreement_ref`, `grid_access_queue_date`, `gcar_milestone`.
- Green attribute and certificate tracking fields in `energy-timeseries.json`: `renewable_attribute_id`, `certificate_standard`, `verification_status`, `carbon_intensity_gCO2_per_kWh`.
- Runtime validator parity for all SA trading schema fields (SEP-001).
- SA trading conformance profiles with profile-level validation (SEP-002).
- Schema Extension Proposal (SEP) issue template.
- SEP process documentation in `GOVERNANCE.md` and `CONTRIBUTING.md`.

### Changed

- Schema extended from solar-only to all-utility energy sources.
- Module renamed from `ods_e` to `odse`.
- README restructured as router-style index.

### Fixed

- Long inline payload strings in path resolver.

## [0.3.0] - 2026-02-10

### Added

- Runtime transform implementations for all 10 OEMs in the support matrix.
- Transform verification harness with fixture/live/mixed modes.
- Launch kit documentation for community rollout.
- Governance policy and contributor launch documents.

### Changed

- README and API access docs expanded with concrete live harness configuration examples.

### Fixed

- Timestamp conversion updated to use timezone-aware UTC conversion.

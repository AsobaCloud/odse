# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning.

## [Unreleased]

## [0.8.1] - 2026-06-28

### Added
- Terraco SCADA historian transform (SEP-021): `TerracoTransformer` handling both JSON (REST API) and CSV (export) inputs, registered under source keys `terraco` and `terraco-historian`. Maps Terraco `{AssetName}.{TagName}` patterns to ODS-E fields with auto-detection of input format.

## [0.8.0] - 2026-06-27

### Added
- Wind turbine SCADA transforms (SEP-025): `VestasTransformer` (Vestas Online), `SiemensGamesaTransformer` (Siemens Gamesa Diagnostic System), and `NordexTransformer` (Nordex Control), registered under source keys `vestas`, `siemens_gamesa`, and `nordex`.
- Four optional wind schema fields in `energy-timeseries.json`: `wind_speed_ms`, `rotor_rpm`, `blade_pitch_deg`, and `nacelle_direction_deg` (0–360).
- `wind_scada` conformance profile requiring `wind_speed_ms`.
- Transform specifications `transforms/vestas-online.yaml`, `transforms/siemens-gamesa-diagnostic.yaml`, and `transforms/nordex-control.yaml`.
- SEP-025 spec document `spec/wind-transforms.md`.
- BESS transforms (SEP-026): `SungrowBESSTransformer` (Sungrow PowerTitan via iSolarCloud) and `BYDBESSTransformer` (BYD BatteryBox / BMS CSV export), registered under source keys `sungrow_bess` and `byd_bess`.
- Eight optional BESS schema fields in `energy-timeseries.json`: `charge_kWh`, `discharge_kWh`, `cycle_count`, `cell_temp_min_c`, `cell_temp_max_c`, `cell_voltage_min_v`, `cell_voltage_max_v`, and `dispatch_mode` (enum: charging/discharging/standby/balancing).
- `bess_dispatch` conformance profile requiring `dispatch_mode` and `soc`.
- Transform specifications `transforms/sungrow-powertitan.yaml` and `transforms/byd-bess.yaml`.
- SEP-026 spec document `spec/bess-transforms.md`.

## [0.7.0] - 2026-05-31

### Added
- Industrial connectors for MQTT and OPC-UA real-time ingestion (`odse.connectors.mqtt`, `odse.connectors.opcua`).
- SCADA (IEC 61850) and Eskom (AMR/Portal) connector specifications and implementations.
- Standardized battery storage support in energy timeseries and asset metadata schemas: `soc` (state of charge), `soh` (state of health), and `capacity_kwh`.
- MQTT ingestion configuration examples and documentation.

### Changed
- Harmonized integration documentation across all supported industrial connectors.
- Updated Sungrow inverter API access documentation.
- Refined regulatory event normalization logic and unified transform specifications.

## [0.6.0] - 2026-05-01

### Added
- Sungrow iSolarCloud API transform specification with OAuth 2.0 authentication support.
- Sungrow Python transformer implementation (`SungrowTransformer`) supporting plant_realtime, device_telemetry, and historical_data endpoints.
- Device status code mapping (16 codes) and plant status code mapping (6 codes) to ODS-E error types.
- 3-phase AC electrical parameter handling with voltage averaging and current summing.
- Multi-string DC parameter support with max voltage and summed current calculations.
- Power factor calculation from active/apparent power when not directly available.
- Comprehensive API documentation including rate limits, OAuth flow, and timezone handling.
- Support for complete ODS-E electrical parameters: kW, kWh, kVA, kVAr, PF, voltage_ac, current_ac, frequency, voltage_dc, current_dc, temperature.

## [0.5.0] - 2026-03-15

### Added
- Higeco OEM transform spec, runtime transformer, and harness fixture (SEP-019 Phase 4).
- Regulatory event normalization contract with unified transform spec and `odse.regulatory` module.
- ERP enrichment JSON schemas: equipment register, equipment ID map, failure taxonomy, maintenance history, spare parts, procurement context, alarm frequency profile.
- ERP enrichment starter notebook with SCADA alarm triage workflow and visualizations.
- IFS Cloud ERP transform spec and alarm frequency computation spec.
- CLI interface (`odse transform`, `odse validate`) with JSON/CSV/Parquet output formats (SEP-015).
- Output serialization module (`odse.io`) with `to_json`, `to_csv`, `to_parquet`, `to_dataframe` (SEP-016).
- Batch validation helper (`odse.validate_batch`) with summary reporting (SEP-018).
- Generic CSV column-mapping transformer (`source="csv"`) with kW-to-kWh fallback (SEP-020).
- SDK usage examples and fixture library: basic transform, batch directory, generic CSV, full pipeline (SEP-019).
- 60-second quickstart guide with sample CSV (SEP-028).
- Sample data fixtures for tutorials and QA: Huawei 24h, Enphase 24h, SolarEdge 24h, generic historian 7d (SEP-037).
- Winter Storm Fern analysis notebook and SMA CSV demo.
- Test scaffold for ERP enrichment schemas (52 tests).

### Fixed
- Version mismatch: synced `__version__` to 0.4.0 and removed phantom dependencies (SEP-017).

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

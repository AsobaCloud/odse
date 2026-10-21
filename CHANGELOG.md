# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning.

## [Unreleased]

## [0.11.0] - 2026-10-21

### Added
- Electrical and per-phase measurement fields in `energy-timeseries` schema (SEP-049, #56): `kW`, `kVAr`, `voltage_ac`/`voltage_ac_l1`/`_l2`/`_l3`, `current_ac`/`current_ac_l1`/`_l2`/`_l3`, `frequency`, `voltage_dc`, `current_dc`, `temperature`, `ambient_temperature_c`, `module_temperature_c`, `poa_irradiance`, `ghi`, `dni`, `dhi` — formalizing fields runtime transformers already emit, plus per-phase slots for distribution-grid unbalance analysis.
- Strict schema conformance harness (`tests/test_schema_conformance.py`, SEP-049): Draft 2020-12 validation of transformer fixture output plus a `SCHEMA_FIELDS` parity check, preventing schema/runtime drift in CI.
- Huawei FusionSolar electrical KPI ingest (SEP-051, #58): `HuaweiTransformer` now maps `a_u`/`b_u`/`c_u` to `voltage_ac_l1`/`_l2`/`_l3`, `pv1_u` to `voltage_dc`, and `active_power` to `kW`; `transforms/huawei-fusionsolar.yaml` input schema updated; new 24 h KPI fixture (`examples/data/huawei_fusionsolar_kpi_24h.csv`) including a grid over-voltage warning event (`inverter_state` 513).
- Per-phase AC emissions from `SungrowTransformer` (SEP-051, #58): `voltage_ac_l1/l2/l3` and `current_ac_l1/l2/l3` emitted alongside retained aggregates (`voltage_ac` mean, `current_ac` sum), preserving phase-unbalance information for distribution-grid analysis.
- `oem_error_code` field in `energy-timeseries` (SEP-051, #58): canonicalizes the OEM status-code emission already produced by the Solax Cloud, Sungrow, and Sungrow BESS transforms; surfaced by the SEP-049 conformance harness when Sungrow coverage was added.
- IEC 62056 (OBIS) billing-meter readings transform `iec62056_meter` (SEP-052, #59): `IEC62056MeterTransformer` decodes Huawei FusionSolar-style northbound meter exports — `Meter`/`MeterMultipliers` header plus `MeterReading[].Readings[]` with OBIS `ReadingType ref` cumulative registers — into per-interval ODS-E records. Cumulative active import (`…1.1.12`) → `direction: consumption` and export (`…1.15.12`) → `direction: generation` deltas; multipliers applied; rollover/negative deltas clamped to zero; slow counters (`1.16`–`1.19`) deferred pending semantic confirmation. First fixture: `examples/data/iec62056-meter-sibaya.json` (Sibaya billing meter, serial 10253148, 185 daily readings 2025-10-30 → 2026-05-02).
- `asset_id` field in `energy-timeseries` (SEP-052, #59): canonicalizes the inline asset identifier emitted by multiple transformers (Huawei, Solax Cloud, and now the meter transform) and the meter transform's serial-number-derived record identity; optional string, additive.

### Changed
- `validate()` now emits non-fatal `UNKNOWN_FIELD` warnings for keys outside the canonical schema (SEP-049); `is_valid` semantics unchanged.

## [0.10.0] - 2026-10-13

### Added
- OpenOA (Open Operational Assessment) interoperability adapter (`odse.adapters.openoa`):
  - `odse_to_openoa()`: Converts ODS-E JSON/JSONL into UTC-indexed pandas DataFrames (`scada`, `tower`, `meter`) or OpenOA `PlantData` objects.
  - `openoa_to_odse()`: Exports OpenOA analysis DataFrames back into standard ODS-E JSON dictionary payloads with sanitized nulls.
  - Optional dependency extra `odse[openoa]` with `openoa>=2.0.0` and `pandas>=1.5.0`.
- Top-level CLI subcommand `to-openoa` (aliased as `openoa`) for converting ODS-E telemetry to OpenOA tables.
- Comprehensive OpenOA integration specification and edge-case troubleshooting documentation (`spec/openoa-integration.md`).

## [0.9.0] - 2026-10-13

### Added
- pvlib-python interoperability adapter (`odse.adapters.pvlib`):
  - `odse_to_pvlib()`: Converts ODS-E JSON/JSONL into UTC-indexed pandas DataFrames conforming to `pvlib.iotools` convention.
  - `pvlib_to_odse()`: Exports simulated pvlib DataFrames back into standard ODS-E JSON dictionary payloads.
  - Optional dependency extra `odse[pvlib]` with `pvlib>=0.10.0` and `pandas>=1.5.0`.
- Top-level CLI subcommand `to-pvlib` (aliased as `pvlib`) for converting ODS-E telemetry to CSV, JSON, or Parquet.
- Comprehensive pvlib integration guide and edge-case troubleshooting documentation (`spec/pvlib-integration.md`).

## [0.8.2] - 2026-06-28

### Fixed
- Logo image now uses absolute GitHub raw URL so it renders on PyPI (previously used relative path `assets/odse.png` which only worked on GitHub).

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

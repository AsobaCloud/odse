# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning.

## [Unreleased]

### Added

- Municipal emissions modeling guide for US jurisdictions, including how-to workflows and project starter blueprints for ComStock/ResStock-based disaggregation.
- Market context extension spec for settlement party IDs, tariff context, and municipal/grid topology (`spec/market-context.md`).
- Optional settlement and tariff fields in `schemas/energy-timeseries.json` for bilateral/wheeling settlement and TOU-aware billing contexts.
- Optional South Africa-ready municipal/grid topology fields in `schemas/asset-metadata.json` location metadata.
- TBD

### Changed

- TBD

### Fixed

- TBD

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

<p align="center">
  <img src="https://raw.githubusercontent.com/AsobaCloud/odse/main/assets/odse.png" width="180" alt="ODS-E Logo" />
</p>

<h1 align="center">ODS-E — Open Data Schema for Energy</h1>

<p align="center">
  <strong>An open specification for interoperable energy asset data across generation, consumption, and net metering.</strong>
</p>

<p align="center">
  <a href="https://creativecommons.org/licenses/by-sa/4.0/">
    <img src="https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg" alt="License: CC BY-SA 4.0">
  </a>
  <a href="https://opensource.org/licenses/Apache-2.0">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache 2.0">
  </a>
  <a href="https://github.com/AsobaCloud/odse/actions/workflows/ci.yml">
    <img src="https://github.com/AsobaCloud/odse/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://github.com/AsobaCloud/odse/releases">
    <img src="https://img.shields.io/github/v/release/AsobaCloud/odse?style=flat" alt="Release">
  </a>
  <a href="https://github.com/AsobaCloud/odse/commits/main">
    <img src="https://img.shields.io/github/last-commit/AsobaCloud/odse/main" alt="Last Commit">
  </a>
</p>

<p align="center">
  <a href="#start-here">Start Here</a> •
  <a href="#repository-map">Repository Map</a> •
  <a href="#for-implementers">For Implementers</a> •
  <a href="#project">Project</a> •
  <a href="#license">License</a>
</p>

---

ODS-E is an open specification for interoperable energy asset data across generation, consumption, and net metering. It ships with versioned schemas, vendor transforms, a Python reference runtime, and integration guides for inverters, industrial protocols, SCADA, and utility data portals.

## Start Here

- [Documentation Site](https://opendataschema.energy/docs/)
- [Documentation Source Repo](https://github.com/AsobaCloud/odse-docs/)
- [Launch Kit](spec/launch-kit.md)
- [60-second quickstart](spec/get-started.md)

## Repository Map

- [Specification docs](spec/)
- [Schemas](schemas/)
- [Transforms](transforms/) (Huawei, Eskom, etc.)
- [Python reference runtime](src/python/) (including SCL, AMR, MQTT, and OPC-UA connectors)
- [Tools](tools/)
- [Demos](demos/)

## For Implementers

- [Schema: `energy-timeseries.json`](schemas/energy-timeseries.json)
- [Schema: `asset-metadata.json`](schemas/asset-metadata.json)
- [Transform harness usage](tools/transform_harness.py)

### Integration Guides

- [Inverter API access setup](spec/inverter-api-access.md)
- [Industrial Protocols (MQTT, OPC-UA)](spec/industrial-connectors.md)
- [SCADA (IEC 61850) Integration](spec/scada-integration.md)
- [Eskom Ingest (AMR, Data Portal)](spec/eskom-ingest.md)

### Modeling & Markets

- [ComStock/ResStock integration](spec/comstock-integration.md)
- [Municipal emissions modeling guide](spec/municipal-emissions-modeling.md)
- [Market context extensions (settlement, tariff, topology)](spec/market-context.md)
- [Market reform extensions (wheeling, curtailment, BRP, certificates)](spec/market-reform-extensions.md)
- [SA trading conformance profiles (SEP-002)](spec/conformance-profiles.md)
- [Reference enrichment contract (SEP-003)](spec/market-context.md)
- [Python SDK examples](examples/README.md)

## Project

- [Contributing](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## License

- Specification, schemas, transforms: [CC-BY-SA 4.0](LICENSE-SPEC.md)
- Reference implementation and tools: [Apache 2.0](LICENSE-CODE.md)

---

Maintained by [Asoba Corporation](https://asoba.co)

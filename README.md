# ODS-E: Open Data Schema for Energy

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/AsobaCloud/odse/actions/workflows/ci.yml/badge.svg)](https://github.com/AsobaCloud/odse/actions/workflows/ci.yml)

ODS-E is an open specification for interoperable energy asset data across generation, consumption, and net metering.

## Start Here

- [Documentation Site](https://opendataschema.energy/docs/)
- [Documentation Source Repo](https://github.com/AsobaCloud/odse-docs/)
- [Launch Kit](spec/launch-kit.md)

## Repository Map

- [Specification docs](spec/)
- [Schemas](schemas/)
- [Transforms](transforms/)
- [Python reference runtime](src/python/)
- [Tools](tools/)
- [Demos](demos/)

## For Implementers

- [Schema: `energy-timeseries.json`](schemas/energy-timeseries.json)
- [Schema: `asset-metadata.json`](schemas/asset-metadata.json)
- [Transform harness usage](tools/transform_harness.py)
- [Inverter API access setup](spec/inverter-api-access.md)
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

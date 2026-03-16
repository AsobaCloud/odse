# ODS-E Launch Kit (Community Promotion)

This package is designed for immediate outreach to climate-tech partners, accelerators, and deployment teams.

Last updated: 2026-02-16

## 1) Release Notes Template

Use this template for each tagged release.

```markdown
# ODS-E Release vX.Y.Z
Release date: YYYY-MM-DD

## Summary
- One-paragraph overview of what changed and why it matters to implementers.

## What is stable in this release
- Schema version(s):
- Runtime transform sources:
- Validation surface:

## Added
- Item

## Changed
- Item

## Fixed
- Item

## Breaking changes
- None / list each with migration action.

## Migration notes
- Exact command(s) and config changes required.

## Verification
- Unit tests: `<count>`
- Harness run mode(s): `fixture|mixed|live`
- Known limitations: list

## Upgrade command
```bash
pip install -U odse==X.Y.Z
```
```

## 2) Public Support Matrix Template

Publish this matrix in docs and outreach posts.

| OEM | Transform Spec | Runtime Function | Live-Tested Evidence | Access Path |
|-----|----------------|------------------|----------------------|------------|
| Huawei | Yes | Yes | Production | FusionSolar Northbound |
| Switch | Yes | Yes | Production | Vendor/customer feed |
| Enphase | Yes | Yes | Demo-ready | Enphase developer app |
| SMA | Yes | Yes | Demo-ready | SMA sandbox + OAuth |
| Fronius | Yes | Yes | Demo-ready (local) | Local inverter API |
| SolarEdge | Yes | Yes | Account-required | Monitoring API key |
| FIMER | Yes | Yes | Account-required | Aurora Vision enablement |
| Solis | Yes | Yes | Partner-gated | SolisCloud onboarding |
| SolaX | Yes | Yes | Account-required | SolaX tokenId |
| Solarman | Yes | Yes | Account/file feed | Logger exports/API |
| Higeco | Yes | Yes | Partner-gated | Higeco docAPI bearer token |

### Consumption & Net Metering Sources (Schema Ready)

| Source Type | Schema Support | Runtime Transform | Notes |
|-------------|---------------|-------------------|-------|
| Grid meter (consumption) | Yes (`direction: consumption`) | Planned | Via utility CSV / Green Button |
| Net meter | Yes (`direction: net`) | Planned | kWh may be negative |
| Sub-meter (end-use) | Yes (`end_use` field) | Planned | ComStock-aligned categories |
| Non-electric (gas, propane) | Yes (`fuel_type` field) | Planned | Supports multi-fuel buildings |

### Matrix Rules

- `Transform Spec` means YAML transform spec exists in `transforms/`.
- `Runtime Function` means `odse.transform(..., source=...)` is implemented.
- `Live-Tested Evidence` must reference date + account class used (sandbox, demo, or production).

## 3) Start Here (15-Minute Setup)

```bash
git clone https://github.com/AsobaCloud/odse.git
cd odse
python3 -m venv .venv
source .venv/bin/activate
pip install -e src/python
```

Run fixture verification for all transform runtimes:

```bash
PYTHONPATH=src/python python3 tools/transform_harness.py --mode fixture
```

Run mixed verification with optional live sources:

```bash
cp .env.example .env
PYTHONPATH=src/python python3 tools/transform_harness.py --mode mixed --oems all
```

Run only demo-friendly live candidates:

```bash
PYTHONPATH=src/python python3 tools/transform_harness.py --mode live --oems enphase,sma,fronius
```

### Validate a Consumption Record

```python
from odse import validate

result = validate({
    "timestamp": "2026-02-16T10:00:00Z",
    "kWh": 3.7,
    "error_type": "normal",
    "direction": "consumption",
    "end_use": "cooling",
    "fuel_type": "electricity"
})
print(result.is_valid)  # True
```

## 4) Design Partner Onboarding Checklist

Use this with each external pilot entity.

1. Verify target OEM(s) and access class (`demo`, `sandbox`, `customer account`, `production`).
2. Confirm API credentials and test endpoint availability.
3. Run harness in `fixture` mode and capture baseline.
4. Run harness in `live` mode for agreed OEMs and capture output.
5. Validate transformed records include `timestamp`, `kWh`, and `error_type`.
6. If consumption/building use case: confirm `direction`, `end_use`, and `fuel_type` field usage.
7. If building benchmark use case: populate `building` metadata in asset-metadata (see [ComStock/ResStock Integration](comstock-integration.md)).
8. Record any OEM-specific normalization assumptions.
9. Confirm data retention, rate-limit, and retry policy.
10. Finalize "go/no-go" decision for production connector rollout.

## 5) Promotion Assets Checklist

Before public promotion, ensure these exist:

- Tagged release with release notes (`vX.Y.Z`).
- Public support matrix with evidence dates.
- One end-to-end quickstart demo (copy-paste runnable).
- One short architecture diagram (ingest -> transform -> validate -> consumer).
- Security/privacy statement for credential handling.
- Contribution guide for adding OEM mappings and tests.
- ComStock/ResStock integration stub for building performance partners ([spec/comstock-integration.md](comstock-integration.md)).

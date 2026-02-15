# ODS-E Launch Kit (Community Promotion)

This package is designed for immediate outreach to climate-tech partners, accelerators, and deployment teams.

Last updated: 2026-02-10

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

## 4) Design Partner Onboarding Checklist

Use this with each external pilot entity.

1. Verify target OEM(s) and access class (`demo`, `sandbox`, `customer account`, `production`).
2. Confirm API credentials and test endpoint availability.
3. Run harness in `fixture` mode and capture baseline.
4. Run harness in `live` mode for agreed OEMs and capture output.
5. Validate transformed records include `timestamp`, `kWh`, and `error_type`.
6. Record any OEM-specific normalization assumptions.
7. Confirm data retention, rate-limit, and retry policy.
8. Finalize “go/no-go” decision for production connector rollout.

## 5) Promotion Assets Checklist

Before public promotion, ensure these exist:

- Tagged release with release notes (`vX.Y.Z`).
- Public support matrix with evidence dates.
- One end-to-end quickstart demo (copy-paste runnable).
- One short architecture diagram (ingest -> transform -> validate -> consumer).
- Security/privacy statement for credential handling.
- Contribution guide for adding OEM mappings and tests.

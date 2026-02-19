# Governance

This document defines how ODS-E decisions are made, who can approve changes, and how compatibility is protected for adopters.

Last updated: 2026-02-19

## Scope

ODS-E includes:

- Specification artifacts: schemas, transforms, and normative documentation.
- Runtime artifacts: Python implementation, tooling, and harness scripts.

## Roles

### Project Lead

- Holds final tie-break authority when maintainers cannot reach consensus.
- Approves major governance or strategy changes.

### Maintainers

- Review and merge pull requests.
- Triage issues, label changes, and enforce compatibility policy.
- Manage release readiness.

### Contributors

- Submit issues and pull requests.
- Follow contribution, security, and compatibility requirements.

## Decision Classes

### Routine

Examples:

- Documentation clarity updates.
- New tests.
- Non-breaking runtime bug fixes.
- Tooling improvements that do not change normative behavior.

Approval:

- 1 maintainer approval.

### Normative

Examples:

- Changes to schema required fields or enums.
- Changes to transform semantics.
- Changes to error taxonomy behavior.
- Deprecation notices for source keys or behaviors.

Approval:

- 2 maintainer approvals.
- Minimum 7-day public comment window before merge.

### Breaking

Examples:

- Removing or changing meaning of existing schema/runtime behavior.
- Removing supported source keys.
- Any change requiring adopter migration.

Approval:

- 2 maintainer approvals plus Project Lead sign-off.
- Explicit migration notes required in release notes.

### Security

Examples:

- Credential handling flaws.
- Vulnerability fixes.
- Supply-chain or dependency risk remediations.

Approval:

- Maintainer + security reviewer (or Project Lead when unavailable).
- May use private disclosure flow until patch is available.

## Compatibility Policy

1. No silent semantic changes to existing fields.
2. Existing source keys should remain functional for at least one minor release after deprecation notice.
3. Breaking changes require explicit migration guidance.
4. Additive changes (new OEMs, optional fields, new tooling) are preferred for minor releases.

## Schema Extension Proposals (SEP)

Changes to schemas, normative field definitions, or structural extensions follow the SEP process.

### When to use a SEP

A SEP is required for:

- Adding or modifying fields in `schemas/energy-timeseries.json` or `schemas/asset-metadata.json`.
- Adding or changing enum values, required fields, or validation constraints.
- Defining new conformance profiles or enrichment contracts.

A SEP is not required for routine changes (documentation fixes, new tests, tooling improvements).

### SEP lifecycle

1. **Proposal.** Open a Schema Extension Proposal issue using the issue template. Assign the next sequential SEP number (e.g. SEP-004).
2. **Discussion.** The proposal follows the decision class rules above: normative SEPs require a 7-day comment window; breaking SEPs require Project Lead sign-off.
3. **Draft spec.** Accepted proposals are implemented as spec documents in `spec/` with the header format: title including `(SEP-NNN)`, `Status: Draft`, and `Last updated` date.
4. **Implementation.** Schema changes, runtime updates, and tests are submitted as pull requests referencing the SEP number.
5. **Finalization.** Once merged and released, the spec status is updated to `Active`.

### SEP numbering

SEP numbers are assigned sequentially and never reused. Current allocations:

- SEP-001: Runtime validator parity for SA trading schema fields.
- SEP-002: SA trading conformance profiles.
- SEP-003: Reference enrichment contract.

## Labels and Workflow

Recommended pull request labels:

- `spec`
- `runtime`
- `breaking`
- `security`
- `docs`

Workflow baseline:

1. Open issue or proposal.
2. Classify decision type (`routine`, `normative`, `breaking`, `security`).
3. Merge when approval threshold is met.
4. Document impact in changelog/release notes.

## Release Governance

Release cadence:

- Minor releases on a predictable cadence (for example monthly).
- Patch releases as needed.

Release checklist:

1. Unit tests pass.
2. Transform harness fixture mode passes.
3. Changelog/release notes updated.
4. Migration notes included for normative or breaking changes.
5. Documentation links remain current.

## Conflict Resolution

If maintainers disagree:

1. Attempt consensus in issue/PR discussion.
2. If unresolved, escalate to Project Lead for final decision.

## Governance Changes

Changes to this document are normative and require:

- 2 maintainer approvals, and
- Project Lead sign-off.

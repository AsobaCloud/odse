# Governance

This document defines how ODS-E decisions are made, who can approve changes, and how compatibility is protected for adopters.

Last updated: 2026-02-10

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

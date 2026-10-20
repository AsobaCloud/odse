# ODS-E Project Governance

This document defines how decision making, maintainership, pull request approvals, and release governance operate within the Open Data Schema for Energy (ODS-E) project.

**Last updated:** 2026-10-20  
**Status:** Active (v2.0)

---

## 1. Scope & Architecture

ODS-E governance applies to all repository assets across two core layers:
* **Specification Artifacts**: JSON Schemas (`schemas/`), declarative YAML OEM transforms (`src/python/odse/transforms/`), Schema Extension Proposals (`spec/`), and normative documentation.
* **Runtime Artifacts**: Python SDK implementation (`src/python/odse/`), CLI tooling (`nehanda-cli`, `@asobacloud/odse-mcp`), testing harnesses, and CI/CD pipelines.

---

## 2. Roles & "The Open Team" Model

ODS-E operates under **The Open Team** model: community engineers, university researchers, and AI coding agents are held to the same technical standards and treated with equal respect.

### A. Project Lead
* Holds final tie-break authority when maintainers cannot reach consensus.
* Approves breaking changes and major governance/strategic shifts.
* Manages maintainer onboarding and offboarding.

### B. Maintainers
* Review and merge pull requests according to decision class approval rules.
* Triage issues, label PRs (`spec`, `runtime`, `breaking`, `good-first-issue`), and enforce compatibility policies.
* Manage release readiness and test harness validation.

### C. Contributors (Human & AI Coding Agents)
* Submit issues, Schema Extension Proposals (SEPs), and pull requests.
* Follow contribution guidelines (`CONTRIBUTING.md`), behavioral testing standards, and git hygiene.
* **AI Agent Mandate**: AI coding agents operating on the codebase are subject to the same governance, issue-linking (`fix: description (#123)`), TDD validation, and PR approval thresholds as human contributors.

---

## 3. Pathway to Maintainership

We actively grow our maintainer team through meritocratic community participation.

### Onboarding Criteria
A contributor may be nominated for Maintainer status by demonstrating:
1. **Sustained Contributions**: A track record of high-quality merged PRs (e.g., 5+ OEM transform specs, runtime bug fixes, or documentation enhancements).
2. **Standard & Quality Alignment**: Mastery of ODS-E compatibility rules, Given-When-Then behavioral testing, and clean commit history.
3. **Constructive Code Review**: Helpful, detailed PR feedback and triage assistance for other community members.

### Nomination & Approval
* Any existing Maintainer may nominate a candidate.
* Requires **2 Maintainer approvals** and **Project Lead sign-off**.

---

## 4. Decision Classes & Approval Thresholds

To maintain rapid development velocity without risking breaking schema changes, decisions are classified into four distinct tiers:

### Tier 1: Routine (Velocity & Unblocked Community Ramp)
**Examples:**
* **Additive OEM Declarative Transforms**: Adding or updating vendor YAML specs in `src/python/odse/transforms/*.yaml` that map vendor keys to existing canonical ODS-E fields without altering core JSON Schemas.
* Documentation, Codelabs, and tutorial clarity updates.
* New unit or behavioral test additions.
* Non-breaking runtime bug fixes and tooling improvements.

**Approval Rule:**
* **1 Maintainer approval**. No public comment window required. Fast-track merge for `good-first-issue` contributions.

---

### Tier 2: Normative (Specification & Schema Semantics)
**Examples:**
* Adding or modifying optional/required fields in core JSON Schemas (`schemas/energy-timeseries.json`, `schemas/asset-metadata.json`).
* Changes to transform execution semantics or the 7-category error taxonomy behavior.
* Deprecation notices for existing source keys or SDK interfaces.

**Approval Rule:**
* **2 Maintainer approvals**.
* **Minimum 7-day public comment window** on the issue or SEP before merging.

---

### Tier 3: Breaking (Backward Compatibility & Migration)
**Examples:**
* Removing or changing the normative meaning of existing schema fields or runtime APIs.
* Removing supported OEM source keys.
* Any change requiring adopter data migration or pipeline rewrites.

**Approval Rule:**
* **2 Maintainer approvals + Project Lead sign-off**.
* Explicit migration notes required in release documentation.

---

### Tier 4: Security (Vulnerability & Supply Chain Remediation)
**Examples:**
* Vulnerability fixes in dependencies, CLI tools, or runtime converters.
* Credential or token handling flaw remediation.

**Approval Rule:**
* **1 Maintainer + Security Lead / Project Lead sign-off**.
* May use private disclosure flows per `SECURITY.md` until a patch is released.

---

## 5. Compatibility Policy

1. **Zero Silent Semantic Drift**: Field meanings and canonical schema types must not change without a major version bump or formal SEP.
2. **Deprecation Grace Period**: Deprecated source keys or SDK methods must remain functional for at least one minor release cycle following deprecation notices.
3. **Additive Preference**: New OEM mappings, optional fields, and expanded adapters (`pvlib`, `OpenOA`) are strongly preferred as minor/patch releases.

---

## 6. Schema Extension Proposals (SEPs)

Structural changes to core schemas, normative field definitions, or new domain profiles follow the **Schema Extension Proposal (SEP)** RFC process.

### SEP Lifecycle
1. **Proposal**: Open an issue using the *Schema Extension Proposal* template and assign the next sequential number (e.g., `SEP-004`).
2. **Discussion**: Community review following Tier 2 (Normative) or Tier 3 (Breaking) comment rules.
3. **Draft Spec**: Document spec details under `spec/SEP-NNN.md` with status `Draft`.
4. **Implementation**: Code changes, YAML specs, and tests reference the SEP number (`feat: add wind turbine fields (SEP-025)`).
5. **Finalization**: Merged and tagged as `Active` in `GOVERNANCE.md`.

### Active SEP Index
* **SEP-001**: Runtime validator parity for SA trading schema fields.
* **SEP-002**: SA trading conformance profiles.
* **SEP-003**: Reference enrichment contract.
* **SEP-025**: Wind turbine SCADA transforms (Vestas, Siemens Gamesa, Nordex) and wind schema fields.
* **SEP-026**: BESS transforms (Sungrow PowerTitan, BYD) and dispatch schema fields.

---

## 7. Pull Request & Release Checklists

### Pull Request Merge Criteria
Before any PR is merged, it must satisfy:
1. **Issue Reference**: Linked to an open GitHub issue (`fix: description (#123)`).
2. **Behavioral Spec Evidence**: Includes Given-When-Then test coverage verifying observable outcomes.
3. **Harness Verification**: Passing `PYTHONPATH=src/python python3 tools/transform_harness.py --mode fixture`.
4. **Contract Synchronization**: If storage backends, SDK interfaces, or schemas change, update `docs/MAP.md` and contract docs in the same PR.
5. **Clean History**: Zero AI assistant attribution watermarks or co-author clutter in git commits.

### Release Governance
* **Minor Releases**: Monthly cadence or upon major OEM/SEP bundle completions.
* **Patch Releases**: As needed for bug or security fixes.
* **Release Verification**: All automated safety checkers pass (`python-safety-checker.py`), changelog updated, and migration guides attached if applicable.

---

## 8. Conflict Resolution & Governance Edits

If Maintainers cannot reach consensus on a PR or SEP:
1. Conduct open technical discussion on the GitHub issue.
2. If unresolved after 5 business days, escalate to the **Project Lead** for final tie-break decision.

Changes to `GOVERNANCE.md` itself are Tier 2 (Normative) and require **2 Maintainer approvals + Project Lead sign-off**.

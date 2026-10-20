# Contributing to Open Data Schema for Energy (ODS-E)

Thank you for your interest in contributing to **ODS-E**!

ODS-E is the open data interchange standard for renewable energy asset performance, SCADA telemetry, and operational intelligence. Whether you are adding a new OEM transformer, refining physics adapters (`pvlib`, `OpenOA`), improving documentation, or fixing bugs, your contributions help eliminate the "80% parser tax" across the clean energy industry.

---

## 1. Our Philosophy: "The Open Team" Model

We manage ODS-E under **The Open Team** model:
* **Equal Rigor & Respect**: Community contributors—whether human engineers, researchers, or AI coding agents—are treated as core members of our engineering team.
* **Mentorship Through Quality**: We maintain a high technical bar and do not "rubber-stamp" pull requests. Constructive, detailed code reviews ensure you level up your engineering craft while keeping the ODS-E specification rock-solid and enterprise-ready.
* **Public-First Engineering**: All design discussions, RFCs, and bug triage happen transparently on GitHub issues and pull requests.

---

## 2. Quick Ramp: "Good First Issues" (15-Minute Contributions)

Looking for a fast, high-impact way to get started? We tag beginner-friendly tasks with **`good-first-issue`** and **`help-wanted`**.

### The 15-Minute OEM Transform Challenge
The fastest way to contribute is adding a declarative YAML transform spec for an inverter, battery, or meter OEM in `src/python/odse/transforms/`:
1. Pick an unmapped OEM (e.g., Sungrow, Fronius, BYD BESS, Solax, GoodWe).
2. Create a new `transforms/{oem_name}.yaml`mapping vendor field names to canonical ODS-E keys (`timestamp`, `kwh`, `error_type`, `active_power_kWh`).
3. Add a sample CSV fixture to `tests/fixtures/{oem_name}_raw.csv`.
4. Validate with `python3 tools/transform_harness.py --mode fixture`.
5. Open your PR!

---

## 3. Engineering Mandates & Quality Standards

To maintain standard integrity and maintainability, all contributors must adhere to our core engineering principles:

### A. No Code Without an Issue
Every pull request must reference an open GitHub Issue. Format commit titles and PR descriptions as `fix: description (#123)` or `feat: description (#123)`.

### B. Explore & Plan Before Coding
* **Search First**: Search existing code (`grep`, `glob`) before creating new utility functions. Never introduce duplicate helper methods.
* **Draft a Plan**: For non-trivial runtime or spec changes, outline your proposed approach in the issue before writing code.

### C. Behavior-First Validation & TDD Standard
* **Test-Driven Development (TDD)**: Create or update a behavioral test *before* implementing feature logic or fixes.
* **Verify System Outcomes**: Unit tests must verify observable behavioral outcomes (e.g., "The transformed DataFrame produces valid UTC timestamps and non-zero kWh under valid irradiances"), not internal implementation details or trivial function signatures.
* **Realistic Mocking**: Mocks are permitted for external network/AWS services, but **strictly prohibited** for the specific functions being modified.
* **The Canary Test Rule**: Ask yourself before submitting: *"Would this test fail if the implementation produced the wrong output?"* If no, strengthen the test assertions.

### D. Zero Root Clutter
The project root directory is a protected zone. Contributors must never commit diagnostic scripts, temporary JSON outputs, or scratch CSV exports to the root directory. Store temporary artifacts in `/tmp/` or designated test directories.

### E. Atomic Commits & Clean Git History
* Keep commits focused, logical, and written in the imperative mood (`fix: resolve UTC offset parsing in Huawei transform`).
* **Keep AI Assistant Branding Out of Git**: Keep automated AI coder attributions, tool watermarks, or co-author footers out of commit messages and PR bodies. We value clean, professional git histories focused purely on the technical change.

### F. Documentation & Contract Synchronization
If a change modifies schema definitions, storage backends, or public SDK interfaces, you *must* update the corresponding specification docs (`docs/MAP.md`, `README.md`, or schema specs) in the *same* pull request.

---

## 4. Local Development Setup

Clone the repository and set up a Python 3.10+
virtual environment:

```bash
# Clone the repository
git clone https://github.com/AsobaCloud/odse.git
cd odse

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the package in editable mode with development dependencies
pip install -e "src/python[dev]"
```

---

## 5. Local Validation & Testing Harness

Before submitting a pull request, ensure all local tests and validation checkers pass:

### Run Unit and Behavioral Tests
```bash
PYTHONPATH=src/python python3 -m unittest discover -s src/python/tests -v
```

### Run the Transform Harness
Verify that all declarative YAML transforms parse their corresponding test fixtures correctly:
```bash
PYTHONPATH=src/python python3 tools/transform_harness.py --mode fixture
```

### Run Code Quality & Safety Checkers
```bash
# Verify Python safety, typing, and formatting
python3 scripts/python-safety-checker.py
```

---

## 6. Pull Request Guidelines

When submitting a pull request, ensure your PR description includes:

1. **Issue Reference**: Clear link to the GitHub issue (`Fixes #123`).
2. **Change Type Label**: Apply the appropriate label:
   * `spec`: Normative schema or field definition change.
   * `runtime`: Python SDK or converter logic change.
   * `breaking`: Backward-incompatible schema or API change.
   * `security`: Vulnerability patch.
   * `docs`: Documentation or tutorial update.
3. **Behavioral Specification (Given-When-Then)**:
   * **Given** a raw SolarEdge CSV with local timestamp offsets,
   * **When** passed through `odse.transform()`,
   * **Then** return normalized ISO-8601 utc records with mapped `kWh` values.
4. **Harness Evidence**: Output logs showing passing unit tests and `transform_harness.py` execution.

---

## 7. Schema Extension Proposals (SEPs)

Changes to core JSON Schemas or normative field definitions require a **Schema Extension Proposal (SEP)**:
 * Open an issue using the **Schema Extension Proposal** template.
 * Follow the SEP RFC lifecycle documented in `GOVERNANCE.md`.
 * Normative changes require consensus from the ODS-E Technical Steering Committee (TSC).

---

## 8. Reporting Security Vulnerabilities

Please do *not* report security vulnerabilities in public GitHub issues. Refer to [SECURITY.md](SECURITY.md) for instructions on responsible disclosure to the security team.

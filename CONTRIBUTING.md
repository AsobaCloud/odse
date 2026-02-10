# Contributing to ODS-E

Thanks for contributing to ODS-E.

This guide covers setup, validation, and pull request expectations.

## Development Setup

```bash
git clone https://github.com/AsobaCloud/odse.git
cd odse
python3 -m venv .venv
source .venv/bin/activate
pip install -e src/python
```

## Validate Changes Locally

Run unit tests:

```bash
PYTHONPATH=src/python python3 -m unittest discover -s src/python/tests -v
```

Run transform harness (fixture mode):

```bash
PYTHONPATH=src/python python3 tools/transform_harness.py --mode fixture
```

## Change Types

Use these labels in pull requests:

- `spec`
- `runtime`
- `breaking`
- `security`
- `docs`

Decision and approval rules are defined in `GOVERNANCE.md`.

## Pull Request Requirements

1. Explain what changed and why.
2. State whether the change is `routine`, `normative`, `breaking`, or `security`.
3. Include tests or harness evidence for behavior changes.
4. Update documentation for user-facing behavior changes.
5. Include migration notes for breaking changes.

## Commit Guidance

- Keep commits focused and atomic.
- Use clear commit messages in imperative mood.
- Do not include secrets or credentials.

## Reporting Issues

- Use issue templates in `.github/ISSUE_TEMPLATE`.
- For vulnerabilities, use `SECURITY.md` instead of public issues.

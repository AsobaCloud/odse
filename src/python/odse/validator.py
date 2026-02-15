"""
ODS-E Validator

Validates energy data against ODS-E JSON schemas.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class ValidationError:
    """Represents a validation error."""
    path: str
    message: str
    code: str


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    level: str = "schema"


def validate(
    data: Union[dict, str, Path],
    level: str = "schema",
    capacity_kw: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> ValidationResult:
    """
    Validate data against ODS-E production-timeseries schema.

    Args:
        data: Dictionary, JSON string, or path to JSON file
        level: Validation level - "schema" or "semantic"
        capacity_kw: Asset capacity in kW (required for semantic validation)
        latitude: Asset latitude (optional, for nighttime checks)
        longitude: Asset longitude (optional, for nighttime checks)

    Returns:
        ValidationResult with is_valid status and any errors/warnings
    """
    # Parse input
    if isinstance(data, (str, Path)):
        if Path(data).exists():
            with open(data) as f:
                data = json.load(f)
        else:
            data = json.loads(data)

    errors = []
    warnings = []

    # Schema validation
    errors.extend(_validate_schema(data))

    # Semantic validation
    if level == "semantic" and not errors:
        sem_errors, sem_warnings = _validate_semantic(
            data, capacity_kw, latitude, longitude
        )
        errors.extend(sem_errors)
        warnings.extend(sem_warnings)

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        level=level,
    )


def validate_file(
    file_path: Union[str, Path],
    level: str = "schema",
    **kwargs,
) -> ValidationResult:
    """
    Validate a JSON file containing ODS-E data.

    Args:
        file_path: Path to JSON file
        level: Validation level
        **kwargs: Additional arguments passed to validate()

    Returns:
        ValidationResult
    """
    return validate(Path(file_path), level=level, **kwargs)


def _validate_schema(data: dict) -> List[ValidationError]:
    """Validate against JSON schema."""
    errors = []

    # Required fields
    required = ["timestamp", "kWh", "error_type"]
    for field in required:
        if field not in data:
            errors.append(ValidationError(
                path=f"$.{field}",
                message=f"Required field '{field}' is missing",
                code="REQUIRED_FIELD_MISSING",
            ))

    if errors:
        return errors

    # Type validation
    if not isinstance(data.get("kWh"), (int, float)):
        errors.append(ValidationError(
            path="$.kWh",
            message=f"Expected number, got {type(data.get('kWh')).__name__}",
            code="TYPE_MISMATCH",
        ))

    # Enum validation
    valid_error_types = [
        "normal", "warning", "critical", "fault",
        "offline", "standby", "unknown"
    ]
    if data.get("error_type") not in valid_error_types:
        errors.append(ValidationError(
            path="$.error_type",
            message=f"Value '{data.get('error_type')}' not in enum {valid_error_types}",
            code="ENUM_MISMATCH",
        ))

    # Bounds validation
    if isinstance(data.get("kWh"), (int, float)) and data["kWh"] < 0:
        errors.append(ValidationError(
            path="$.kWh",
            message="kWh must be >= 0",
            code="OUT_OF_BOUNDS",
        ))

    if "PF" in data:
        pf = data["PF"]
        if isinstance(pf, (int, float)) and (pf < 0 or pf > 1):
            errors.append(ValidationError(
                path="$.PF",
                message="Power factor must be between 0 and 1",
                code="OUT_OF_BOUNDS",
            ))

    return errors


def _validate_semantic(
    data: dict,
    capacity_kw: Optional[float],
    latitude: Optional[float],
    longitude: Optional[float],
) -> tuple:
    """Validate semantic constraints."""
    errors = []
    warnings = []

    # Physical bounds check
    if capacity_kw and isinstance(data.get("kWh"), (int, float)):
        # Assume 1-hour interval for simplicity
        max_kwh = capacity_kw * 1.1
        if data["kWh"] > max_kwh:
            warnings.append(ValidationError(
                path="$.kWh",
                message=f"kWh ({data['kWh']}) exceeds maximum possible ({max_kwh}) for {capacity_kw}kW capacity",
                code="EXCEEDS_PHYSICAL_MAXIMUM",
            ))

    # State/production consistency
    if data.get("error_type") == "offline" and data.get("kWh", 0) > 10:
        warnings.append(ValidationError(
            path="$",
            message=f"Significant production ({data['kWh']} kWh) reported with error_type 'offline'",
            code="STATE_PRODUCTION_MISMATCH",
        ))

    return errors, warnings

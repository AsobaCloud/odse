"""
ODS-E Validator

Validates energy data against ODS-E JSON schemas.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union


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


@dataclass
class BatchValidationResult:
    """Aggregated validation result for a batch of records."""
    total: int
    valid: int
    invalid: int
    errors: List[Tuple[int, ValidationError]]
    summary: str


PROFILES = {
    "bilateral": {
        "required_fields": [
            "seller_party_id", "buyer_party_id",
            "settlement_period_start", "settlement_period_end",
            "contract_reference", "settlement_type",
        ],
        "field_constraints": {
            "settlement_type": ["bilateral"],
        },
    },
    "wheeling": {
        "required_fields": [
            "seller_party_id", "buyer_party_id",
            "settlement_period_start", "settlement_period_end",
            "contract_reference", "settlement_type",
            "network_operator_id", "wheeling_type",
            "injection_point_id", "offtake_point_id",
            "wheeling_status", "loss_factor",
        ],
        "field_constraints": {
            "settlement_type": ["bilateral"],
        },
    },
    "sawem_brp": {
        "required_fields": [
            "seller_party_id", "balance_responsible_party_id",
            "settlement_type", "forecast_kWh",
            "settlement_period_start", "settlement_period_end",
        ],
        "field_constraints": {
            "settlement_type": [
                "sawem_day_ahead", "sawem_intra_day", "balancing", "ancillary",
            ],
        },
    },
    "municipal_recon": {
        "required_fields": [
            "buyer_party_id", "billing_period",
            "billed_kWh", "billing_status",
        ],
        "field_constraints": {},
    },
}


def validate(
    data: Union[dict, str, Path],
    level: str = "schema",
    capacity_kw: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    profile: Optional[str] = None,
) -> ValidationResult:
    """
    Validate data against ODS-E energy-timeseries schema.

    Args:
        data: Dictionary, JSON string, or path to JSON file
        level: Validation level - "schema" or "semantic"
        capacity_kw: Asset capacity in kW (required for semantic validation)
        latitude: Asset latitude (optional, for nighttime checks)
        longitude: Asset longitude (optional, for nighttime checks)
        profile: Optional conformance profile name (e.g. "bilateral", "wheeling")

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

    # Profile validation
    if profile is not None and not errors:
        errors.extend(_validate_profile(data, profile))

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


def validate_batch(
    records: List[dict],
    level: str = "schema",
    profile: Optional[str] = None,
    **kwargs,
) -> BatchValidationResult:
    """
    Validate a list of records and return aggregate validation results.

    Args:
        records: List of ODS-E records
        level: Validation level
        profile: Optional conformance profile
        **kwargs: Additional arguments passed to validate()

    Returns:
        BatchValidationResult
    """
    indexed_errors: List[Tuple[int, ValidationError]] = []
    error_counts = {}
    total = len(records)
    valid = 0

    for idx, record in enumerate(records):
        result = validate(record, level=level, profile=profile, **kwargs)
        if result.is_valid:
            valid += 1
            continue
        for err in result.errors:
            indexed_errors.append((idx, err))
            error_counts[err.code] = error_counts.get(err.code, 0) + 1

    invalid = total - valid
    if invalid == 0:
        summary = f"{valid}/{total} valid, 0 errors"
    else:
        breakdown = ", ".join(
            f"{count}x {code}" for code, count in sorted(error_counts.items())
        )
        summary = f"{valid}/{total} valid, {len(indexed_errors)} errors: {breakdown}"

    return BatchValidationResult(
        total=total,
        valid=valid,
        invalid=invalid,
        errors=indexed_errors,
        summary=summary,
    )


def _check_optional_type(
    data: dict, field: str, expected_type: str, errors: list, type_label: str,
) -> None:
    """Type check for an optional field. Skips if field is absent."""
    if field not in data:
        return
    value = data[field]
    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(ValidationError(
                path=f"$.{field}",
                message=f"Expected {type_label}, got {type(value).__name__}",
                code="TYPE_MISMATCH",
            ))
    elif expected_type == "number":
        if type(value) is bool or not isinstance(value, (int, float)):
            errors.append(ValidationError(
                path=f"$.{field}",
                message=f"Expected {type_label}, got {type(value).__name__}",
                code="TYPE_MISMATCH",
            ))
    elif expected_type == "boolean":
        if type(value) is not bool:
            errors.append(ValidationError(
                path=f"$.{field}",
                message=f"Expected {type_label}, got {type(value).__name__}",
                code="TYPE_MISMATCH",
            ))


def _check_optional_enum(
    data: dict, field: str, valid_values: list, errors: list,
) -> None:
    """Enum check for an optional field. Skips if field is absent."""
    if field not in data:
        return
    if data[field] not in valid_values:
        errors.append(ValidationError(
            path=f"$.{field}",
            message=f"Value '{data[field]}' not in enum {valid_values}",
            code="ENUM_MISMATCH",
        ))


def _check_optional_minimum(
    data: dict, field: str, minimum: float, errors: list,
) -> None:
    """Lower-bound check for an optional numeric field. Skips if absent or wrong type."""
    if field not in data:
        return
    value = data[field]
    if type(value) is bool or not isinstance(value, (int, float)):
        return
    if value < minimum:
        errors.append(ValidationError(
            path=f"$.{field}",
            message=f"{field} must be >= {minimum}",
            code="OUT_OF_BOUNDS",
        ))


def _check_optional_pattern(
    data: dict, field: str, pattern: str, errors: list,
) -> None:
    """Regex pattern check for an optional string field. Skips if absent or wrong type."""
    if field not in data:
        return
    value = data[field]
    if not isinstance(value, str):
        return
    if not re.match(pattern, value):
        errors.append(ValidationError(
            path=f"$.{field}",
            message=f"Value '{value}' does not match pattern '{pattern}'",
            code="PATTERN_MISMATCH",
        ))


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

    _check_optional_enum(data, "direction",
                         ["generation", "consumption", "net"], errors)

    _check_optional_enum(data, "end_use", [
        "cooling", "heating", "fans", "pumps", "water_systems",
        "interior_lighting", "exterior_lighting", "interior_equipment",
        "refrigeration", "cooking", "laundry", "ev_charging",
        "pv_generation", "battery_storage", "whole_building", "other",
    ], errors)

    _check_optional_enum(data, "fuel_type",
                         ["electricity", "natural_gas", "propane", "fuel_oil", "other"], errors)

    # Bounds validation — kWh >= 0 except for net direction
    direction = data.get("direction", "generation")
    if isinstance(data.get("kWh"), (int, float)) and data["kWh"] < 0 and direction != "net":
        errors.append(ValidationError(
            path="$.kWh",
            message="kWh must be >= 0 for generation and consumption",
            code="OUT_OF_BOUNDS",
        ))

    # PF bounds (0..1)
    if "PF" in data:
        pf = data["PF"]
        if isinstance(pf, (int, float)) and (pf < 0 or pf > 1):
            errors.append(ValidationError(
                path="$.PF",
                message="Power factor must be between 0 and 1",
                code="OUT_OF_BOUNDS",
            ))

    # --- Unchecked base fields ---
    _check_optional_type(data, "error_code", "string", errors, "string")
    _check_optional_type(data, "kVArh", "number", errors, "number")
    _check_optional_type(data, "kVA", "number", errors, "number")
    _check_optional_minimum(data, "kVA", 0, errors)

    # --- Party IDs ---
    _party_id_pattern = r"^[a-z0-9._-]+:[a-z0-9._-]+:[a-zA-Z0-9._-]+$"
    for pid_field in [
        "seller_party_id", "buyer_party_id", "network_operator_id",
        "wheeling_agent_id", "balance_responsible_party_id",
    ]:
        _check_optional_type(data, pid_field, "string", errors, "string")
        _check_optional_pattern(data, pid_field, _party_id_pattern, errors)

    # --- Settlement ---
    _check_optional_type(data, "settlement_period_start", "string", errors, "string")
    _check_optional_type(data, "settlement_period_end", "string", errors, "string")
    _check_optional_type(data, "loss_factor", "number", errors, "number")
    _check_optional_minimum(data, "loss_factor", 0, errors)
    _check_optional_type(data, "contract_reference", "string", errors, "string")
    _check_optional_enum(data, "settlement_type", [
        "bilateral", "sawem_day_ahead", "sawem_intra_day", "balancing", "ancillary",
    ], errors)

    # --- Tariff ---
    _check_optional_type(data, "tariff_schedule_id", "string", errors, "string")
    _check_optional_pattern(data, "tariff_schedule_id",
                            r"^[a-z0-9._-]+:[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+:v[0-9]+$", errors)
    _check_optional_enum(data, "tariff_period",
                         ["peak", "standard", "off_peak", "critical_peak"], errors)
    _check_optional_type(data, "tariff_currency", "string", errors, "string")
    _check_optional_pattern(data, "tariff_currency", r"^[A-Z]{3}$", errors)
    _check_optional_type(data, "tariff_version_effective_at", "string", errors, "string")
    _check_optional_type(data, "energy_charge_component", "number", errors, "number")
    _check_optional_minimum(data, "energy_charge_component", 0, errors)
    _check_optional_type(data, "network_charge_component", "number", errors, "number")
    _check_optional_minimum(data, "network_charge_component", 0, errors)

    # --- Granular charge components ---
    for charge_field in [
        "generation_charge_component", "transmission_charge_component",
        "distribution_charge_component", "ancillary_service_charge_component",
        "non_bypassable_charge_component", "environmental_levy_component",
    ]:
        _check_optional_type(data, charge_field, "number", errors, "number")
        _check_optional_minimum(data, charge_field, 0, errors)

    # --- Wheeling ---
    _check_optional_enum(data, "wheeling_type",
                         ["traditional", "virtual", "portfolio"], errors)
    _check_optional_enum(data, "wheeling_status",
                         ["provisional", "confirmed", "reconciled", "disputed"], errors)
    _check_optional_type(data, "injection_point_id", "string", errors, "string")
    _check_optional_type(data, "offtake_point_id", "string", errors, "string")
    _check_optional_type(data, "wheeling_path_id", "string", errors, "string")

    # --- Curtailment ---
    _check_optional_type(data, "curtailment_flag", "boolean", errors, "boolean")
    _check_optional_enum(data, "curtailment_type",
                         ["congestion", "frequency", "voltage", "instruction", "other"], errors)
    _check_optional_type(data, "curtailed_kWh", "number", errors, "number")
    _check_optional_minimum(data, "curtailed_kWh", 0, errors)
    _check_optional_type(data, "curtailment_instruction_id", "string", errors, "string")

    # --- BRP / Imbalance ---
    _check_optional_type(data, "forecast_kWh", "number", errors, "number")
    _check_optional_type(data, "imbalance_kWh", "number", errors, "number")

    # --- Municipal billing ---
    _check_optional_type(data, "billing_period", "string", errors, "string")
    _check_optional_type(data, "billed_kWh", "number", errors, "number")
    _check_optional_minimum(data, "billed_kWh", 0, errors)
    _check_optional_enum(data, "billing_status",
                         ["metered", "estimated", "adjusted", "disputed"], errors)
    _check_optional_type(data, "daa_reference", "string", errors, "string")

    # --- Certificates ---
    _check_optional_type(data, "renewable_attribute_id", "string", errors, "string")
    _check_optional_enum(data, "certificate_standard",
                         ["i_rec", "rego", "go", "rec", "tigr", "other"], errors)
    _check_optional_enum(data, "verification_status",
                         ["pending", "issued", "retired", "cancelled"], errors)
    _check_optional_type(data, "carbon_intensity_gCO2_per_kWh", "number", errors, "number")
    _check_optional_minimum(data, "carbon_intensity_gCO2_per_kWh", 0, errors)

    return errors


def _validate_profile(data: dict, profile_name: str) -> List[ValidationError]:
    """Validate data against a conformance profile's required fields and value constraints."""
    errors = []

    if profile_name not in PROFILES:
        errors.append(ValidationError(
            path="$",
            message=f"Unknown profile '{profile_name}'. Valid profiles: {list(PROFILES.keys())}",
            code="UNKNOWN_PROFILE",
        ))
        return errors

    profile = PROFILES[profile_name]

    for field in profile["required_fields"]:
        if field not in data:
            errors.append(ValidationError(
                path=f"$.{field}",
                message=f"Profile '{profile_name}' requires field '{field}'",
                code="PROFILE_FIELD_MISSING",
            ))

    for field, allowed_values in profile["field_constraints"].items():
        if field in data and data[field] not in allowed_values:
            errors.append(ValidationError(
                path=f"$.{field}",
                message=f"Profile '{profile_name}' requires '{field}' to be one of {allowed_values}, got '{data[field]}'",
                code="PROFILE_VALUE_MISMATCH",
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

    # Physical bounds check — skip for consumption (capacity doesn't bound consumption)
    direction = data.get("direction", "generation")
    if capacity_kw and isinstance(data.get("kWh"), (int, float)) and direction != "consumption":
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

"""Template validation: placeholder registry and schema enforcement.

This module provides:
1. Placeholder registry loading and validation
2. YAML module schema validation by module type
3. Fail-fast error reporting for production safety
"""
from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import yaml


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class PlaceholderInfo:
    """Information about a registered placeholder."""
    token: str
    category: str
    label: str
    hint: str
    profile_path: Optional[str] = None


@dataclass
class ValidationError:
    """A single validation error."""
    file_name: str
    module_id: Optional[str]
    module_title: Optional[str]
    error_type: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation run."""
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, error: ValidationError):
        self.errors.append(error)
        self.valid = False

    def raise_if_invalid(self):
        """Raise exception if validation failed."""
        if not self.valid:
            error_lines = ["Template validation failed:"]
            for err in self.errors:
                loc = f"{err.file_name}"
                if err.module_id:
                    loc += f" > {err.module_id}"
                if err.module_title:
                    loc += f" ({err.module_title})"
                error_lines.append(f"  [{err.error_type}] {loc}")
                error_lines.append(f"    {err.message}")
                if err.suggestion:
                    error_lines.append(f"    Suggestion: {err.suggestion}")
            raise TemplateValidationError("\n".join(error_lines))


class TemplateValidationError(Exception):
    """Raised when template validation fails."""
    pass


# ============================================================
# PLACEHOLDER REGISTRY
# ============================================================

class PlaceholderRegistry:
    """Registry of allowed placeholders and their metadata."""

    _instance: Optional["PlaceholderRegistry"] = None
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not PlaceholderRegistry._loaded:
            self._placeholders: dict[str, PlaceholderInfo] = {}
            self._categories: dict[str, str] = {}  # id -> label
            self._load_registry()
            PlaceholderRegistry._loaded = True

    def _load_registry(self):
        """Load placeholder registry from YAML file."""
        registry_path = Path(__file__).parent / "placeholder_registry.yaml"
        if not registry_path.exists():
            raise FileNotFoundError(f"Placeholder registry not found: {registry_path}")

        with open(registry_path, "r") as f:
            data = yaml.safe_load(f)

        # Load categories
        for cat in data.get("categories", []):
            self._categories[cat["id"]] = cat["label"]

        # Load placeholders
        for token, info in data.get("placeholders", {}).items():
            self._placeholders[token] = PlaceholderInfo(
                token=token,
                category=info.get("category", ""),
                label=info.get("label", token),
                hint=info.get("hint", ""),
                profile_path=info.get("profile_path"),
            )

    def is_registered(self, token: str) -> bool:
        """Check if a placeholder token is registered."""
        return token in self._placeholders

    def get(self, token: str) -> Optional[PlaceholderInfo]:
        """Get placeholder info by token."""
        return self._placeholders.get(token)

    def get_hint(self, token: str) -> str:
        """Get hint text for a placeholder."""
        info = self._placeholders.get(token)
        return info.hint if info else f"No hint available for {token}"

    def get_label(self, token: str) -> str:
        """Get human-friendly label for a placeholder."""
        info = self._placeholders.get(token)
        return info.label if info else token.replace("_", " ").title()

    def get_category(self, token: str) -> str:
        """Get category for a placeholder."""
        info = self._placeholders.get(token)
        if info and info.category:
            return self._categories.get(info.category, info.category)
        return "Other"

    def get_category_id(self, token: str) -> str:
        """Get category ID for a placeholder."""
        info = self._placeholders.get(token)
        return info.category if info else "other"

    def all_tokens(self) -> list[str]:
        """Get all registered placeholder tokens."""
        return list(self._placeholders.keys())

    def find_similar(self, token: str, max_results: int = 3) -> list[str]:
        """Find similar registered tokens (for suggestions)."""
        # Simple similarity: shared word parts
        token_parts = set(token.lower().split("_"))
        scored = []
        for registered in self._placeholders.keys():
            reg_parts = set(registered.lower().split("_"))
            overlap = len(token_parts & reg_parts)
            if overlap > 0:
                scored.append((registered, overlap))
        scored.sort(key=lambda x: -x[1])
        return [t for t, _ in scored[:max_results]]

    @property
    def categories(self) -> dict[str, str]:
        """Get all categories (id -> label)."""
        return self._categories.copy()


# ============================================================
# PLACEHOLDER VALIDATION
# ============================================================

# Regex to find placeholders: [LIKE_THIS]
PLACEHOLDER_PATTERN = re.compile(r'\[([A-Z][A-Z0-9_]*)\]')


def extract_placeholders(text: str) -> set[str]:
    """Extract all placeholder tokens from text."""
    if not text:
        return set()
    return set(PLACEHOLDER_PATTERN.findall(text))


def extract_placeholders_from_value(value, collected: set[str]):
    """Recursively extract placeholders from any value type."""
    if isinstance(value, str):
        collected.update(extract_placeholders(value))
    elif isinstance(value, list):
        for item in value:
            extract_placeholders_from_value(item, collected)
    elif isinstance(value, dict):
        for v in value.values():
            extract_placeholders_from_value(v, collected)


def validate_module_placeholders(
    module_id: str,
    module_data: dict,
    file_name: str,
    registry: PlaceholderRegistry,
    result: ValidationResult
):
    """Validate all placeholders in a module are registered."""
    placeholders: set[str] = set()
    extract_placeholders_from_value(module_data, placeholders)

    module_title = module_data.get("title", "")

    for token in placeholders:
        if not registry.is_registered(token):
            similar = registry.find_similar(token)
            suggestion = f"Did you mean: {', '.join(similar)}?" if similar else None
            result.add_error(ValidationError(
                file_name=file_name,
                module_id=module_id,
                module_title=module_title,
                error_type="UNREGISTERED_PLACEHOLDER",
                message=f"Placeholder [{token}] is not registered in placeholder_registry.yaml",
                suggestion=suggestion,
            ))


def validate_all_templates(data_dir: Optional[Path] = None) -> ValidationResult:
    """Validate all YAML template files for placeholder registration."""
    if data_dir is None:
        data_dir = Path(__file__).parent / "data"

    registry = PlaceholderRegistry()
    result = ValidationResult(valid=True)

    yaml_files = list(data_dir.glob("*.yaml"))
    if not yaml_files:
        result.warnings.append(f"No YAML files found in {data_dir}")
        return result

    for yaml_path in yaml_files:
        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                continue

            file_name = yaml_path.name
            for module_id, module_data in data.items():
                if isinstance(module_data, dict):
                    validate_module_placeholders(
                        module_id, module_data, file_name, registry, result
                    )
        except yaml.YAMLError as e:
            result.add_error(ValidationError(
                file_name=yaml_path.name,
                module_id=None,
                module_title=None,
                error_type="YAML_PARSE_ERROR",
                message=str(e),
            ))

    return result


# ============================================================
# SCHEMA VALIDATION BY MODULE TYPE
# ============================================================

# Required fields per module type
MODULE_TYPE_SCHEMAS: dict[str, dict] = {
    "playbook": {
        "required": ["title", "phases"],
        "phases_required": True,  # Must have phase structure
        "description": "Emergency playbooks must have title and phases",
    },
    "checklist": {
        "required": ["title"],
        "one_of": ["items", "content", "tasks"],  # Must have at least one
        "description": "Checklists must have title and items/content/tasks",
    },
    "maintenance": {
        "required": ["title"],
        "recommended": ["warning_signs", "when_to_call_pro"],
        "description": "Maintenance modules should have warning signs and pro thresholds",
    },
    "seasonal": {
        "required": ["title"],
        "one_of": ["tasks", "content", "items"],
        "description": "Seasonal modules must have tasks or content",
    },
    "systems": {
        "required": ["title"],
        "recommended": ["warning_signs", "best_practices"],
        "description": "System modules should include warning signs",
    },
    "inventory": {
        "required": ["title"],
        "one_of": ["systems", "items", "base_supplies"],
        "description": "Inventory modules must have items or systems",
    },
    "quick_start": {
        "required": ["title"],
        "one_of": ["cards", "actions", "content"],
        "description": "Quick start modules must have cards or actions",
    },
    "region": {
        "required": ["title"],
        "description": "Region modules must have a title",
    },
    "household": {
        "required": ["title", "trigger"],
        "description": "Household modules must have a trigger condition",
    },
    "home_type": {
        "required": ["title"],
        "description": "Home type modules must have a title",
    },
}


def infer_module_type(module_id: str, module_data: dict) -> str:
    """Infer module type from explicit field, id, or category.

    Priority:
    1. Explicit module_type field (if present)
    2. Module ID prefix (playbook_, seasonal_, etc.)
    3. Category field
    4. Default to maintenance
    """
    # Check explicit module_type first (highest priority)
    explicit_type = module_data.get("module_type", "")
    if explicit_type:
        # Types like "guide", "reference" have no schema - return as-is
        return explicit_type

    # Check explicit category
    category = module_data.get("category", "")
    if category in MODULE_TYPE_SCHEMAS:
        return category

    # Infer from module_id prefix
    id_lower = module_id.lower()
    if id_lower.startswith("playbook_"):
        return "playbook"
    if id_lower.startswith("seasonal_"):
        return "seasonal"
    if id_lower.startswith("cleaning_"):
        return "checklist"
    if "inventory" in id_lower or "checklist" in id_lower:
        return "inventory"
    if "quick_start" in id_lower or id_lower.startswith("qs_"):
        return "quick_start"

    # Default based on category field
    if category == "emergency":
        return "playbook"
    if category in ("cleaning", "seasonal"):
        return category
    if category == "systems":
        return "systems"

    return "maintenance"  # Default


def validate_module_schema(
    module_id: str,
    module_data: dict,
    file_name: str,
    result: ValidationResult
):
    """Validate module against its type-specific schema."""
    module_type = infer_module_type(module_id, module_data)
    schema = MODULE_TYPE_SCHEMAS.get(module_type)

    if not schema:
        return  # No schema defined for this type

    module_title = module_data.get("title", "")

    # Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in module_data or not module_data[field]:
            result.add_error(ValidationError(
                file_name=file_name,
                module_id=module_id,
                module_title=module_title,
                error_type="MISSING_REQUIRED_FIELD",
                message=f"Module type '{module_type}' requires field '{field}'",
                suggestion=schema.get("description"),
            ))

    # Check one_of fields (at least one required)
    one_of = schema.get("one_of", [])
    if one_of:
        has_one = any(
            field in module_data and module_data[field]
            for field in one_of
        )
        if not has_one:
            result.add_error(ValidationError(
                file_name=file_name,
                module_id=module_id,
                module_title=module_title,
                error_type="MISSING_CONTENT_FIELD",
                message=f"Module type '{module_type}' requires at least one of: {', '.join(one_of)}",
                suggestion=schema.get("description"),
            ))

    # Check phases for playbooks
    if schema.get("phases_required") and module_type == "playbook":
        phases = module_data.get("phases", {})
        if not phases or not isinstance(phases, dict):
            result.add_error(ValidationError(
                file_name=file_name,
                module_id=module_id,
                module_title=module_title,
                error_type="INVALID_PHASES",
                message="Playbook must have a 'phases' dict with phase definitions",
                suggestion="Add phases like: phase_1_immediate, phase_2_stabilization, phase_3_recovery",
            ))


def validate_all_schemas(data_dir: Optional[Path] = None) -> ValidationResult:
    """Validate all YAML modules against their type schemas."""
    if data_dir is None:
        data_dir = Path(__file__).parent / "data"

    result = ValidationResult(valid=True)

    yaml_files = list(data_dir.glob("*.yaml"))

    for yaml_path in yaml_files:
        # Skip inventory_templates and quick_start - different structure
        if yaml_path.name in ("inventory_templates.yaml",):
            continue

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                continue

            file_name = yaml_path.name
            for module_id, module_data in data.items():
                if isinstance(module_data, dict):
                    validate_module_schema(module_id, module_data, file_name, result)

        except yaml.YAMLError as e:
            result.add_error(ValidationError(
                file_name=yaml_path.name,
                module_id=None,
                module_title=None,
                error_type="YAML_PARSE_ERROR",
                message=str(e),
            ))

    return result


# ============================================================
# COMBINED VALIDATION
# ============================================================

def validate_templates(fail_fast: bool = True) -> ValidationResult:
    """Run all template validations.

    Args:
        fail_fast: If True, raise exception on first validation failure.

    Returns:
        ValidationResult with all errors/warnings.
    """
    # Placeholder validation
    placeholder_result = validate_all_templates()

    # Schema validation
    schema_result = validate_all_schemas()

    # Combine results
    combined = ValidationResult(valid=placeholder_result.valid and schema_result.valid)
    combined.errors = placeholder_result.errors + schema_result.errors
    combined.warnings = placeholder_result.warnings + schema_result.warnings

    if fail_fast:
        combined.raise_if_invalid()

    return combined


def validate_placeholders_only(fail_fast: bool = True) -> ValidationResult:
    """Validate only placeholders (fail-fast critical).

    Use this in production loaders - placeholder errors cause render failures.
    Schema errors don't prevent rendering and are treated as warnings.

    Args:
        fail_fast: If True, raise exception on placeholder errors.

    Returns:
        ValidationResult.
    """
    # Placeholder validation - these are critical, fail-fast
    placeholder_result = validate_all_templates()

    # Schema validation - run but don't fail, just warn
    schema_result = validate_all_schemas()

    # For placeholders-only, only fail on placeholder errors
    result = ValidationResult(valid=placeholder_result.valid)
    result.errors = placeholder_result.errors  # Only placeholder errors
    result.warnings = (
        placeholder_result.warnings +
        schema_result.warnings +
        [f"[SCHEMA] {e.file_name} > {e.module_id}: {e.message}" for e in schema_result.errors]
    )

    if fail_fast:
        result.raise_if_invalid()

    return result


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import sys

    print("Validating templates...")
    try:
        result = validate_templates(fail_fast=False)
        if result.valid:
            print("All templates valid.")
            print(f"  Warnings: {len(result.warnings)}")
            for w in result.warnings:
                print(f"    - {w}")
        else:
            print(f"Validation FAILED with {len(result.errors)} errors:")
            for err in result.errors:
                print(f"  [{err.error_type}] {err.file_name} > {err.module_id}")
                print(f"    {err.message}")
                if err.suggestion:
                    print(f"    Suggestion: {err.suggestion}")
            sys.exit(1)
    except Exception as e:
        print(f"Validation error: {e}")
        sys.exit(1)

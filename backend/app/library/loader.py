"""YAML-based content library loader.

Validates all templates on first load (fail-fast) to catch:
- Unregistered placeholders
- Missing required fields by module type
"""

import os
import logging
import yaml

from app.library.validation import validate_placeholders_only, TemplateValidationError

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_cache: dict[str, dict] = {}
_validated: bool = False


def _validate_once():
    """Run validation once on first load. Fail-fast on placeholder errors only."""
    global _validated
    if _validated:
        return

    try:
        result = validate_placeholders_only(fail_fast=True)
        _validated = True
        if result.warnings:
            for w in result.warnings:
                logger.warning(f"Template warning: {w}")
        logger.info("Template validation passed (placeholders OK)")
    except TemplateValidationError as e:
        logger.error(f"Template validation failed:\n{e}")
        raise


def _load_yaml(filename: str) -> dict:
    # Validate templates on first load
    _validate_once()

    if filename in _cache:
        return _cache[filename]
    path = os.path.join(_DATA_DIR, filename)
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    _cache[filename] = data
    return data


def get_universal_modules() -> dict:
    return _load_yaml("universal.yaml")


def get_region_modules_data() -> dict:
    return _load_yaml("region.yaml")


def get_home_type_modules_data() -> dict:
    return _load_yaml("home_type.yaml")


def get_systems_modules_data() -> dict:
    return _load_yaml("systems.yaml")


def get_household_modules_data() -> dict:
    return _load_yaml("household.yaml")


def get_landscaping_modules_data() -> dict:
    return _load_yaml("landscaping.yaml")


def get_playbook_modules() -> dict:
    return _load_yaml("playbooks.yaml")


def get_quick_start_modules() -> dict:
    return _load_yaml("quick_start.yaml")


def get_inventory_modules() -> dict:
    return _load_yaml("inventory_templates.yaml")


def get_all_modules() -> dict:
    """Return every module across all YAML files -- useful for landing page stats."""
    combined = {}
    for fn in os.listdir(_DATA_DIR):
        if fn.endswith(".yaml"):
            combined.update(_load_yaml(fn))
    return combined


def clear_cache():
    """Clear the module cache and validation state. For testing only."""
    global _cache, _validated
    _cache = {}
    _validated = False


def skip_validation():
    """Mark validation as done without running. For testing only."""
    global _validated
    _validated = True

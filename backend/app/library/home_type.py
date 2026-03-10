"""Home-type-specific modules — loaded from YAML."""

from app.library.loader import get_home_type_modules_data

MODULES = get_home_type_modules_data()


def get_home_type_modules(home_type: str) -> dict:
    if not home_type:
        return {}
    return {k: v for k, v in MODULES.items() if v.get("home_type") == home_type}

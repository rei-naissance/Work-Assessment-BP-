"""Feature/system-specific modules — loaded from YAML."""

from app.library.loader import get_systems_modules_data

MODULES = get_systems_modules_data()


def get_feature_modules(features: dict) -> dict:
    result = {}
    for key, mod in MODULES.items():
        feat = mod.get("feature", "")
        if feat.startswith("hvac_"):
            if features.get("hvac_type") == feat.replace("hvac_", ""):
                result[key] = mod
        elif features.get(feat, False):
            result[key] = mod
    return result

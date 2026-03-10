from app.models.profile import Profile, HomeIdentity, Features, Household, Coverage
from app.rules.engine import select_modules, select_modules_flat


def _flat(profile, tier="premium"):
    """Helper: flatten section-grouped result for backward-compat assertions."""
    return select_modules_flat(profile, tier)


# -- Basic module inclusion (via flat helper) --

def test_universal_modules_included():
    profile = Profile(user_id="test")
    modules = _flat(profile)
    assert "emergency_contacts" in modules
    assert "fire_safety" in modules
    assert "seasonal_spring" in modules
    assert "cleaning_basics" in modules
    assert "general_maintenance" in modules


def test_coverage_filters():
    profile = Profile(user_id="test", coverage=Coverage(
        include_emergency=False,
        include_seasonal=False,
        include_cleaning=False,
        include_maintenance=False,
        include_landscaping=False,
    ))
    modules = _flat(profile)
    assert "emergency_contacts" not in modules
    assert "seasonal_spring" not in modules
    assert "cleaning_basics" not in modules
    assert "general_maintenance" not in modules
    assert "landscaping_general" not in modules


def test_region_modules():
    profile = Profile(user_id="test", home_identity=HomeIdentity(zip_code="33101"))
    modules = _flat(profile)
    assert "southeast_hurricane" in modules


def test_home_type_modules():
    profile = Profile(user_id="test", home_identity=HomeIdentity(home_type="condo"))
    modules = _flat(profile)
    assert "condo_association" in modules


def test_feature_modules():
    profile = Profile(user_id="test", features=Features(has_pool=True, has_garage=True))
    modules = _flat(profile)
    assert "pool_care" in modules
    assert "garage_maintenance" in modules


def test_hvac_feature():
    profile = Profile(user_id="test", features=Features(hvac_type="central_air"))
    modules = _flat(profile)
    assert "hvac_central_air" in modules
    assert "hvac_heat_pump" not in modules


def test_hvac_radiant():
    profile = Profile(user_id="test", features=Features(hvac_type="radiant"))
    modules = _flat(profile)
    assert "hvac_radiant" in modules


def test_household_pets():
    profile = Profile(user_id="test", household=Household(has_pets=True, pet_types="dog"))
    modules = _flat(profile)
    assert "pet_safety" in modules


def test_household_children():
    profile = Profile(user_id="test", household=Household(num_children=2))
    modules = _flat(profile)
    assert "child_safety" in modules


def test_household_elderly():
    profile = Profile(user_id="test", household=Household(has_elderly=True))
    modules = _flat(profile)
    assert "elderly_accessibility" in modules


def test_household_allergies():
    profile = Profile(user_id="test", household=Household(has_allergies=True))
    modules = _flat(profile)
    assert "allergy_air_quality" in modules


def test_landscaping_included_by_default():
    profile = Profile(user_id="test")
    modules = _flat(profile)
    assert "landscaping_general" in modules
    assert "landscaping_drainage" in modules


def test_landscaping_excluded():
    profile = Profile(user_id="test", coverage=Coverage(include_landscaping=False))
    modules = _flat(profile)
    assert "landscaping_general" not in modules


def test_standard_tier_excludes_systems():
    profile = Profile(user_id="test", features=Features(has_pool=True))
    modules = _flat(profile, tier="standard")
    assert "emergency_contacts" in modules
    assert "pool_care" not in modules


def test_standard_tier_excludes_household():
    profile = Profile(user_id="test", household=Household(has_pets=True))
    modules = _flat(profile, tier="standard")
    assert "pet_safety" not in modules


def test_standard_tier_excludes_landscaping():
    profile = Profile(user_id="test")
    modules = _flat(profile, tier="standard")
    assert "landscaping_general" not in modules


def test_standard_tier_includes_region():
    profile = Profile(user_id="test", home_identity=HomeIdentity(zip_code="33101"))
    modules = _flat(profile, tier="standard")
    assert "southeast_hurricane" in modules


def test_premium_tier_includes_everything():
    profile = Profile(
        user_id="test",
        home_identity=HomeIdentity(zip_code="33101", home_type="single_family"),
        features=Features(has_pool=True),
        household=Household(has_pets=True, num_children=1, has_elderly=True, has_allergies=True),
    )
    modules = _flat(profile, tier="premium")
    assert "emergency_contacts" in modules
    assert "southeast_hurricane" in modules
    assert "single_family_exterior" in modules
    assert "pool_care" in modules
    assert "pet_safety" in modules
    assert "child_safety" in modules
    assert "elderly_accessibility" in modules
    assert "allergy_air_quality" in modules
    assert "landscaping_general" in modules


# -- New section-grouped tests --

def test_section_grouped_return():
    profile = Profile(user_id="test")
    sections = select_modules(profile)
    assert "section_0" in sections
    assert "section_1" in sections
    assert "section_3" in sections
    assert "section_5" in sections
    assert "section_6" in sections


def test_playbooks_always_included():
    profile = Profile(user_id="test")
    sections = select_modules(profile)
    assert "playbook_fire" in sections["section_3"]
    assert "playbook_water_leak" in sections["section_3"]
    assert "playbook_power_outage" in sections["section_3"]
    assert "playbook_hvac_failure" in sections["section_3"]
    assert "playbook_storm" in sections["section_3"]
    assert "playbook_security" in sections["section_3"]


def test_playbooks_included_standard_tier():
    profile = Profile(user_id="test")
    sections = select_modules(profile, tier="standard")
    assert "playbook_fire" in sections["section_3"]


def test_section_assignment_emergency():
    profile = Profile(user_id="test")
    sections = select_modules(profile)
    assert "emergency_contacts" in sections["section_3"]
    assert "fire_safety" in sections["section_3"]


def test_section_assignment_maintenance():
    profile = Profile(user_id="test")
    sections = select_modules(profile)
    assert "seasonal_spring" in sections["section_5"]
    assert "cleaning_basics" in sections["section_5"]
    assert "general_maintenance" in sections["section_5"]


def test_storm_playbook_gets_region_tag():
    profile = Profile(user_id="test", home_identity=HomeIdentity(zip_code="33101"))
    sections = select_modules(profile)
    storm = sections["section_3"]["playbook_storm"]
    assert storm.get("region_tag") == "southeast"


def test_storm_playbook_no_region_tag_without_zip():
    profile = Profile(user_id="test")
    sections = select_modules(profile)
    storm = sections["section_3"]["playbook_storm"]
    assert "region_tag" not in storm


def test_quick_start_in_section_1():
    profile = Profile(user_id="test")
    sections = select_modules(profile)
    assert "emergency_quick_start" in sections["section_1"]


def test_inventory_in_section_6():
    profile = Profile(user_id="test")
    sections = select_modules(profile)
    assert "equipment_checklist" in sections["section_6"]
    assert "emergency_kit" in sections["section_6"]

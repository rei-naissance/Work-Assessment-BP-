"""Rules engine: selects content modules based on a user profile and tier.

Returns section-grouped dict for the 8-section binder structure.
"""

from app.models.profile import Profile
from app.library.loader import (
    get_universal_modules, get_household_modules_data, get_landscaping_modules_data,
    get_playbook_modules, get_quick_start_modules, get_inventory_modules,
)
from app.library.region import get_region_modules, get_region
from app.library.home_type import get_home_type_modules
from app.library.systems import get_feature_modules


def select_modules(profile: Profile, tier: str = "premium") -> dict:
    """Return a section-grouped dict of module_key -> module data.

    Sections:
      section_0: cover (no modules)
      section_1: emergency quick-start cards
      section_2: home profile (no modules, rendered from profile)
      section_3: emergency playbooks + emergency modules
      section_4: guest/sitter mode (no modules, rendered from profile)
      section_5: maintenance modules (seasonal, cleaning, systems, etc.)
      section_6: inventory templates
      section_7: contacts (no modules, rendered from profile)
      section_8: appendix (no modules, rendered from profile + all modules)
    """
    sections: dict = {
        "section_0": {},
        "section_1": {},
        "section_2": {},
        "section_3": {},
        "section_4": {},
        "section_5": {},
        "section_6": {},
        "section_7": {},
        "section_8": {},
    }
    coverage = profile.coverage

    # -- Section 1: Quick Start (both tiers) --
    quick_start = get_quick_start_modules()
    sections["section_1"].update(quick_start)

    # -- Section 3: Playbooks (both tiers, always included) --
    playbooks = get_playbook_modules()
    for key, mod in playbooks.items():
        if key == "playbook_storm":
            region = get_region(profile.home_identity.zip_code) if profile.home_identity.zip_code else ""
            mod = dict(mod)
            if region:
                mod["region_tag"] = region
        sections["section_3"][key] = mod

    # -- Universal modules --
    universal = get_universal_modules()
    for key, mod in universal.items():
        cat = mod.get("category", "")
        if cat == "emergency" and not coverage.include_emergency:
            continue
        if cat == "seasonal" and not coverage.include_seasonal:
            continue
        if cat == "cleaning" and not coverage.include_cleaning:
            continue
        if cat == "maintenance" and not coverage.include_maintenance:
            continue
        section = mod.get("section", 5)
        sections[f"section_{section}"][key] = mod

    # -- Region modules (both tiers) --
    zip_code = profile.home_identity.zip_code
    if zip_code:
        for key, mod in get_region_modules(zip_code).items():
            section = mod.get("section", 5)
            sections[f"section_{section}"][key] = mod

    # -- Home type modules (both tiers) --
    home_type = profile.home_identity.home_type
    if home_type:
        for key, mod in get_home_type_modules(home_type).items():
            section = mod.get("section", 5)
            sections[f"section_{section}"][key] = mod

    # -- Section 6: Inventory templates (both tiers) --
    inventory = get_inventory_modules()
    sections["section_6"].update(inventory)

    # -- Premium-only sections below --
    if tier != "premium":
        return sections

    # Feature/system modules
    if coverage.include_systems:
        features = profile.features.model_dump()
        for key, mod in get_feature_modules(features).items():
            section = mod.get("section", 5)
            sections[f"section_{section}"][key] = mod

    # Household-triggered modules
    household = profile.household
    household_data = get_household_modules_data()
    for key, mod in household_data.items():
        trigger = mod.get("trigger", "")
        include = False
        if trigger == "has_pets" and household.has_pets:
            include = True
        elif trigger == "has_children" and household.num_children > 0:
            include = True
        elif trigger == "has_elderly" and household.has_elderly:
            include = True
        elif trigger == "has_allergies" and household.has_allergies:
            include = True
        if include:
            section = mod.get("section", 5)
            sections[f"section_{section}"][key] = mod

    # Landscaping modules
    if coverage.include_landscaping:
        landscaping = get_landscaping_modules_data()
        for key, mod in landscaping.items():
            section = mod.get("section", 5)
            sections[f"section_{section}"][key] = mod

    return sections


def select_modules_flat(profile: Profile, tier: str = "premium") -> dict:
    """Backward-compatible flat dict of all modules (for tests during transition)."""
    sections = select_modules(profile, tier)
    flat = {}
    for section_modules in sections.values():
        flat.update(section_modules)
    return flat


def get_rules_tree() -> dict:
    """Return a comprehensive tree describing the full content pipeline."""
    return {
        # ── SECTIONS: what goes into each binder section ──────────────
        "sections": {
            "section_0": {
                "title": "Cover Page",
                "rendering": "profile-rendered",
                "source": "PDF generator (no YAML modules)",
                "content": [
                    "Home nickname or address",
                    "Property details (type, year built, sq ft)",
                    "Household summary (adults, children, pets)",
                    "Generated date",
                ],
                "variables_used": {
                    "home_identity.home_nickname": "Step 4: Critical Locations",
                    "home_identity.address_line1": "Step 1: Home Identity",
                    "home_identity.home_type": "Step 1: Home Identity",
                    "home_identity.year_built": "Step 1: Home Identity",
                    "home_identity.square_feet": "Step 1: Home Identity",
                    "household.num_adults": "Step 3: Household",
                    "household.num_children": "Step 3: Household",
                    "household.has_pets": "Step 3: Household",
                    "household.pet_types": "Step 3: Household",
                },
            },
            "section_1": {
                "title": "Emergency Quick-Start Cards",
                "rendering": "always included (both tiers)",
                "source": "quick_start.yaml",
                "content": [
                    "Gas Leak Emergency card",
                    "Water Leak / Flood Emergency card",
                    "Fire Emergency card",
                    "Power Outage Response card",
                ],
                "description": "Laminated-style reference cards for immediate crisis response. Each card has warning signs, step-by-step actions, shutoff info, and emergency contacts.",
                "key_placeholders": {
                    "[GAS_SHUTOFF_LOCATION]": "critical_locations.gas_shutoff.location → Step 4",
                    "[WATER_SHUTOFF_LOCATION]": "critical_locations.water_shutoff.location → Step 4",
                    "[ELECTRICAL_PANEL_LOCATION]": "critical_locations.electrical_panel.location → Step 4",
                    "[FIRE_MEETING_POINT]": "guest_sitter_mode.fire_meeting_point → Step 8",
                    "[HOME_ADDRESS]": "home_identity.address_line1 → Step 1",
                    "[GAS_COMPANY_PHONE]": "contacts_vendors.gas.phone → Step 6",
                    "[POWER_COMPANY_PHONE]": "contacts_vendors.power.phone → Step 6",
                    "[PLUMBER_NAME]": "contacts_vendors.plumber.name → Step 6",
                    "[PLUMBER_PHONE]": "contacts_vendors.plumber.phone → Step 6",
                    "[HVAC_NAME]": "contacts_vendors.hvac_tech.name → Step 6",
                    "[HVAC_PHONE]": "contacts_vendors.hvac_tech.phone → Step 6",
                },
            },
            "section_2": {
                "title": "Home Profile",
                "rendering": "profile-rendered",
                "source": "PDF generator (no YAML modules)",
                "content": [
                    "Full address and property details",
                    "Home type and ownership status",
                    "All features/systems inventory",
                    "Household composition",
                    "Coverage preferences",
                    "Critical locations map",
                ],
                "variables_used": {
                    "home_identity.*": "Step 1: Home Identity",
                    "features.*": "Step 2: Features (93 toggles + HVAC type)",
                    "household.*": "Step 3: Household",
                    "critical_locations.*": "Step 4: Critical Locations",
                    "coverage.*": "Step 5: Coverage",
                    "preferences.*": "Step 9: Preferences",
                },
            },
            "section_3": {
                "title": "Emergency Playbooks",
                "rendering": "always included (both tiers)",
                "source": "playbooks.yaml + universal.yaml (emergency category)",
                "modules": {
                    "always_included": {
                        "playbook_fire": "Fire Emergency Playbook (3 phases: immediate → stabilization → recovery)",
                        "playbook_water_leak": "Water Leak / Flood Emergency (3 phases)",
                        "playbook_power_outage": "Power Outage (3 phases)",
                        "playbook_hvac_failure": "HVAC Failure (3 phases)",
                        "playbook_storm": "Severe Storm Preparedness (3 phases) — gets region_tag from ZIP",
                        "playbook_security": "Security Incident (3 phases)",
                    },
                    "if_include_emergency": {
                        "emergency_contacts": "Emergency Contacts & Critical Shutoffs (from universal.yaml)",
                        "fire_safety": "Fire Safety & Prevention (from universal.yaml)",
                    },
                },
                "key_placeholders": {
                    "[FIRE_MEETING_POINT]": "guest_sitter_mode.fire_meeting_point → Step 8",
                    "[HOME_ADDRESS]": "home_identity.address_line1 → Step 1",
                    "[WATER_SHUTOFF_LOCATION]": "critical_locations.water_shutoff.location → Step 4",
                    "[GAS_SHUTOFF_LOCATION]": "critical_locations.gas_shutoff.location → Step 4",
                    "[ELECTRICAL_PANEL_LOCATION]": "critical_locations.electrical_panel.location → Step 4",
                    "[HVAC_UNIT_LOCATION]": "critical_locations.hvac_unit.location → Step 4",
                    "[PRIMARY_CONTACT_NAME]": "contacts_vendors.emergency_contacts[0].name → Step 7",
                    "[PRIMARY_CONTACT_PHONE]": "contacts_vendors.emergency_contacts[0].phone → Step 7",
                    "[INSURANCE_PROVIDER]": "contacts_vendors.insurance.provider → Step 6",
                    "[INSURANCE_CLAIM_PHONE]": "contacts_vendors.insurance.claim_phone → Step 6",
                    "[RESTORATION_COMPANY]": "fill-in placeholder (not captured in onboarding)",
                    "[SAFE_ROOM_LOCATION]": "fill-in placeholder (not captured in onboarding)",
                },
                "feedback_loop": "playbook_storm gets a region_tag based on ZIP → tailors storm advice to hurricanes (SE), tornadoes (MW), wildfire (W), etc.",
            },
            "section_4": {
                "title": "Guest / Sitter Mode",
                "rendering": "profile-rendered",
                "source": "PDF generator (no YAML modules)",
                "content": [
                    "General house instructions",
                    "Alarm / security instructions",
                    "Escalation contacts list",
                    "Pet sitter info (names, feeding, meds, vet)",
                    "WiFi password, garage code",
                    "Fire meeting point, safe room",
                ],
                "variables_used": {
                    "guest_sitter_mode.instructions": "Step 8: Guest/Sitter Mode",
                    "guest_sitter_mode.alarm_instructions": "Step 8: Guest/Sitter Mode",
                    "guest_sitter_mode.escalation_contacts": "Step 8: Guest/Sitter Mode",
                    "guest_sitter_mode.pet_sitter_info.*": "Step 8: Guest/Sitter Mode",
                    "guest_sitter_mode.fire_meeting_point": "Step 8: Guest/Sitter Mode",
                    "guest_sitter_mode.wifi_password": "Step 8: Guest/Sitter Mode",
                    "guest_sitter_mode.garage_code": "Step 8: Guest/Sitter Mode",
                    "guest_sitter_mode.safe_room_location": "Step 8: Guest/Sitter Mode",
                },
                "skip_toggles": "Each sub-section has a skip toggle (skip_instructions, skip_alarm, skip_escalation, skip_pet_sitter) — if skipped, that sub-section is omitted from the binder.",
            },
            "section_5": {
                "title": "Maintenance Modules",
                "rendering": "rules-driven (largest section)",
                "description": "This is the main rules-driven section. Modules are selected from 6 YAML sources based on profile data.",
                "module_sources": {
                    "universal.yaml (both tiers)": {
                        "description": "Base modules filtered by coverage toggles",
                        "modules": {
                            "seasonal_spring": {"title": "Spring Maintenance Checklist", "filter": "include_seasonal"},
                            "seasonal_summer": {"title": "Summer Maintenance Checklist", "filter": "include_seasonal"},
                            "seasonal_fall": {"title": "Fall Maintenance Checklist", "filter": "include_seasonal"},
                            "seasonal_winter": {"title": "Winter Maintenance Checklist", "filter": "include_seasonal"},
                            "cleaning_basics": {"title": "Cleaning Schedule & Guidelines", "filter": "include_cleaning"},
                            "general_maintenance": {"title": "General Home Maintenance", "filter": "include_maintenance"},
                            "home_inventory": {"title": "Home Inventory & Documentation", "filter": "include_maintenance"},
                        },
                    },
                    "region.yaml (both tiers)": {
                        "description": "Modules selected by ZIP → region lookup (3-digit prefix mapping)",
                        "selection_rule": "home_identity.zip_code → 3-digit prefix → region → all modules for that region",
                        "captured_at": "Step 1: Home Identity (ZIP code)",
                        "regions": {
                            "northeast": ["northeast_winter", "northeast_pests", "northeast_ice_dam_roof", "northeast_energy_efficiency", "northeast_coastal_flooding"],
                            "southeast": ["southeast_hurricane", "southeast_humidity", "southeast_pests", "southeast_mold_prevention", "southeast_energy_cooling"],
                            "midwest": ["midwest_tornado", "midwest_foundation", "midwest_winter_freeze", "midwest_basement_flooding", "midwest_energy_insulation"],
                            "southwest": ["southwest_heat", "southwest_monsoon", "southwest_dust_storms", "southwest_water_conservation", "southwest_uv_roof_protection"],
                            "west": ["west_wildfire", "west_earthquake", "west_radon", "west_mudslide_erosion", "west_energy_solar_optimization"],
                        },
                    },
                    "home_type.yaml (both tiers)": {
                        "description": "One module selected based on home type",
                        "selection_rule": "home_identity.home_type → matching module",
                        "captured_at": "Step 1: Home Identity (Home Type dropdown)",
                        "modules": {
                            "single_family_exterior": {"title": "Single Family Home Exterior Maintenance", "when": "home_type == single_family"},
                            "condo_association": {"title": "Condo & HOA Living Guide", "when": "home_type == condo"},
                            "townhouse_shared": {"title": "Townhouse Shared-Wall Considerations", "when": "home_type == townhouse"},
                            "apartment_renter": {"title": "Apartment & Renter Essentials", "when": "home_type == apartment"},
                            "mobile_home": {"title": "Mobile & Manufactured Home Care", "when": "home_type == mobile"},
                        },
                    },
                    "systems.yaml (premium only)": {
                        "description": "Modules selected by feature toggles — only if include_systems is ON",
                        "gate": "coverage.include_systems must be true",
                        "captured_at": "Step 2: Features (checkbox grid) + Step 5: Coverage (include_systems toggle)",
                        "modules": {
                            "pool_care": {"title": "Pool Maintenance Guide", "feature": "has_pool"},
                            "hot_tub_spa": {"title": "Hot Tub / Spa Care", "feature": "has_hot_tub"},
                            "garage_maintenance": {"title": "Garage Door & Workspace", "feature": "has_garage"},
                            "basement_care": {"title": "Basement Care & Waterproofing", "feature": "has_basement"},
                            "attic_care": {"title": "Attic Inspection & Insulation", "feature": "has_attic"},
                            "fireplace_care": {"title": "Fireplace & Chimney Maintenance", "feature": "has_fireplace"},
                            "septic_system": {"title": "Septic System Care", "feature": "has_septic"},
                            "well_water": {"title": "Well Water System Maintenance", "feature": "has_well_water"},
                            "solar_panels": {"title": "Solar Panel System Care", "feature": "has_solar"},
                            "sprinkler_system": {"title": "Irrigation & Sprinkler System", "feature": "has_sprinklers"},
                            "security_system": {"title": "Security System Management", "feature": "has_security_system"},
                            "water_heater": {"title": "Water Heater Maintenance", "feature": "has_water_heater"},
                            "roof_maintenance": {"title": "Roof Care & Inspection", "feature": "has_roof"},
                            "plumbing_system": {"title": "Plumbing System Care", "feature": "has_plumbing"},
                            "electrical_panel": {"title": "Electrical Panel & Safety", "feature": "has_electrical"},
                            "washer_dryer": {"title": "Washer & Dryer Care", "feature": "has_washer_dryer"},
                            "dishwasher": {"title": "Dishwasher Maintenance", "feature": "has_dishwasher"},
                            "refrigerator": {"title": "Refrigerator Care", "feature": "has_refrigerator"},
                            "water_softener": {"title": "Water Softener Maintenance", "feature": "has_water_softener"},
                            "water_filtration": {"title": "Water Filtration System", "feature": "has_water_filtration"},
                            "sump_pump": {"title": "Sump Pump Maintenance", "feature": "has_sump_pump"},
                            "generator": {"title": "Generator Maintenance", "feature": "has_generator"},
                            "ev_charger": {"title": "EV Charger Care", "feature": "has_ev_charger"},
                            "smart_home": {"title": "Smart Home Systems", "feature": "has_smart_home"},
                            "garbage_disposal": {"title": "Garbage Disposal Care", "feature": "has_garbage_disposal"},
                            "radon_mitigation": {"title": "Radon Mitigation System", "feature": "has_radon_mitigation"},
                            "hvac_central_air": {"title": "Central Air Conditioning", "feature": "hvac_type == central_air"},
                            "hvac_heat_pump": {"title": "Heat Pump System", "feature": "hvac_type == heat_pump"},
                            "hvac_radiant": {"title": "Radiant Heating System", "feature": "hvac_type == radiant"},
                            "hvac_window_unit": {"title": "Window AC Units", "feature": "hvac_type == window_unit"},
                        },
                    },
                    "household.yaml (premium only)": {
                        "description": "Modules triggered by household composition",
                        "captured_at": "Step 3: Household (checkboxes + counts)",
                        "modules": {
                            "pet_safety": {"title": "Pet Safety & Home Care", "trigger": "household.has_pets == true"},
                            "child_safety": {"title": "Child-Proofing & Safety", "trigger": "household.num_children > 0"},
                            "elderly_accessibility": {"title": "Accessibility & Aging-in-Place", "trigger": "household.has_elderly == true"},
                            "allergy_air_quality": {"title": "Allergy Management & Indoor Air Quality", "trigger": "household.has_allergies == true"},
                        },
                    },
                    "landscaping.yaml (premium only)": {
                        "description": "Landscaping suite — only if include_landscaping is ON",
                        "gate": "coverage.include_landscaping must be true",
                        "captured_at": "Step 5: Coverage (include_landscaping toggle)",
                        "modules": {
                            "landscaping_general": "Lawn & Landscaping Master Guide",
                            "landscaping_trees_shrubs": "Tree & Shrub Care Guide",
                            "landscaping_spring": "Spring Landscaping Checklist",
                            "landscaping_fall": "Fall Landscaping Checklist",
                            "landscaping_drainage": "Drainage & Grading Guide",
                        },
                    },
                },
            },
            "section_6": {
                "title": "Inventory Templates",
                "rendering": "always included (both tiers)",
                "source": "inventory_templates.yaml",
                "modules": {
                    "equipment_checklist": "17 home systems with fill-in fields (make, model, serial, warranty, service company)",
                    "emergency_kit": "Base emergency supply checklist + 6 regional supplement lists",
                },
                "description": "Fill-in templates for documenting equipment details and building an emergency supply kit. Regional supplements are selected by ZIP.",
            },
            "section_7": {
                "title": "Contacts & Vendors",
                "rendering": "profile-rendered",
                "source": "PDF generator (no YAML modules)",
                "content": [
                    "Emergency contacts (name, phone, relationship)",
                    "Neighbors (name, phone, relationship)",
                    "Service providers: plumber, electrician, HVAC, handyman, locksmith, roofer, landscaper, pool, pest, restoration, appliance, garage door",
                    "Utilities: power, gas, water, ISP (company, account #, phone)",
                    "Insurance: provider, policy #, claims phone",
                ],
                "variables_used": {
                    "contacts_vendors.emergency_contacts[]": "Step 7: Emergency Contacts",
                    "contacts_vendors.neighbors[]": "Step 7: Emergency Contacts",
                    "contacts_vendors.plumber/electrician/hvac_tech/handyman/locksmith": "Step 6: Service Providers",
                    "contacts_vendors.power/gas/water/isp": "Step 6: Service Providers",
                    "contacts_vendors.insurance": "Step 6: Service Providers",
                },
            },
            "section_8": {
                "title": "Appendix",
                "rendering": "profile + all selected modules",
                "source": "PDF generator (summary of all modules)",
                "content": [
                    "Module index with section references",
                    "Free-form notes from user",
                    "Output preferences summary",
                ],
                "variables_used": {
                    "free_notes.notes": "Step 10: Free Notes",
                    "output_tone.tone": "Step 9: Output Tone",
                    "output_tone.detail_level": "Step 9: Output Tone",
                },
            },
        },

        # ── ONBOARDING DATA CAPTURE: what each step collects ──────────
        "onboarding_steps": {
            "step_0 — Home Identity": {
                "fields": ["address_line1", "address_line2", "city", "state", "zip_code (required)", "home_type (required)", "year_built", "square_feet"],
                "profile_path": "home_identity.*",
                "drives": [
                    "ZIP → region selection (5 region modules)",
                    "home_type → home type module (1 of 5)",
                    "Address → populates [HOME_ADDRESS] in playbooks and quick-start cards",
                ],
            },
            "step_1 — Features": {
                "fields": ["93 boolean feature toggles (has_pool, has_garage, has_solar, etc.)", "hvac_type dropdown (central_air, heat_pump, radiant, window_unit, none)"],
                "profile_path": "features.*",
                "drives": [
                    "Each true toggle → includes matching system module (premium only, 30 possible modules)",
                    "hvac_type → includes matching HVAC module (1 of 4)",
                    "has_water_heater, has_roof, has_plumbing, has_electrical default to true (always-present systems)",
                ],
            },
            "step_2 — Household": {
                "fields": ["num_adults", "num_children", "has_pets + pet_types", "has_elderly", "has_allergies"],
                "profile_path": "household.*",
                "drives": [
                    "has_pets → pet_safety module (premium)",
                    "num_children > 0 → child_safety module (premium)",
                    "has_elderly → elderly_accessibility module (premium)",
                    "has_allergies → allergy_air_quality module (premium)",
                    "Household counts → cover page summary",
                ],
            },
            "step_3 — Critical Locations": {
                "fields": [
                    "home_nickname",
                    "owner_renter (owner/renter)",
                    "7 critical locations, each with status (known/unknown) + location text:",
                    "  water_shutoff, gas_shutoff, electrical_panel, hvac_unit, sump_pump, attic_access, crawlspace_access",
                ],
                "profile_path": "critical_locations.*",
                "drives": [
                    "Populates [WATER_SHUTOFF_LOCATION], [GAS_SHUTOFF_LOCATION], [ELECTRICAL_PANEL_LOCATION], [HVAC_UNIT_LOCATION], etc. across all playbooks and quick-start cards",
                    "Unknown locations become 'TO BE FILLED IN' placeholders in the printed binder — encourages discovery",
                ],
            },
            "step_4 — Coverage": {
                "fields": ["include_emergency", "include_seasonal", "include_maintenance", "include_systems (premium)", "include_cleaning", "include_landscaping (premium)"],
                "profile_path": "coverage.*",
                "drives": [
                    "Each toggle gates an entire category of modules:",
                    "  include_emergency OFF → drops emergency_contacts, fire_safety from section 3",
                    "  include_seasonal OFF → drops 4 seasonal checklists from section 5",
                    "  include_cleaning OFF → drops cleaning_basics from section 5",
                    "  include_maintenance OFF → drops general_maintenance, home_inventory from section 5",
                    "  include_systems OFF → drops ALL 30 system modules from section 5 (premium)",
                    "  include_landscaping OFF → drops ALL 5 landscaping modules from section 5 (premium)",
                ],
            },
            "step_5 — Service Providers": {
                "fields": [
                    "5 providers: plumber, electrician, hvac_tech, handyman, locksmith (each: name, phone, skip)",
                    "4 utilities: power, gas, water, isp (each: company, account #, phone, skip)",
                    "Insurance: provider, policy_number, claim_phone, skip",
                ],
                "profile_path": "contacts_vendors.{plumber,electrician,...,insurance}",
                "drives": [
                    "Populates [PLUMBER_NAME], [PLUMBER_PHONE], [ELECTRICIAN_NAME], etc. in playbooks",
                    "Populates [GAS_COMPANY_PHONE], [POWER_COMPANY_PHONE] in quick-start cards",
                    "Populates [INSURANCE_PROVIDER], [INSURANCE_POLICY_NUMBER] in emergency contacts",
                    "Skipped providers become fill-in blanks in the binder",
                ],
            },
            "step_6 — Emergency Contacts": {
                "fields": [
                    "Emergency contacts list (name, phone, relationship) — dynamic add/remove",
                    "Neighbors list (name, phone, relationship) — dynamic add/remove",
                ],
                "profile_path": "contacts_vendors.emergency_contacts[], contacts_vendors.neighbors[]",
                "drives": [
                    "Populates [PRIMARY_CONTACT_NAME], [PRIMARY_CONTACT_PHONE] in all playbooks",
                    "Populates [TRUSTED_NEIGHBOR_NAME], [TRUSTED_NEIGHBOR_PHONE] in emergency reference",
                    "Rendered in Section 7: Contacts & Vendors",
                ],
            },
            "step_7 — Guest / Sitter Mode": {
                "fields": [
                    "fire_meeting_point (critical safety)",
                    "wifi_password, garage_code, safe_room_location",
                    "General instructions + skip toggle",
                    "Alarm instructions + skip toggle",
                    "Escalation contacts list + skip toggle",
                    "Pet sitter info (pet_names, feeding_instructions, medications, vet_name, vet_phone) + skip toggle",
                ],
                "profile_path": "guest_sitter_mode.*",
                "drives": [
                    "Populates [FIRE_MEETING_POINT] in fire playbook and quick-start cards",
                    "Populates [WIFI_PASSWORD], [GARAGE_CODE], [ALARM_CODE] in guest mode section",
                    "Entire Section 4 is rendered from this data",
                    "Skip toggles omit sub-sections from the printed binder",
                ],
            },
            "step_8 — Preferences": {
                "fields": ["maintenance_style (minimal, balanced, thorough)", "diy_comfort (none, moderate, advanced)", "budget_priority (budget, balanced, premium)"],
                "profile_path": "preferences.*",
                "drives": [
                    "Influences AI-generated content tone and recommendations",
                    "DIY comfort level affects whether modules emphasize pro vs. DIY approaches",
                ],
            },
            "step_9 — Output Tone": {
                "fields": ["tone (friendly, professional, concise)", "detail_level (brief, standard, detailed)"],
                "profile_path": "output_tone.*",
                "drives": [
                    "Controls AI content generation style",
                    "detail_level affects how verbose AI-generated section intros and tips are",
                ],
            },
            "step_10 — Free Notes": {
                "fields": ["notes (free-form text)"],
                "profile_path": "free_notes.notes",
                "drives": ["Included in Section 8: Appendix as user notes"],
            },
            "step_11 — Review": {
                "fields": ["No new data — summary review of all steps"],
                "drives": ["Marks profile as completed on finish → unlocks plan selection"],
            },
        },

        # ── FEEDBACK LOOPS: how choices cascade through the system ─────
        "feedback_loops": {
            "zip_to_region": {
                "input": "home_identity.zip_code (Step 1)",
                "logic": "3-digit ZIP prefix → region lookup table → one of 5 regions",
                "output": "5 region-specific modules added to section 5 + region_tag on storm playbook",
                "example": "ZIP 33101 → prefix 331 → southeast → hurricane, humidity, pests, mold, energy cooling modules",
            },
            "home_type_to_module": {
                "input": "home_identity.home_type (Step 1)",
                "logic": "Exact match on home_type field → one module selected",
                "output": "1 home-type module added to section 5",
                "example": "home_type=condo → condo_association module (HOA guide, shared walls, dues tracking)",
            },
            "features_to_systems": {
                "input": "features.* (Step 2) + coverage.include_systems (Step 5)",
                "logic": "For each true feature toggle, include matching systems.yaml module. HVAC uses hvac_type instead of boolean.",
                "gate": "Only runs if tier=premium AND coverage.include_systems=true",
                "output": "0-30 system modules added to section 5",
                "example": "has_pool=true + has_solar=true + hvac_type=heat_pump → pool_care + solar_panels + hvac_heat_pump",
            },
            "household_to_safety": {
                "input": "household.* (Step 3)",
                "logic": "has_pets → pet module, num_children>0 → child module, has_elderly → elderly module, has_allergies → allergy module",
                "gate": "Only runs if tier=premium",
                "output": "0-4 household modules added to section 5",
            },
            "coverage_to_universal": {
                "input": "coverage.* (Step 5)",
                "logic": "Each toggle gates a category: emergency, seasonal, cleaning, maintenance, systems, landscaping",
                "output": "Toggles can exclude entire module categories from the binder",
                "note": "Allows users to customize binder scope — a 'minimal' user might disable seasonal + cleaning + landscaping for a focused emergency/maintenance binder",
            },
            "placeholders_to_fill_in": {
                "input": "Any profile field left empty or location marked 'unknown'",
                "logic": "Empty profile fields → placeholders remain as [BRACKET_TEXT] in YAML → rendered as 'TO BE FILLED IN' blanks in the PDF",
                "output": "Blank lines in the printed binder that users fill in by hand",
                "purpose": "Encourages discovery — the binder itself becomes a checklist of things to figure out about your home",
            },
        },

        # ── TIER COMPARISON ───────────────────────────────────────────
        "tier_comparison": {
            "standard": {
                "sources": ["quick_start.yaml", "playbooks.yaml", "universal.yaml", "region.yaml", "home_type.yaml", "inventory_templates.yaml"],
                "max_modules": "~25 (1 quick-start + 6 playbooks + 9 universal + 5 region + 1 home-type + 2 inventory)",
                "description": "Emergency, seasonal, cleaning, maintenance, region, home type, inventory",
            },
            "premium": {
                "sources": ["all standard sources", "systems.yaml", "household.yaml", "landscaping.yaml"],
                "max_modules": "~87 (standard ~25 + 30 systems + 4 household + 5 landscaping + AI-enhanced content)",
                "description": "Everything in standard + system-specific SOPs + household safety + landscaping + AI personalization",
            },
        },

        # ── PLACEHOLDER CATEGORIES ────────────────────────────────────
        "placeholder_categories": {
            "home_access": "Locations and access info (shutoffs, panels, meeting points, codes) — captured in Steps 4, 8",
            "people": "Emergency contacts, neighbors, pet info, children, elderly — captured in Steps 3, 7, 8",
            "vendors": "Service providers, utilities, insurance, specialty contractors — captured in Step 6",
            "systems": "Equipment details, model numbers, capacities, settings — fill-in placeholders in the binder",
        },
    }

"""
Section-based completeness validation for BinderPro.

Works backwards from what each binder section needs to be useful.
Returns structured data showing exactly what's missing and where.
"""
from dataclasses import dataclass, field
from typing import Optional
from app.models.profile import Profile


@dataclass
class SectionStatus:
    """Completeness status for a single binder section."""
    name: str
    score: int = 100
    status: str = "complete"  # complete, incomplete, empty
    critical_missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)


@dataclass
class FeatureWarning:
    """Warning for a feature that needs additional data."""
    feature: str
    missing: list[str]
    step_to_fix: str  # Which assessment step to visit


@dataclass
class CompletenessResult:
    """Full completeness check result."""
    overall_score: int = 0
    can_generate: bool = False
    blocking_issues: list[str] = field(default_factory=list)
    sections: dict[str, dict] = field(default_factory=dict)
    feature_warnings: list[dict] = field(default_factory=list)


def check_section_1_emergency(profile: Profile) -> SectionStatus:
    """Section 1: Emergency Quick Start needs critical locations, emergency contacts, key providers."""
    section = SectionStatus(name="Emergency Quick Start")
    cl = profile.critical_locations
    cv = profile.contacts_vendors
    gsm = profile.guest_sitter_mode

    # Critical: Fire meeting point (used in fire emergency card)
    if not gsm.fire_meeting_point:
        section.critical_missing.append("Fire meeting point")

    # Critical: Main shutoffs
    if cl.water_shutoff.status == "unknown":
        section.critical_missing.append("Water shutoff location")
    if cl.gas_shutoff.status == "unknown":
        section.warnings.append("Gas shutoff location unknown")
    if cl.electrical_panel.status == "unknown":
        section.critical_missing.append("Electrical panel location")

    # Critical: At least one emergency contact
    if not cv.emergency_contacts or not cv.emergency_contacts[0].phone:
        section.critical_missing.append("Primary emergency contact")

    # Warnings: Key service providers
    if not cv.plumber.name and not cv.plumber.skip:
        section.warnings.append("Plumber not set")
    if not cv.electrician.name and not cv.electrician.skip:
        section.warnings.append("Electrician not set")
    if not cv.hvac_tech.name and not cv.hvac_tech.skip:
        section.warnings.append("HVAC technician not set")

    # Warnings: Utilities (for emergency calls)
    if not cv.power.phone and not cv.power.skip:
        section.warnings.append("Power company phone not set")
    if not cv.gas.phone and not cv.gas.skip:
        section.warnings.append("Gas company phone not set")

    # Warnings: Insurance (for recovery phase)
    if not cv.insurance.claim_phone and not cv.insurance.skip:
        section.warnings.append("Insurance claim phone not set")

    # Warnings: Restoration company (water/fire damage)
    if not cv.restoration_company.name and not cv.restoration_company.skip:
        section.tips.append("Consider adding a restoration company for water/fire emergencies")

    _calculate_section_score(section)
    return section


def check_section_2_home_profile(profile: Profile) -> SectionStatus:
    """Section 2: Home Profile needs basic home info."""
    section = SectionStatus(name="Home Profile")
    hi = profile.home_identity

    # Critical: Address
    if not hi.address_line1:
        section.critical_missing.append("Street address")
    if not hi.city:
        section.critical_missing.append("City")
    if not hi.state:
        section.critical_missing.append("State")
    if not hi.zip_code:
        section.critical_missing.append("ZIP code")

    # Critical: Home type (affects content selection)
    if not hi.home_type:
        section.critical_missing.append("Home type")

    # Warnings: Helpful for context
    if not hi.year_built:
        section.warnings.append("Year built not set")
    if not hi.square_feet:
        section.warnings.append("Square footage not set")

    _calculate_section_score(section)
    return section


def check_section_3_playbooks(profile: Profile) -> SectionStatus:
    """Section 3: Emergency Playbooks need locations, contacts, and system details."""
    section = SectionStatus(name="Emergency Playbooks")
    cl = profile.critical_locations
    cv = profile.contacts_vendors
    gsm = profile.guest_sitter_mode
    sd = profile.system_details
    f = profile.features

    # NOTE: Location items are warnings here, not critical, because they're already
    # tracked as critical in section 1. This avoids duplicate blocking issues.

    # Fire playbook needs
    if not gsm.fire_meeting_point:
        section.warnings.append("Fire meeting point needed for fire playbook")
    if not cv.insurance.claim_phone and not cv.insurance.skip:
        section.warnings.append("Insurance claim phone (fire recovery)")

    # Water emergency playbook needs
    if cl.water_shutoff.status == "unknown":
        section.warnings.append("Water shutoff needed for water emergency playbook")
    if not cv.plumber.phone and not cv.plumber.skip:
        section.warnings.append("Plumber phone (water emergency)")

    # HVAC failure playbook needs
    if cl.hvac_unit.status == "unknown":
        section.warnings.append("HVAC unit location unknown")
    if not sd.hvac_filter_size:
        section.warnings.append("HVAC filter size not set")
    if not sd.hvac_filter_location:
        section.tips.append("HVAC filter location helps with troubleshooting")

    # Power outage playbook needs
    if cl.electrical_panel.status == "unknown":
        section.warnings.append("Electrical panel needed for power outage playbook")
    if not cv.power.phone and not cv.power.skip:
        section.warnings.append("Power company phone (outage reporting)")

    # Generator-specific (if they have one)
    if f.has_generator:
        if not sd.generator_location:
            section.warnings.append("Generator location not set")
        if not sd.generator_fuel_type:
            section.warnings.append("Generator fuel type not set")

    # Security playbook needs (if they have a system)
    if f.has_security_system:
        if not sd.alarm_panel_location:
            section.warnings.append("Alarm panel location not set")
        if not sd.alarm_company_phone:
            section.warnings.append("Alarm company phone not set")

    _calculate_section_score(section)
    return section


def check_section_4_guest_mode(profile: Profile) -> SectionStatus:
    """Section 4: Guest & Sitter Mode needs access info and emergency contacts."""
    section = SectionStatus(name="Guest & Sitter Mode")
    gsm = profile.guest_sitter_mode
    h = profile.household
    f = profile.features

    # Critical: WiFi is essential for any guest
    if not gsm.wifi_password:
        section.critical_missing.append("WiFi password not set")

    # Critical: Fire meeting point is a safety essential
    if not gsm.fire_meeting_point:
        section.critical_missing.append("Fire meeting point not set")

    # Critical: Escalation contacts — guests need someone to call
    if not gsm.escalation_contacts and not gsm.skip_escalation:
        section.critical_missing.append("No escalation contacts for emergencies")

    # Warnings: Conditional on features
    if f.has_garage and not gsm.garage_code:
        section.warnings.append("Garage code not set")

    # Alarm instructions if they have a security system
    if f.has_security_system and not gsm.alarm_instructions and not gsm.skip_alarm:
        section.warnings.append("Alarm instructions not set")

    # Pet info if they have pets
    if h.has_pets:
        psi = gsm.pet_sitter_info
        if not psi.feeding_instructions and not gsm.skip_pet_sitter:
            section.warnings.append("Pet feeding instructions not set")
        if not psi.vet_phone and not gsm.skip_pet_sitter:
            section.tips.append("Vet phone number helpful for pet emergencies")

    # General instructions
    if not gsm.instructions and not gsm.skip_instructions:
        section.tips.append("General house instructions can help guests")

    _calculate_section_score(section)
    return section


def check_section_5_maintenance(profile: Profile) -> SectionStatus:
    """Section 5: Maintenance needs system details for schedules and guides."""
    section = SectionStatus(name="Maintenance & Seasonal Care")
    sd = profile.system_details
    f = profile.features

    # HVAC maintenance
    if not sd.hvac_filter_size:
        section.warnings.append("HVAC filter size needed for replacement reminders")

    # Water heater maintenance
    if not sd.water_heater_location:
        section.tips.append("Water heater location helps with maintenance tasks")

    # Pool maintenance (if applicable)
    if f.has_pool:
        if not sd.pool_equipment_location:
            section.warnings.append("Pool equipment location not set")

    # Generator maintenance (if applicable)
    if f.has_generator:
        if not sd.generator_location:
            section.warnings.append("Generator location not set")

    _calculate_section_score(section)
    return section


def check_section_6_inventory(profile: Profile) -> SectionStatus:
    """Section 6: Inventory - currently just forms to fill in."""
    section = SectionStatus(name="Home Inventory & Checklists")
    sd = profile.system_details

    # These are tips, not warnings - inventory is fill-in forms
    if not sd.hvac_model:
        section.tips.append("HVAC make/model for service records")
    if not sd.water_heater_type:
        section.tips.append("Water heater type for maintenance guides")

    # Inventory section is always "complete" since it's designed as fill-in forms
    section.status = "complete"
    section.score = 100
    return section


def check_section_7_contacts(profile: Profile) -> SectionStatus:
    """Section 7: Contacts needs emergency contacts, providers, utilities."""
    section = SectionStatus(name="Contacts & Vendors")
    cv = profile.contacts_vendors
    f = profile.features

    # Emergency contacts
    if not cv.emergency_contacts:
        section.critical_missing.append("No emergency contacts")
    elif len(cv.emergency_contacts) < 2:
        section.warnings.append("Only one emergency contact - consider adding backup")

    # Neighbors
    if not cv.neighbors:
        section.tips.append("Adding trusted neighbors can help in emergencies")

    # Core providers
    core_providers = [
        ("plumber", cv.plumber),
        ("electrician", cv.electrician),
        ("hvac_tech", cv.hvac_tech),
    ]
    for name, provider in core_providers:
        if not provider.name and not provider.skip:
            section.warnings.append(f"{name.replace('_', ' ').title()} not set")

    # Feature-dependent providers
    if f.has_pool and not cv.pool_service.name and not cv.pool_service.skip:
        section.warnings.append("Pool service provider not set")
    if f.has_garage and not cv.garage_door.name and not cv.garage_door.skip:
        section.tips.append("Garage door service can be helpful")
    if (f.has_sprinklers or f.has_fence or f.has_deck_patio) and not cv.landscaper.name and not cv.landscaper.skip:
        section.tips.append("Landscaper can help with outdoor maintenance")

    # Utilities
    if not cv.power.company and not cv.power.skip:
        section.warnings.append("Power company not set")
    if not cv.insurance.provider and not cv.insurance.skip:
        section.warnings.append("Insurance provider not set")

    _calculate_section_score(section)
    return section


def check_section_8_appendix(profile: Profile) -> SectionStatus:
    """Section 8: Appendix - preferences and notes."""
    section = SectionStatus(name="Appendix")
    # Appendix is always complete - it's just preferences/notes
    section.status = "complete"
    section.score = 100
    return section


def get_feature_warnings(profile: Profile) -> list[FeatureWarning]:
    """Check features against their required data."""
    warnings = []
    f = profile.features
    cv = profile.contacts_vendors
    sd = profile.system_details
    gsm = profile.guest_sitter_mode

    if f.has_pool:
        missing = []
        if not cv.pool_service.name and not cv.pool_service.skip:
            missing.append("Pool service provider")
        if not sd.pool_equipment_location:
            missing.append("Pool equipment location")
        if missing:
            warnings.append(FeatureWarning(
                feature="Pool",
                missing=missing,
                step_to_fix="Service Providers"
            ))

    if f.has_generator:
        missing = []
        if not sd.generator_location:
            missing.append("Generator location")
        if not sd.generator_fuel_type:
            missing.append("Generator fuel type")
        if missing:
            warnings.append(FeatureWarning(
                feature="Generator",
                missing=missing,
                step_to_fix="System Details"
            ))

    if f.has_security_system:
        missing = []
        if not sd.alarm_panel_location:
            missing.append("Alarm panel location")
        if not sd.alarm_company_phone:
            missing.append("Alarm company phone")
        if not gsm.alarm_instructions and not gsm.skip_alarm:
            missing.append("Alarm instructions for guests")
        if missing:
            warnings.append(FeatureWarning(
                feature="Security System",
                missing=missing,
                step_to_fix="Guest & Sitter Mode"
            ))

    if f.has_garage:
        missing = []
        if not gsm.garage_code:
            missing.append("Garage code for guests")
        if missing:
            warnings.append(FeatureWarning(
                feature="Garage",
                missing=missing,
                step_to_fix="Guest & Sitter Mode"
            ))

    if f.has_septic:
        missing = []
        # Could add septic service provider check here if we add that field
        if missing:
            warnings.append(FeatureWarning(
                feature="Septic System",
                missing=missing,
                step_to_fix="Service Providers"
            ))

    return warnings


def _calculate_section_score(section: SectionStatus):
    """Calculate score based on critical issues and warnings."""
    # Start at 100, subtract for issues
    score = 100
    score -= len(section.critical_missing) * 20  # Critical issues are -20 each
    score -= len(section.warnings) * 10  # Warnings are -10 each
    score -= len(section.tips) * 2  # Tips are minor -2 each

    section.score = max(0, min(100, score))

    if section.critical_missing:
        section.status = "incomplete"
    elif section.warnings:
        section.status = "needs_attention"
    else:
        section.status = "complete"


def check_completeness(profile: Profile) -> CompletenessResult:
    """Full completeness check across all sections."""
    result = CompletenessResult()

    # Check each section
    sections = [
        ("section_1", check_section_1_emergency(profile)),
        ("section_2", check_section_2_home_profile(profile)),
        ("section_3", check_section_3_playbooks(profile)),
        ("section_4", check_section_4_guest_mode(profile)),
        ("section_5", check_section_5_maintenance(profile)),
        ("section_6", check_section_6_inventory(profile)),
        ("section_7", check_section_7_contacts(profile)),
        ("section_8", check_section_8_appendix(profile)),
    ]

    total_score = 0
    for key, section in sections:
        result.sections[key] = {
            "name": section.name,
            "score": section.score,
            "status": section.status,
            "critical_missing": section.critical_missing,
            "warnings": section.warnings,
            "tips": section.tips,
        }
        total_score += section.score

        # Collect blocking issues (critical from sections 1 and 2 only)
        # Section 3's needs are contextual and already covered by section 1
        if key in ["section_1", "section_2"]:
            result.blocking_issues.extend(section.critical_missing)

    result.overall_score = total_score // len(sections)

    # Can generate if no blocking issues in core sections
    result.can_generate = len(result.blocking_issues) == 0

    # Feature warnings
    feature_warnings = get_feature_warnings(profile)
    result.feature_warnings = [
        {"feature": fw.feature, "missing": fw.missing, "step_to_fix": fw.step_to_fix}
        for fw in feature_warnings
    ]

    return result

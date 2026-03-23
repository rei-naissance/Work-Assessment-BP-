"""Unit tests for app.validation.validators and app.validation.completeness."""
import pytest

from app.validation.validators import (
    validate_phone,
    validate_zip_code,
    validate_email,
    sanitize_string,
    contains_xss,
    sanitize_profile_data,
)
from app.validation.completeness import (
    check_section_1_emergency,
    check_section_2_home_profile,
    check_section_4_guest_mode,
    check_section_7_contacts,
    check_completeness,
    get_feature_warnings,
    _calculate_section_score,
    SectionStatus,
)
from app.models.profile import (
    Profile,
    HomeIdentity,
    Features,
    CriticalLocations,
    LocationStatus,
    ContactsVendors,
    EmergencyContact,
    ServiceProvider,
    GuestSitterMode,
    SystemDetails,
    Household,
    UtilityProvider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(**overrides) -> Profile:
    """Minimal profile that passes the section_1 and section_2 blocking checks."""
    p = Profile(user_id="test-user-id")
    p.home_identity = HomeIdentity(
        address_line1="123 Main St",
        city="Springfield",
        state="IL",
        zip_code="62701",
        home_type="single_family",
    )
    p.critical_locations = CriticalLocations(
        water_shutoff=LocationStatus(status="known", location="Basement"),
        electrical_panel=LocationStatus(status="known", location="Garage"),
    )
    p.contacts_vendors = ContactsVendors(
        emergency_contacts=[EmergencyContact(name="Jane Doe", phone="555-123-4567", relationship="spouse")],
    )
    p.guest_sitter_mode = GuestSitterMode(
        wifi_password="supersecret",
        fire_meeting_point="Front sidewalk near mailbox",
        escalation_contacts=[EmergencyContact(name="Jane Doe", phone="555-123-4567")],
    )
    for attr, val in overrides.items():
        setattr(p, attr, val)
    return p


# ===========================================================================
# validators.py — validate_phone
# ===========================================================================

class TestValidatePhone:
    def test_empty_string_is_valid(self):
        assert validate_phone("") is True

    def test_none_equivalent_whitespace_only(self):
        assert validate_phone("   ") is True

    def test_us_dashes(self):
        assert validate_phone("555-123-4567") is True

    def test_us_dots(self):
        assert validate_phone("555.123.4567") is True

    def test_us_parentheses(self):
        assert validate_phone("(555) 123-4567") is True

    def test_us_no_separators(self):
        assert validate_phone("5551234567") is True

    def test_with_country_code(self):
        assert validate_phone("+15551234567") is True

    def test_too_short(self):
        assert validate_phone("123") is False

    def test_letters_in_number(self):
        assert validate_phone("555-CALL-NOW") is False


# ===========================================================================
# validators.py — validate_zip_code
# ===========================================================================

class TestValidateZipCode:
    def test_empty_is_valid(self):
        assert validate_zip_code("") is True

    def test_five_digits(self):
        assert validate_zip_code("12345") is True

    def test_nine_digit_with_dash(self):
        assert validate_zip_code("12345-6789") is True

    def test_four_digits_invalid(self):
        assert validate_zip_code("1234") is False

    def test_six_digits_invalid(self):
        assert validate_zip_code("123456") is False

    def test_letters_invalid(self):
        assert validate_zip_code("ABCDE") is False

    def test_whitespace_is_valid(self):
        assert validate_zip_code("   ") is True


# ===========================================================================
# validators.py — validate_email
# ===========================================================================

class TestValidateEmail:
    def test_empty_is_valid(self):
        assert validate_email("") is True

    def test_standard_email(self):
        assert validate_email("user@example.com") is True

    def test_subdomain_email(self):
        assert validate_email("user@mail.example.co.uk") is True

    def test_plus_addressing(self):
        assert validate_email("user+tag@example.com") is True

    def test_missing_at_sign(self):
        assert validate_email("notanemail") is False

    def test_missing_tld(self):
        assert validate_email("user@example") is False

    def test_missing_domain(self):
        assert validate_email("@example.com") is False

    def test_whitespace_only(self):
        assert validate_email("   ") is True


# ===========================================================================
# validators.py — sanitize_string
# ===========================================================================

class TestSanitizeString:
    def test_empty_returns_empty(self):
        assert sanitize_string("") == ""

    def test_strips_whitespace(self):
        assert sanitize_string("  hello  ") == "hello"

    def test_html_encodes_angle_brackets(self):
        result = sanitize_string("<b>bold</b>")
        assert "<" not in result
        assert ">" not in result

    def test_html_encodes_ampersand(self):
        result = sanitize_string("cats & dogs")
        assert "&amp;" in result

    def test_truncates_at_max_length(self):
        long_str = "a" * 20000
        result = sanitize_string(long_str, max_length=100)
        assert len(result) <= 100

    def test_normal_text_passes_through(self):
        assert sanitize_string("Hello, world!") == "Hello, world!"


# ===========================================================================
# validators.py — contains_xss
# ===========================================================================

class TestContainsXss:
    def test_empty_is_clean(self):
        assert contains_xss("") is False

    def test_plain_text_is_clean(self):
        assert contains_xss("Hello there, how are you?") is False

    def test_detects_script_tag(self):
        assert contains_xss("<script>alert(1)</script>") is True

    def test_detects_javascript_protocol(self):
        assert contains_xss("javascript:void(0)") is True

    def test_detects_onerror_attribute(self):
        assert contains_xss('<img src=x onerror=alert(1)>') is True

    def test_detects_onclick_attribute(self):
        assert contains_xss('<div onclick=evil()>') is True

    def test_case_insensitive_detection(self):
        assert contains_xss("<SCRIPT>evil()</SCRIPT>") is True

    def test_detects_iframe(self):
        assert contains_xss("<iframe src=evil.com>") is True


# ===========================================================================
# validators.py — sanitize_profile_data
# ===========================================================================

class TestSanitizeProfileData:
    def test_string_values_are_sanitized(self):
        data = {"name": "  Hello  "}
        result = sanitize_profile_data(data)
        assert result["name"] == "Hello"

    def test_nested_dicts_are_sanitized(self):
        data = {"address": {"line1": "<b>123 Main</b>"}}
        result = sanitize_profile_data(data)
        assert "<" not in result["address"]["line1"]

    def test_lists_are_sanitized(self):
        data = {"tags": ["<script>evil</script>", "safe"]}
        result = sanitize_profile_data(data)
        assert "<" not in result["tags"][0]
        assert result["tags"][1] == "safe"

    def test_non_string_values_pass_through(self):
        data = {"count": 42, "flag": True, "nothing": None}
        result = sanitize_profile_data(data)
        assert result["count"] == 42
        assert result["flag"] is True
        assert result["nothing"] is None


# ===========================================================================
# completeness.py — _calculate_section_score
# ===========================================================================

class TestCalculateSectionScore:
    def test_perfect_score_when_no_issues(self):
        s = SectionStatus(name="Test")
        _calculate_section_score(s)
        assert s.score == 100
        assert s.status == "complete"

    def test_critical_missing_reduces_score_by_20_each(self):
        s = SectionStatus(name="Test")
        s.critical_missing = ["A", "B"]
        _calculate_section_score(s)
        assert s.score == 60
        assert s.status == "incomplete"

    def test_warnings_reduce_score_by_10_each(self):
        s = SectionStatus(name="Test")
        s.warnings = ["W1", "W2", "W3"]
        _calculate_section_score(s)
        assert s.score == 70
        assert s.status == "needs_attention"

    def test_tips_reduce_score_by_2_each(self):
        s = SectionStatus(name="Test")
        s.tips = ["tip1", "tip2"]
        _calculate_section_score(s)
        assert s.score == 96

    def test_score_never_goes_below_zero(self):
        s = SectionStatus(name="Test")
        s.critical_missing = ["A"] * 10  # would be -200
        _calculate_section_score(s)
        assert s.score == 0

    def test_score_never_exceeds_100(self):
        s = SectionStatus(name="Test")
        _calculate_section_score(s)
        assert s.score == 100


# ===========================================================================
# completeness.py — check_section_1_emergency
# ===========================================================================

class TestCheckSection1Emergency:
    def test_empty_profile_has_blocking_critical_issues(self):
        p = Profile(user_id="x")
        result = check_section_1_emergency(p)
        assert "Fire meeting point" in result.critical_missing
        assert "Water shutoff location" in result.critical_missing
        assert "Electrical panel location" in result.critical_missing
        assert "Primary emergency contact" in result.critical_missing
        assert result.status == "incomplete"

    def test_fully_set_profile_has_no_critical_missing(self):
        p = _make_profile()
        result = check_section_1_emergency(p)
        assert result.critical_missing == []

    def test_known_water_shutoff_removes_that_critical_item(self):
        p = Profile(user_id="x")
        p.critical_locations = CriticalLocations(
            water_shutoff=LocationStatus(status="known", location="Basement"),
        )
        result = check_section_1_emergency(p)
        assert "Water shutoff location" not in result.critical_missing

    def test_gas_shutoff_unknown_is_warning_not_critical(self):
        p = _make_profile()
        result = check_section_1_emergency(p)
        # Gas shutoff unknown is a warning, not a blocking critical issue
        assert "Gas shutoff location unknown" not in [c for c in result.critical_missing]

    def test_missing_providers_generate_warnings(self):
        p = Profile(user_id="x")
        p.guest_sitter_mode = GuestSitterMode(fire_meeting_point="Front yard")
        p.critical_locations = CriticalLocations(
            water_shutoff=LocationStatus(status="known"),
            electrical_panel=LocationStatus(status="known"),
        )
        p.contacts_vendors = ContactsVendors(
            emergency_contacts=[EmergencyContact(name="Bob", phone="555-111-2222")],
        )
        result = check_section_1_emergency(p)
        warning_text = " ".join(result.warnings)
        assert "Plumber" in warning_text
        assert "Electrician" in warning_text
        assert "HVAC" in warning_text


# ===========================================================================
# completeness.py — check_section_2_home_profile
# ===========================================================================

class TestCheckSection2HomeProfile:
    def test_empty_home_identity_blocks_on_all_fields(self):
        p = Profile(user_id="x")
        result = check_section_2_home_profile(p)
        assert "Street address" in result.critical_missing
        assert "City" in result.critical_missing
        assert "State" in result.critical_missing
        assert "ZIP code" in result.critical_missing
        assert "Home type" in result.critical_missing

    def test_complete_home_identity_has_no_critical_missing(self):
        p = _make_profile()
        result = check_section_2_home_profile(p)
        assert result.critical_missing == []

    def test_missing_year_built_is_warning_not_critical(self):
        p = _make_profile()
        p.home_identity.year_built = None
        result = check_section_2_home_profile(p)
        assert "Year built not set" in result.warnings
        assert result.critical_missing == []

    def test_missing_square_feet_is_warning_not_critical(self):
        p = _make_profile()
        p.home_identity.square_feet = None
        result = check_section_2_home_profile(p)
        assert "Square footage not set" in result.warnings


# ===========================================================================
# completeness.py — check_section_4_guest_mode
# ===========================================================================

class TestCheckSection4GuestMode:
    def test_missing_wifi_password_is_critical(self):
        p = Profile(user_id="x")
        p.guest_sitter_mode = GuestSitterMode(
            fire_meeting_point="Front yard",
            escalation_contacts=[EmergencyContact(name="Bob", phone="555-111-2222")],
        )
        result = check_section_4_guest_mode(p)
        assert "WiFi password not set" in result.critical_missing

    def test_missing_fire_meeting_point_is_critical(self):
        p = Profile(user_id="x")
        p.guest_sitter_mode = GuestSitterMode(
            wifi_password="abc123",
            escalation_contacts=[EmergencyContact(name="Bob", phone="555-111-2222")],
        )
        result = check_section_4_guest_mode(p)
        assert "Fire meeting point not set" in result.critical_missing

    def test_skip_escalation_suppresses_critical(self):
        p = Profile(user_id="x")
        p.guest_sitter_mode = GuestSitterMode(
            wifi_password="wifi123",
            fire_meeting_point="Front yard",
            skip_escalation=True,
        )
        result = check_section_4_guest_mode(p)
        assert "No escalation contacts for emergencies" not in result.critical_missing

    def test_garage_code_warning_when_has_garage(self):
        p = _make_profile()
        p.features = Features(has_garage=True)
        p.guest_sitter_mode.garage_code = ""
        result = check_section_4_guest_mode(p)
        assert "Garage code not set" in result.warnings

    def test_pet_warning_when_has_pets_no_instructions(self):
        p = _make_profile()
        p.household = Household(has_pets=True)
        p.guest_sitter_mode.pet_sitter_info.feeding_instructions = ""
        result = check_section_4_guest_mode(p)
        assert "Pet feeding instructions not set" in result.warnings


# ===========================================================================
# completeness.py — check_section_7_contacts
# ===========================================================================

class TestCheckSection7Contacts:
    def test_no_emergency_contacts_is_critical(self):
        p = Profile(user_id="x")
        result = check_section_7_contacts(p)
        assert "No emergency contacts" in result.critical_missing

    def test_only_one_emergency_contact_is_warning(self):
        p = _make_profile()  # has exactly one
        result = check_section_7_contacts(p)
        assert any("one emergency contact" in w for w in result.warnings)

    def test_two_emergency_contacts_no_warning(self):
        p = _make_profile()
        p.contacts_vendors.emergency_contacts.append(
            EmergencyContact(name="Backup", phone="555-999-0000")
        )
        result = check_section_7_contacts(p)
        assert not any("one emergency contact" in w for w in result.warnings)

    def test_pool_service_warning_when_has_pool(self):
        p = _make_profile()
        p.features = Features(has_pool=True)
        result = check_section_7_contacts(p)
        assert "Pool service provider not set" in result.warnings

    def test_skip_pool_service_suppresses_warning(self):
        p = _make_profile()
        p.features = Features(has_pool=True)
        p.contacts_vendors.pool_service = ServiceProvider(skip=True)
        result = check_section_7_contacts(p)
        assert "Pool service provider not set" not in result.warnings


# ===========================================================================
# completeness.py — get_feature_warnings
# ===========================================================================

class TestGetFeatureWarnings:
    def test_no_features_no_warnings(self):
        p = _make_profile()
        warnings = get_feature_warnings(p)
        assert warnings == []

    def test_pool_without_service_generates_warning(self):
        p = _make_profile()
        p.features = Features(has_pool=True)
        warnings = get_feature_warnings(p)
        names = [w.feature for w in warnings]
        assert "Pool" in names

    def test_generator_without_location_generates_warning(self):
        p = _make_profile()
        p.features = Features(has_generator=True)
        p.system_details = SystemDetails()  # no generator_location
        warnings = get_feature_warnings(p)
        names = [w.feature for w in warnings]
        assert "Generator" in names

    def test_generator_fully_set_no_warning(self):
        p = _make_profile()
        p.features = Features(has_generator=True)
        p.system_details = SystemDetails(
            generator_location="Backyard shed",
            generator_fuel_type="propane",
        )
        warnings = get_feature_warnings(p)
        names = [w.feature for w in warnings]
        assert "Generator" not in names

    def test_security_system_missing_details_warns(self):
        p = _make_profile()
        p.features = Features(has_security_system=True)
        warnings = get_feature_warnings(p)
        names = [w.feature for w in warnings]
        assert "Security System" in names

    def test_garage_without_code_warns(self):
        p = _make_profile()
        p.features = Features(has_garage=True)
        p.guest_sitter_mode.garage_code = ""
        warnings = get_feature_warnings(p)
        names = [w.feature for w in warnings]
        assert "Garage" in names


# ===========================================================================
# completeness.py — check_completeness (integration)
# ===========================================================================

class TestCheckCompleteness:
    def test_empty_profile_cannot_generate(self):
        p = Profile(user_id="x")
        result = check_completeness(p)
        assert result.can_generate is False
        assert len(result.blocking_issues) > 0

    def test_minimal_complete_profile_can_generate(self):
        p = _make_profile()
        result = check_completeness(p)
        assert result.can_generate is True
        assert result.blocking_issues == []

    def test_overall_score_is_average_of_sections(self):
        p = _make_profile()
        result = check_completeness(p)
        assert 0 <= result.overall_score <= 100

    def test_all_sections_present_in_result(self):
        p = _make_profile()
        result = check_completeness(p)
        expected_keys = {
            "section_1", "section_2", "section_3", "section_4",
            "section_5", "section_6", "section_7", "section_8",
        }
        assert expected_keys == set(result.sections.keys())

    def test_section_dict_has_required_keys(self):
        p = _make_profile()
        result = check_completeness(p)
        s = result.sections["section_1"]
        for key in ("name", "score", "status", "critical_missing", "warnings", "tips"):
            assert key in s

    def test_blocking_issues_only_from_sections_1_and_2(self):
        """Section 3+ critical items must not appear in blocking_issues."""
        p = _make_profile()
        # Remove fire_meeting_point — critical in section_1 AND section_3
        p.guest_sitter_mode.fire_meeting_point = ""
        p.guest_sitter_mode.escalation_contacts = []
        p.guest_sitter_mode.skip_escalation = True
        result = check_completeness(p)
        # Blocking issues should include the section_1 fire_meeting_point entry
        assert "Fire meeting point" in result.blocking_issues

    def test_feature_warnings_included_in_result(self):
        p = _make_profile()
        p.features = Features(has_pool=True)
        result = check_completeness(p)
        feature_names = [fw["feature"] for fw in result.feature_warnings]
        assert "Pool" in feature_names

    def test_perfect_profile_has_high_score(self):
        p = _make_profile()
        # Fill in all common warnings
        p.critical_locations.gas_shutoff = LocationStatus(status="known", location="Side yard")
        p.contacts_vendors.plumber = ServiceProvider(name="Joe's Plumbing", phone="555-100-0001")
        p.contacts_vendors.electrician = ServiceProvider(name="Sparky", phone="555-100-0002")
        p.contacts_vendors.hvac_tech = ServiceProvider(name="CoolAir", phone="555-100-0003")
        p.contacts_vendors.power = UtilityProvider(
            company="ComEd", phone="800-334-7661"
        )
        p.contacts_vendors.emergency_contacts.append(
            EmergencyContact(name="Backup", phone="555-999-8888")
        )
        p.system_details.hvac_filter_size = "16x20x1"
        result = check_completeness(p)
        assert result.overall_score >= 75



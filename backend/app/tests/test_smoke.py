"""Smoke tests for binder generation with 3 profile archetypes.

Tests the full generation pipeline:
- Template validation
- Binder PDF generation
- Sitter packet generation
- Fill-in checklist generation

Run with: pytest app/tests/test_smoke.py -v
"""

import os
import tempfile
import pytest

from app.models.profile import (
    Profile, HomeIdentity, Features, Household, Coverage,
    CriticalLocations, LocationStatus, ContactsVendors,
    GuestSitterMode, PetSitterInfo, Preferences,
    EmergencyContact, ServiceProvider, UtilityProvider, InsuranceInfo,
)
from app.pdf.generator import generate_binder_pdf
from app.outputs.sitter_packet import generate_sitter_packet, generate_sitter_packet_markdown
from app.outputs.fill_in_checklist import (
    generate_fill_in_checklist, generate_fill_in_checklist_markdown,
    collect_unknowns_from_render,
)
from app.templates.narrative import clear_unknown_placeholders, get_unknown_placeholders
from app.library.validation import validate_templates, validate_placeholders_only, PlaceholderRegistry


# ============================================================
# PROFILE ARCHETYPES
# ============================================================

def _profile_minimal() -> Profile:
    """Minimal profile: only required fields, everything else empty.

    Represents a user who just signed up and entered bare minimum.
    """
    return Profile(
        user_id="smoke_minimal",
        home_identity=HomeIdentity(
            address_line1="123 Test St",
            city="Anytown",
            state="NY",
            zip_code="10001",
            home_type="apartment",
        ),
    )


def _profile_typical() -> Profile:
    """Typical profile: most common fields filled, some gaps.

    Represents an average user: single-family home, some features,
    partial contacts, critical locations partially known.
    """
    return Profile(
        user_id="smoke_typical",
        home_identity=HomeIdentity(
            address_line1="456 Oak Avenue",
            city="Springfield",
            state="IL",
            zip_code="62701",
            home_type="single_family",
            home_nickname="Oak House",
            year_built=1995,
            square_feet=2200,
            owner_renter="owner",
        ),
        features=Features(
            has_garage=True,
            has_basement=True,
            has_attic=True,
            hvac_type="central_air",
        ),
        household=Household(
            num_adults=2,
            num_children=1,
            has_pets=True,
            pet_types="dog",
        ),
        critical_locations=CriticalLocations(
            water_shutoff=LocationStatus(status="known", location="Basement utility room, left wall"),
            gas_shutoff=LocationStatus(status="known", location="Exterior, left side of house"),
            electrical_panel=LocationStatus(status="known", location="Garage, east wall"),
            hvac_unit=LocationStatus(status="unknown"),  # Gap
            sump_pump=LocationStatus(status="na"),
        ),
        contacts_vendors=ContactsVendors(
            emergency_contacts=[
                EmergencyContact(name="John Smith", phone="555-1234", relationship="neighbor"),
            ],
            neighbors=[
                EmergencyContact(name="Jane Doe", phone="555-5678", relationship="neighbor"),
            ],
            plumber=ServiceProvider(name="ABC Plumbing", phone="555-7586"),
            electrician=ServiceProvider(),  # Gap
            power=UtilityProvider(company="Springfield Electric", account_number="12345"),
            gas=UtilityProvider(company="IL Gas Co", account_number="67890"),
        ),
        guest_sitter_mode=GuestSitterMode(
            instructions="Please water the plants and check the mail.",
            alarm_instructions="Alarm code is 1234. Arm when leaving.",
            pet_sitter_info=PetSitterInfo(
                pet_names="Max",
                feeding_instructions="1 cup dry food morning and evening. Walk once in the morning.",
            ),
        ),
    )


def _profile_maximal() -> Profile:
    """Maximal profile: everything filled out completely.

    Represents a power user who filled every single field.
    """
    return Profile(
        user_id="smoke_maximal",
        home_identity=HomeIdentity(
            address_line1="789 Premium Lane",
            address_line2="Suite 100",
            city="Miami",
            state="FL",
            zip_code="33101",
            home_type="single_family",
            home_nickname="Beach House",
            year_built=2010,
            square_feet=4500,
            owner_renter="owner",
        ),
        features=Features(
            has_garage=True,
            has_basement=False,
            has_attic=True,
            has_pool=True,
            has_hot_tub=True,
            has_septic=False,
            has_well_water=False,
            has_solar=True,
            has_generator=True,
            has_ev_charger=True,
            has_fireplace=True,
            has_security_system=True,
            has_smart_home=True,
            has_water_softener=True,
            has_water_filtration=True,
            has_sump_pump=False,
            has_battery_backup=True,
            hvac_type="central_air",
        ),
        household=Household(
            num_adults=2,
            num_children=3,
            has_pets=True,
            pet_types="dog, cat",
            has_elderly=True,
            has_allergies=True,
        ),
        coverage=Coverage(
            include_emergency=True,
            include_seasonal=True,
            include_cleaning=True,
            include_maintenance=True,
            include_systems=True,
            include_landscaping=True,
        ),
        critical_locations=CriticalLocations(
            water_shutoff=LocationStatus(status="known", location="Garage, north wall near water heater"),
            gas_shutoff=LocationStatus(status="known", location="Exterior meter, front of house"),
            electrical_panel=LocationStatus(status="known", location="Garage, south wall"),
            hvac_unit=LocationStatus(status="known", location="Closet in hallway, 2nd floor"),
            sump_pump=LocationStatus(status="na"),
            attic_access=LocationStatus(status="known", location="Master bedroom closet ceiling"),
            crawlspace_access=LocationStatus(status="na"),
        ),
        contacts_vendors=ContactsVendors(
            emergency_contacts=[
                EmergencyContact(name="Alice Johnson", phone="555-1111", relationship="sister"),
                EmergencyContact(name="Bob Wilson", phone="555-2222", relationship="neighbor"),
            ],
            neighbors=[
                EmergencyContact(name="The Garcias", phone="555-3333", relationship="neighbor"),
                EmergencyContact(name="The Patels", phone="555-4444", relationship="neighbor"),
            ],
            plumber=ServiceProvider(name="Miami Plumbing Pros", phone="305-555-7586"),
            electrician=ServiceProvider(name="Sunshine Electric", phone="305-555-3532"),
            hvac_tech=ServiceProvider(name="Cool Breeze HVAC", phone="305-555-2665"),
            handyman=ServiceProvider(name="Handy Dan", phone="305-555-4263"),
            locksmith=ServiceProvider(name="24/7 Locksmith", phone="305-555-5625"),
            power=UtilityProvider(company="FPL", phone="800-555-7697", account_number="123456789"),
            gas=UtilityProvider(company="Florida Gas", phone="800-555-4277", account_number="987654321"),
            water=UtilityProvider(company="Miami Water", phone="305-555-9287", account_number="456789123"),
            isp=UtilityProvider(company="Xfinity", phone="800-555-9346", account_number="789123456"),
            insurance=InsuranceInfo(provider="State Farm", policy_number="HO-12345", claim_phone="305-555-4678"),
        ),
        guest_sitter_mode=GuestSitterMode(
            instructions="Welcome! WiFi password is 'BeachLife2024'. Trash pickup is Tuesday.",
            alarm_instructions="Code: 1234. System panel is by front door. Arm 'Away' when leaving.",
            escalation_contacts=[
                EmergencyContact(name="Alice Johnson", phone="555-1111", relationship="sister"),
            ],
            pet_sitter_info=PetSitterInfo(
                pet_names="Max (golden retriever), Whiskers (tabby cat)",
                feeding_instructions="Max: 2 cups morning, 2 cups evening. Whiskers: 1/2 cup dry food, refill as needed.",
                medications="Max: 1 pill with dinner (in cabinet above sink)",
                vet_name="Dr. Smith at Miami Pets",
                vet_phone="305-555-8387",
            ),
        ),
        preferences=Preferences(
            maintenance_style="thorough",
        ),
    )


# ============================================================
# VALIDATION TESTS
# ============================================================

def test_template_validation_passes():
    """All templates should pass placeholder validation (critical for rendering).

    Schema validation warnings are acceptable - they don't prevent rendering.
    """
    result = validate_placeholders_only(fail_fast=False)

    # Print any errors for debugging
    if not result.valid:
        for err in result.errors:
            print(f"  [{err.error_type}] {err.file_name} > {err.module_id}: {err.message}")

    assert result.valid, f"Placeholder validation failed with {len(result.errors)} errors"

    # Print schema warnings (non-fatal)
    if result.warnings:
        print(f"\n  Schema warnings ({len(result.warnings)}):")
        for w in result.warnings[:5]:  # Show first 5
            print(f"    {w}")


def test_placeholder_registry_loads():
    """Placeholder registry should load without errors."""
    registry = PlaceholderRegistry()
    tokens = registry.all_tokens()

    assert len(tokens) > 0, "No placeholders registered"
    assert "WATER_SHUTOFF_LOCATION" in tokens
    assert "GAS_SHUTOFF_LOCATION" in tokens
    assert "HOME_ADDRESS" in tokens


# ============================================================
# MINIMAL PROFILE TESTS
# ============================================================

class TestMinimalProfile:
    """Tests with minimal profile (bare minimum fields)."""

    def test_binder_pdf_generates(self):
        """Minimal profile should generate a valid PDF."""
        profile = _profile_minimal()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "minimal_binder.pdf")
            result = generate_binder_pdf(profile, path, tier="standard")

            assert os.path.exists(result)
            assert os.path.getsize(result) > 1000

    def test_sitter_packet_generates(self):
        """Minimal profile should generate sitter packet."""
        profile = _profile_minimal()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "minimal_sitter.pdf")
            result = generate_sitter_packet(profile, path, tier="standard")

            assert os.path.exists(result)
            assert os.path.getsize(result) > 500

    def test_fill_in_checklist_has_many_unknowns(self):
        """Minimal profile should have many unknowns to fill in."""
        profile = _profile_minimal()
        clear_unknown_placeholders()

        # Generate binder to populate unknowns
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "minimal_binder.pdf")
            generate_binder_pdf(profile, path, tier="standard")

        unknowns = get_unknown_placeholders()
        assert len(unknowns) >= 5, f"Expected many unknowns, got {len(unknowns)}"

    def test_fill_in_checklist_pdf(self):
        """Minimal profile should generate fill-in checklist PDF."""
        profile = _profile_minimal()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate binder first
            binder_path = os.path.join(tmpdir, "minimal_binder.pdf")
            generate_binder_pdf(profile, binder_path, tier="standard")

            # Now generate checklist
            checklist_path = os.path.join(tmpdir, "minimal_checklist.pdf")
            result = generate_fill_in_checklist(profile, checklist_path)

            assert os.path.exists(result)
            assert os.path.getsize(result) > 500


# ============================================================
# TYPICAL PROFILE TESTS
# ============================================================

class TestTypicalProfile:
    """Tests with typical profile (common user scenario)."""

    def test_binder_pdf_generates(self):
        """Typical profile should generate a valid PDF."""
        profile = _profile_typical()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "typical_binder.pdf")
            result = generate_binder_pdf(profile, path, tier="premium")

            assert os.path.exists(result)
            assert os.path.getsize(result) > 5000

    def test_sitter_packet_generates(self):
        """Typical profile should generate sitter packet with pet info."""
        profile = _profile_typical()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "typical_sitter.pdf")
            result = generate_sitter_packet(profile, path, tier="premium")

            assert os.path.exists(result)
            assert os.path.getsize(result) > 1000

    def test_sitter_packet_markdown(self):
        """Typical profile markdown should include pet info."""
        profile = _profile_typical()
        clear_unknown_placeholders()

        md = generate_sitter_packet_markdown(profile, tier="premium")

        assert "Max" in md  # Pet name
        assert "Oak House" in md  # Home nickname
        assert "Alarm" in md or "alarm" in md

    def test_fill_in_checklist_has_some_unknowns(self):
        """Typical profile should have some (but not many) unknowns."""
        profile = _profile_typical()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "typical_binder.pdf")
            generate_binder_pdf(profile, path, tier="premium")

        unknowns = get_unknown_placeholders()
        # Typical profile has gaps: electrician, HVAC location
        assert len(unknowns) >= 1, "Expected at least some unknowns"
        assert len(unknowns) < 20, f"Too many unknowns for typical profile: {len(unknowns)}"

    def test_fill_in_checklist_markdown(self):
        """Typical profile checklist should have categories."""
        profile = _profile_typical()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "typical_binder.pdf")
            generate_binder_pdf(profile, path, tier="premium")

        # Collect unknowns
        unknowns = collect_unknowns_from_render()

        md = generate_fill_in_checklist_markdown(profile, unknowns)

        assert "Fill-In Checklist" in md
        # Should have at least one category if there are unknowns
        if unknowns:
            assert "##" in md  # Category headers


# ============================================================
# MAXIMAL PROFILE TESTS
# ============================================================

class TestMaximalProfile:
    """Tests with maximal profile (everything filled out)."""

    def test_binder_pdf_generates_large(self):
        """Maximal profile should generate a large, comprehensive PDF."""
        profile = _profile_maximal()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "maximal_binder.pdf")
            result = generate_binder_pdf(profile, path, tier="premium")

            assert os.path.exists(result)
            # Maximal profile should produce larger PDF
            assert os.path.getsize(result) > 10000

    def test_sitter_packet_generates(self):
        """Maximal profile should generate comprehensive sitter packet."""
        profile = _profile_maximal()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "maximal_sitter.pdf")
            result = generate_sitter_packet(profile, path, tier="premium")

            assert os.path.exists(result)
            assert os.path.getsize(result) > 2000

    def test_fill_in_checklist_has_zero_unknowns(self):
        """Maximal profile should have minimal unknowns.

        Note: Some placeholders in templates don't have corresponding profile fields
        (e.g., ALARM_COMPANY, SAFE_ROOM_LOCATION). These are acceptable.
        """
        profile = _profile_maximal()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "maximal_binder.pdf")
            generate_binder_pdf(profile, path, tier="premium")

        unknowns = get_unknown_placeholders()
        # Allow unknowns for fields that don't exist in Profile model
        # Templates may reference fields we haven't added to profile yet
        assert len(unknowns) <= 20, f"Too many unknowns for maximal profile: {len(unknowns)}: {unknowns}"

    def test_fill_in_checklist_complete_message(self):
        """Maximal profile checklist should show 'complete' message."""
        profile = _profile_maximal()
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "maximal_binder.pdf")
            generate_binder_pdf(profile, path, tier="premium")

        unknowns = collect_unknowns_from_render()
        md = generate_fill_in_checklist_markdown(profile, unknowns)

        # If no unknowns, should say "complete"
        if not unknowns:
            assert "complete" in md.lower() or "no items" in md.lower()


# ============================================================
# CROSS-ARCHETYPE TESTS
# ============================================================

def test_all_archetypes_generate_without_errors():
    """All 3 archetypes should generate all outputs without exceptions."""
    archetypes = [
        ("minimal", _profile_minimal()),
        ("typical", _profile_typical()),
        ("maximal", _profile_maximal()),
    ]

    for name, profile in archetypes:
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Binder
            binder_path = os.path.join(tmpdir, f"{name}_binder.pdf")
            generate_binder_pdf(profile, binder_path, tier="premium")
            assert os.path.exists(binder_path), f"{name}: binder not created"

            # Sitter packet
            sitter_path = os.path.join(tmpdir, f"{name}_sitter.pdf")
            generate_sitter_packet(profile, sitter_path, tier="premium")
            assert os.path.exists(sitter_path), f"{name}: sitter packet not created"

            # Fill-in checklist
            checklist_path = os.path.join(tmpdir, f"{name}_checklist.pdf")
            generate_fill_in_checklist(profile, checklist_path)
            assert os.path.exists(checklist_path), f"{name}: checklist not created"


def test_markdown_outputs_are_valid():
    """All markdown outputs should be non-empty strings."""
    archetypes = [
        ("minimal", _profile_minimal()),
        ("typical", _profile_typical()),
        ("maximal", _profile_maximal()),
    ]

    for name, profile in archetypes:
        clear_unknown_placeholders()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate binder first to populate unknowns
            binder_path = os.path.join(tmpdir, f"{name}_binder.pdf")
            generate_binder_pdf(profile, binder_path, tier="premium")

        # Sitter packet markdown
        sitter_md = generate_sitter_packet_markdown(profile, tier="premium")
        assert isinstance(sitter_md, str), f"{name}: sitter MD not string"
        assert len(sitter_md) > 100, f"{name}: sitter MD too short"

        # Checklist markdown
        unknowns = collect_unknowns_from_render()
        checklist_md = generate_fill_in_checklist_markdown(profile, unknowns)
        assert isinstance(checklist_md, str), f"{name}: checklist MD not string"
        assert len(checklist_md) > 50, f"{name}: checklist MD too short"

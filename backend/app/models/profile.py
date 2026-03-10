from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re
import html


# Inline validators to avoid circular import with validation module
def _validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone or not phone.strip():
        return True
    pattern = r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{4,6}[-\s\.]?[0-9]{0,4}$'
    return bool(re.match(pattern, phone.strip()))


def _validate_zip_code(zip_code: str) -> bool:
    """Validate US ZIP code format."""
    if not zip_code or not zip_code.strip():
        return True
    return bool(re.match(r'^[0-9]{5}(-[0-9]{4})?$', zip_code.strip()))


def _sanitize_string(value: str, max_length: int = 10000) -> str:
    """Sanitize a string input to prevent XSS attacks."""
    if not value:
        return ""
    if len(value) > max_length:
        value = value[:max_length]
    return html.escape(value.strip())


class HomeIdentity(BaseModel):
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    home_type: str = ""  # single_family, condo, townhouse, apartment, mobile
    year_built: Optional[int] = None
    square_feet: Optional[int] = None
    home_nickname: str = ""
    owner_renter: str = "owner"  # "owner" or "renter"

    @field_validator('zip_code')
    @classmethod
    def validate_zip(cls, v: str) -> str:
        if v and not _validate_zip_code(v):
            raise ValueError('Invalid ZIP code format. Use 12345 or 12345-6789')
        return _sanitize_string(v)

    @field_validator('address_line1', 'address_line2', 'city', 'state', 'home_nickname')
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        return _sanitize_string(v)


class Features(BaseModel):
    # Structure
    has_pool: bool = False
    has_hot_tub: bool = False
    has_garage: bool = False
    has_basement: bool = False
    has_attic: bool = False
    has_crawl_space: bool = False
    has_fireplace: bool = False
    has_gutters: bool = False
    # Outdoor / Property
    has_sprinklers: bool = False
    has_fence: bool = False
    has_deck_patio: bool = False
    has_lanai: bool = False
    has_roof_deck: bool = False
    has_driveway: bool = False
    has_shed: bool = False
    has_outdoor_kitchen: bool = False
    has_outdoor_lighting: bool = False
    has_retaining_wall: bool = False
    # Water & waste
    has_septic: bool = False
    has_well_water: bool = False
    has_water_softener: bool = False
    has_water_filtration: bool = False
    has_sump_pump: bool = False
    # Energy & power
    has_solar: bool = False
    has_generator: bool = False
    has_ev_charger: bool = False
    has_battery_backup: bool = False
    # Climate & ventilation
    has_whole_house_fan: bool = False
    has_dehumidifier: bool = False
    has_humidifier: bool = False
    has_air_purifier: bool = False
    has_ductwork: bool = False
    # Security & automation
    has_security_system: bool = False
    has_smart_home: bool = False
    has_cameras: bool = False
    has_smoke_co: bool = False
    has_doorbell_cam: bool = False
    # Appliances
    has_washer_dryer: bool = False
    has_dishwasher: bool = False
    has_refrigerator: bool = False
    has_garbage_disposal: bool = False
    has_oven_range: bool = False
    has_microwave: bool = False
    has_freezer: bool = False
    has_trash_compactor: bool = False
    # Always-present systems (included by default for most homes)
    has_water_heater: bool = True
    has_roof: bool = True
    has_plumbing: bool = True
    has_electrical: bool = True
    # Specialty
    has_radon_mitigation: bool = False
    has_elevator_stairlift: bool = False
    has_central_vacuum: bool = False
    has_intercom: bool = False
    has_wine_cellar: bool = False
    # HVAC
    hvac_type: str = ""  # central_air, window_unit, heat_pump, radiant, none


class Household(BaseModel):
    num_adults: int = 1
    num_children: int = 0
    has_pets: bool = False
    pet_types: str = ""
    has_elderly: bool = False
    has_allergies: bool = False


class Preferences(BaseModel):
    maintenance_style: str = "balanced"  # minimal, balanced, thorough
    diy_comfort: str = "moderate"  # none, moderate, advanced
    budget_priority: str = "balanced"  # budget, balanced, premium


class Coverage(BaseModel):
    include_emergency: bool = True
    include_seasonal: bool = True
    include_maintenance: bool = True
    include_systems: bool = True
    include_cleaning: bool = True
    include_landscaping: bool = True


class OutputTone(BaseModel):
    tone: str = "friendly"  # friendly, professional, concise
    detail_level: str = "standard"  # brief, standard, detailed


class FreeNotes(BaseModel):
    notes: str = ""


class SystemDetails(BaseModel):
    """Key system details needed by playbooks and maintenance guides."""
    # HVAC
    hvac_filter_size: str = ""
    hvac_filter_location: str = ""
    hvac_model: str = ""
    hvac_last_serviced: str = ""
    # Water heater
    water_heater_type: str = ""  # gas, electric, tankless
    water_heater_location: str = ""
    # Generator (if has_generator)
    generator_location: str = ""
    generator_fuel_type: str = ""  # gas, propane, diesel
    generator_wattage: str = ""
    # Pool (if has_pool)
    pool_type: str = ""  # in-ground, above-ground
    pool_equipment_location: str = ""
    # Security system (if has_security_system)
    alarm_company: str = ""
    alarm_company_phone: str = ""
    alarm_panel_location: str = ""


class LocationStatus(BaseModel):
    status: str = "unknown"  # "known" or "unknown"
    location: str = ""


class CriticalLocations(BaseModel):
    water_shutoff: LocationStatus = LocationStatus()
    gas_shutoff: LocationStatus = LocationStatus()
    electrical_panel: LocationStatus = LocationStatus()
    hvac_unit: LocationStatus = LocationStatus()
    sump_pump: LocationStatus = LocationStatus()
    attic_access: LocationStatus = LocationStatus()
    crawlspace_access: LocationStatus = LocationStatus()


class EmergencyContact(BaseModel):
    name: str = ""
    phone: str = ""
    relationship: str = ""

    @field_validator('phone')
    @classmethod
    def _validate_phone_number(cls, v: str) -> str:
        if v and not _validate_phone(v):
            raise ValueError('Invalid phone number format')
        return _sanitize_string(v)

    @field_validator('name', 'relationship')
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        return _sanitize_string(v)


class ServiceProvider(BaseModel):
    name: str = ""
    phone: str = ""
    skip: bool = False

    @field_validator('phone')
    @classmethod
    def _validate_phone_number(cls, v: str) -> str:
        if v and not _validate_phone(v):
            raise ValueError('Invalid phone number format')
        return _sanitize_string(v)

    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        return _sanitize_string(v)


class UtilityProvider(BaseModel):
    company: str = ""
    account_number: str = ""
    phone: str = ""
    skip: bool = False

    @field_validator('phone')
    @classmethod
    def _validate_phone_number(cls, v: str) -> str:
        if v and not _validate_phone(v):
            raise ValueError('Invalid phone number format')
        return _sanitize_string(v)

    @field_validator('company', 'account_number')
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        return _sanitize_string(v)


class InsuranceInfo(BaseModel):
    provider: str = ""
    policy_number: str = ""
    claim_phone: str = ""
    skip: bool = False

    @field_validator('claim_phone')
    @classmethod
    def _validate_phone_number(cls, v: str) -> str:
        if v and not _validate_phone(v):
            raise ValueError('Invalid phone number format')
        return _sanitize_string(v)

    @field_validator('provider', 'policy_number')
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        return _sanitize_string(v)


class PetSitterInfo(BaseModel):
    pet_names: str = ""
    feeding_instructions: str = ""
    medications: str = ""
    vet_name: str = ""
    vet_phone: str = ""

    @field_validator('vet_phone')
    @classmethod
    def _validate_phone_number(cls, v: str) -> str:
        if v and not _validate_phone(v):
            raise ValueError('Invalid phone number format')
        return _sanitize_string(v)

    @field_validator('pet_names', 'feeding_instructions', 'medications', 'vet_name')
    @classmethod
    def sanitize_fields(cls, v: str) -> str:
        return _sanitize_string(v)


class ContactsVendors(BaseModel):
    emergency_contacts: list[EmergencyContact] = []
    neighbors: list[EmergencyContact] = []
    # Core service providers (always relevant)
    plumber: ServiceProvider = ServiceProvider()
    electrician: ServiceProvider = ServiceProvider()
    hvac_tech: ServiceProvider = ServiceProvider()
    handyman: ServiceProvider = ServiceProvider()
    locksmith: ServiceProvider = ServiceProvider()
    # Feature-dependent service providers
    roofer: ServiceProvider = ServiceProvider()
    landscaper: ServiceProvider = ServiceProvider()
    pool_service: ServiceProvider = ServiceProvider()
    pest_control: ServiceProvider = ServiceProvider()
    restoration_company: ServiceProvider = ServiceProvider()  # Water/fire damage
    appliance_repair: ServiceProvider = ServiceProvider()
    garage_door: ServiceProvider = ServiceProvider()
    # Utilities
    power: UtilityProvider = UtilityProvider()
    gas: UtilityProvider = UtilityProvider()
    water: UtilityProvider = UtilityProvider()
    isp: UtilityProvider = UtilityProvider()
    insurance: InsuranceInfo = InsuranceInfo()


class GuestSitterMode(BaseModel):
    instructions: str = ""
    skip_instructions: bool = False
    escalation_contacts: list[EmergencyContact] = []
    skip_escalation: bool = False
    alarm_instructions: str = ""
    skip_alarm: bool = False
    pet_sitter_info: PetSitterInfo = PetSitterInfo()
    skip_pet_sitter: bool = False
    # Critical safety & access fields
    fire_meeting_point: str = ""
    wifi_password: str = ""
    garage_code: str = ""
    safe_room_location: str = ""  # For tornado/severe weather


class BinderGoals(BaseModel):
    """What the user wants to get out of their binder."""
    emergency_preparedness: bool = False
    guest_handoff: bool = False
    maintenance_tracking: bool = False
    new_homeowner: bool = False
    insurance_docs: bool = False
    vendor_organization: bool = False


class Profile(BaseModel):
    user_id: str
    home_identity: HomeIdentity = HomeIdentity()
    features: Features = Features()
    household: Household = Household()
    preferences: Preferences = Preferences()
    coverage: Coverage = Coverage()
    output_tone: OutputTone = OutputTone()
    free_notes: FreeNotes = FreeNotes()
    critical_locations: CriticalLocations = CriticalLocations()
    contacts_vendors: ContactsVendors = ContactsVendors()
    guest_sitter_mode: GuestSitterMode = GuestSitterMode()
    system_details: SystemDetails = SystemDetails()
    binder_goals: BinderGoals = BinderGoals()
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

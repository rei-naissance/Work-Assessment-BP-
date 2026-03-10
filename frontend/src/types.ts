export interface HomeIdentity {
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip_code: string;
  home_type: string;
  year_built: number | null;
  square_feet: number | null;
  home_nickname: string;
  owner_renter: string;
}

export interface Features {
  // Structure
  has_pool: boolean;
  has_hot_tub: boolean;
  has_garage: boolean;
  has_basement: boolean;
  has_attic: boolean;
  has_crawl_space: boolean;
  has_fireplace: boolean;
  has_gutters: boolean;
  // Outdoor / Property
  has_sprinklers: boolean;
  has_fence: boolean;
  has_deck_patio: boolean;
  has_lanai: boolean;
  has_roof_deck: boolean;
  has_driveway: boolean;
  has_shed: boolean;
  has_outdoor_kitchen: boolean;
  has_outdoor_lighting: boolean;
  has_retaining_wall: boolean;
  // Water & waste
  has_septic: boolean;
  has_well_water: boolean;
  has_water_softener: boolean;
  has_water_filtration: boolean;
  has_sump_pump: boolean;
  // Energy & power
  has_solar: boolean;
  has_generator: boolean;
  has_ev_charger: boolean;
  has_battery_backup: boolean;
  // Climate & ventilation
  has_whole_house_fan: boolean;
  has_dehumidifier: boolean;
  has_humidifier: boolean;
  has_air_purifier: boolean;
  has_ductwork: boolean;
  // Security & automation
  has_security_system: boolean;
  has_smart_home: boolean;
  has_cameras: boolean;
  has_smoke_co: boolean;
  has_doorbell_cam: boolean;
  // Appliances
  has_washer_dryer: boolean;
  has_dishwasher: boolean;
  has_refrigerator: boolean;
  has_garbage_disposal: boolean;
  has_oven_range: boolean;
  has_microwave: boolean;
  has_freezer: boolean;
  has_trash_compactor: boolean;
  // Always-present systems
  has_water_heater: boolean;
  has_roof: boolean;
  has_plumbing: boolean;
  has_electrical: boolean;
  // Specialty
  has_radon_mitigation: boolean;
  has_elevator_stairlift: boolean;
  has_central_vacuum: boolean;
  has_intercom: boolean;
  has_wine_cellar: boolean;
  // HVAC
  hvac_type: string;
}

export interface Household {
  num_adults: number;
  num_children: number;
  has_pets: boolean;
  pet_types: string;
  has_elderly: boolean;
  has_allergies: boolean;
}

export interface Preferences {
  maintenance_style: string;
  diy_comfort: string;
  budget_priority: string;
}

export interface Coverage {
  include_emergency: boolean;
  include_seasonal: boolean;
  include_maintenance: boolean;
  include_systems: boolean;
  include_cleaning: boolean;
  include_landscaping: boolean;
}

export interface OutputTone {
  tone: string;
  detail_level: string;
}

export interface FreeNotes {
  notes: string;
}

export interface LocationStatus {
  status: string;
  location: string;
}

export interface CriticalLocations {
  water_shutoff: LocationStatus;
  gas_shutoff: LocationStatus;
  electrical_panel: LocationStatus;
  hvac_unit: LocationStatus;
  sump_pump: LocationStatus;
  attic_access: LocationStatus;
  crawlspace_access: LocationStatus;
}

export interface EmergencyContact {
  name: string;
  phone: string;
  relationship: string;
}

export interface ServiceProvider {
  name: string;
  phone: string;
  skip: boolean;
}

export interface UtilityProvider {
  company: string;
  account_number: string;
  phone: string;
  skip: boolean;
}

export interface InsuranceInfo {
  provider: string;
  policy_number: string;
  claim_phone: string;
  skip: boolean;
}

export interface PetSitterInfo {
  pet_names: string;
  feeding_instructions: string;
  medications: string;
  vet_name: string;
  vet_phone: string;
}

export interface ContactsVendors {
  emergency_contacts: EmergencyContact[];
  neighbors: EmergencyContact[];
  // Core service providers
  plumber: ServiceProvider;
  electrician: ServiceProvider;
  hvac_tech: ServiceProvider;
  handyman: ServiceProvider;
  locksmith: ServiceProvider;
  // Feature-dependent providers
  roofer: ServiceProvider;
  landscaper: ServiceProvider;
  pool_service: ServiceProvider;
  pest_control: ServiceProvider;
  restoration_company: ServiceProvider;
  appliance_repair: ServiceProvider;
  garage_door: ServiceProvider;
  // Utilities
  power: UtilityProvider;
  gas: UtilityProvider;
  water: UtilityProvider;
  isp: UtilityProvider;
  insurance: InsuranceInfo;
}

export interface GuestSitterMode {
  instructions: string;
  skip_instructions: boolean;
  escalation_contacts: EmergencyContact[];
  skip_escalation: boolean;
  alarm_instructions: string;
  skip_alarm: boolean;
  pet_sitter_info: PetSitterInfo;
  skip_pet_sitter: boolean;
  // Critical safety & access fields
  fire_meeting_point: string;
  wifi_password: string;
  garage_code: string;
  safe_room_location: string;
}

export interface SystemDetails {
  // HVAC
  hvac_filter_size: string;
  hvac_filter_location: string;
  hvac_model: string;
  hvac_last_serviced: string;
  // Water heater
  water_heater_type: string;
  water_heater_location: string;
  // Generator
  generator_location: string;
  generator_fuel_type: string;
  generator_wattage: string;
  // Pool
  pool_type: string;
  pool_equipment_location: string;
  // Security
  alarm_company: string;
  alarm_company_phone: string;
  alarm_panel_location: string;
}

export interface BinderGoals {
  emergency_preparedness: boolean;
  guest_handoff: boolean;
  maintenance_tracking: boolean;
  new_homeowner: boolean;
  insurance_docs: boolean;
  vendor_organization: boolean;
}

export interface Profile {
  user_id: string;
  home_identity: HomeIdentity;
  features: Features;
  household: Household;
  preferences: Preferences;
  coverage: Coverage;
  output_tone: OutputTone;
  free_notes: FreeNotes;
  critical_locations: CriticalLocations;
  contacts_vendors: ContactsVendors;
  guest_sitter_mode: GuestSitterMode;
  system_details: SystemDetails;
  binder_goals: BinderGoals;
  completed: boolean;
  purchased_tier?: Tier | '';
  stripe_session_id?: string;
}

// ── Readiness Review types ──────────────────────────────────

export interface GoalFieldEntry {
  field: string;
  step: number;
  step_label: string;
  weight: 'critical' | 'important' | 'helpful';
  message: string;
}

export interface GoalReport {
  label: string;
  score: number;
  total_fields: number;
  filled_fields: number;
  present: GoalFieldEntry[];
  missing: GoalFieldEntry[];
}

export interface StepGroupItem {
  field: string;
  goal: string;
  goal_label: string;
  weight: 'critical' | 'important' | 'helpful';
  message: string;
}

export interface ReadinessData {
  overall_score: number;
  can_generate: boolean;
  blocking_issues: string[];
  goals_were_selected: boolean;
  active_goals: string[];
  goal_reports: Record<string, GoalReport>;
  step_groups: Record<string, StepGroupItem[]>;
  sections: Record<string, unknown>;
  feature_warnings: unknown[];
}

export type Tier = 'standard' | 'premium';

export interface Binder {
  id: string;
  user_id: string;
  tier: Tier;
  modules: string[];
  status: string;
  created_at: string | null;
}
